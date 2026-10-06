import re
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


def extract_amount(text: str) -> Optional[float]:
    """Coba ekstrak nominal rupiah dari teks."""
    # Pola umum: Rp 1.234.567 atau Rp1.234.567,00 atau 1.234.567
    patterns = [
        r"Rp\s*([\d.,]+)",
        r"IDR\s*([\d.,]+)",
        r"nominal[:\s]*([\d.,]+)",
        r"sebesar\s*([\d.,]+)",
        r"jumlah[:\s]*([\d.,]+)",
        r"([\d]{1,3}(?:\.\d{3})+(?:,\d{2})?)",  # 1.234.567,00
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            raw = match.group(1).strip()
            # Normalisasi: hapus titik ribuan, ganti koma jadi titik
            if "," in raw and "." in raw:
                # Format Indonesia: 1.234.567,89
                raw = raw.replace(".", "").replace(",", ".")
            elif "," in raw:
                # Bisa 1234,56 atau 1,234.56 (ambigous)
                if re.match(r"^\d{1,3}(,\d{3})+(,\d{2})?$", raw):
                    raw = raw.replace(",", "")
                else:
                    raw = raw.replace(",", ".")
            else:
                raw = raw.replace(".", "") if raw.count(".") > 1 else raw
            try:
                return float(raw)
            except ValueError:
                continue
    return None


def is_credit_transaction(text: str, keywords: List[str]) -> bool:
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return True
    # Pola tambahan
    credit_patterns = [
        r"dana\s+masuk",
        r"transfer\s+masuk",
        r"kredit",
        r"penerimaan",
        r"received",
        r"credit",
        r"saldo\s+bertambah",
    ]
    for pat in credit_patterns:
        if re.search(pat, text_lower):
            return True
    return False


def extract_sender(text: str) -> str:
    patterns = [
        r"dari\s+[:\-]?\s*([A-Z0-9 \.\-/]{3,50})",
        r"pengirim\s*[:\-]?\s*([A-Z0-9 \.\-/]{3,50})",
        r"from\s*[:\-]?\s*([A-Z0-9 \.\-/]{3,50})",
        r"atas nama\s*[:\-]?\s*([A-Z0-9 \.\-/]{3,50})",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()[:80]
    return ""


def parse_transaction(email_data: dict, bank_name: str, bank_config: dict) -> Optional[Dict]:
    """
    Parse email menjadi transaksi jika memenuhi kriteria.
    Return dict transaksi atau None.
    """
    subject = email_data.get("subject", "")
    body = email_data.get("body", "")
    from_addr = email_data.get("from", "").lower()
    full_text = f"{subject}\n{body}"

    # Cek sender diizinkan
    allowed_senders = [s.lower() for s in bank_config.get("allowed_senders", [])]
    sender_ok = False
    for allowed in allowed_senders:
        if allowed in from_addr:
            sender_ok = True
            break
    if not sender_ok and allowed_senders:
        return None

    # Cek apakah kredit
    keywords = bank_config.get("keywords_credit", [])
    if not is_credit_transaction(full_text, keywords):
        return None

    amount = extract_amount(full_text)
    if amount is None or amount <= 0:
        return None

    description = body[:300].replace("\n", " ").strip() if body else subject
    sender = extract_sender(full_text)

    return {
        "bank": bank_name,
        "amount": amount,
        "description": description,
        "sender": sender,
        "account": email_data.get("account"),
        "email": email_data.get("email"),
        "subject": subject,
        "date": email_data.get("date"),
        "message_id": email_data.get("message_id"),
        "from": email_data.get("from"),
        "raw_body_preview": body[:500],
    }