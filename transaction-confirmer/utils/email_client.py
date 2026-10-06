import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class EmailClient:
    def __init__(self, account_config: dict):
        self.name = account_config.get("name", "Unknown")
        self.email = account_config["email"]
        self.password = account_config["password"]
        self.imap_server = account_config.get("imap_server", "imap.gmail.com")
        self.imap_port = account_config.get("imap_port", 993)
        self.use_ssl = account_config.get("use_ssl", True)
        self.folders = account_config.get("folders", ["INBOX"])
        self.conn = None

    def connect(self) -> bool:
        try:
            if self.use_ssl:
                self.conn = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            else:
                self.conn = imaplib.IMAP4(self.imap_server, self.imap_port)
            self.conn.login(self.email, self.password)
            logger.info(f"[{self.name}] Berhasil login ke {self.email}")
            return True
        except Exception as e:
            logger.error(f"[{self.name}] Gagal login: {e}")
            return False

    def disconnect(self):
        try:
            if self.conn:
                self.conn.logout()
        except Exception:
            pass
        self.conn = None

    def _decode_header(self, value) -> str:
        if value is None:
            return ""
        decoded_parts = decode_header(value)
        result = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    result.append(part.decode(encoding or "utf-8", errors="replace"))
                except Exception:
                    result.append(part.decode("utf-8", errors="replace"))
            else:
                result.append(str(part))
        return " ".join(result)

    def _get_body(self, msg) -> str:
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                if "attachment" in content_disposition:
                    continue
                try:
                    payload = part.get_payload(decode=True)
                    if payload is None:
                        continue
                    charset = part.get_content_charset() or "utf-8"
                    text = payload.decode(charset, errors="replace")
                    if content_type == "text/plain":
                        body += text + "\n"
                    elif content_type == "text/html" and not body:
                        soup = BeautifulSoup(text, "lxml")
                        body += soup.get_text(separator="\n", strip=True) + "\n"
                except Exception:
                    continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                    if msg.get_content_type() == "text/html":
                        soup = BeautifulSoup(body, "lxml")
                        body = soup.get_text(separator="\n", strip=True)
            except Exception:
                body = ""
        return body.strip()

    def fetch_recent_emails(self, since_hours: int = 24, limit: int = 30) -> List[Dict]:
        """Ambil email terbaru dari folder yang dikonfigurasi."""
        if not self.conn:
            if not self.connect():
                return []

        emails = []
        for folder in self.folders:
            try:
                status, _ = self.conn.select(folder, readonly=True)
                if status != "OK":
                    logger.warning(f"[{self.name}] Tidak bisa buka folder {folder}")
                    continue

                # Cari email sejak X jam lalu
                since_date = (datetime.now(timezone.utc).timestamp() - since_hours * 3600)
                # IMAP SEARCH lebih reliable pakai SINCE (tanggal)
                date_str = datetime.now().strftime("%d-%b-%Y")
                status, data = self.conn.search(None, "ALL")
                if status != "OK" or not data[0]:
                    continue

                email_ids = data[0].split()
                # Ambil yang terbaru saja
                email_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids

                for eid in reversed(email_ids):
                    try:
                        status, msg_data = self.conn.fetch(eid, "(RFC822)")
                        if status != "OK":
                            continue
                        raw = msg_data[0][1]
                        msg = email.message_from_bytes(raw)

                        subject = self._decode_header(msg.get("Subject", ""))
                        from_addr = self._decode_header(msg.get("From", ""))
                        date_str_header = msg.get("Date")
                        try:
                            dt = parsedate_to_datetime(date_str_header)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                        except Exception:
                            dt = datetime.now(timezone.utc)

                        body = self._get_body(msg)
                        message_id = msg.get("Message-ID", f"{self.email}-{eid.decode()}")

                        emails.append({
                            "account": self.name,
                            "email": self.email,
                            "message_id": message_id,
                            "subject": subject,
                            "from": from_addr,
                            "date": dt.isoformat(),
                            "body": body,
                            "folder": folder,
                        })
                    except Exception as e:
                        logger.debug(f"Gagal parse email {eid}: {e}")
                        continue
            except Exception as e:
                logger.error(f"[{self.name}] Error di folder {folder}: {e}")

        return emails