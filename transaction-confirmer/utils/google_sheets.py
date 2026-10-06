import logging
from typing import Optional, List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    logger.warning("gspread / oauth2client belum terinstall. Google Sheets dinonaktifkan.")


class GoogleSheetsLogger:
    def __init__(self, credentials_file: str, spreadsheet_id: str, worksheet_name: str = "Transaksi"):
        self.credentials_file = credentials_file
        self.spreadsheet_id = spreadsheet_id
        self.worksheet_name = worksheet_name
        self.client = None
        self.sheet = None

    def connect(self) -> bool:
        if not GSPREAD_AVAILABLE:
            return False
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_file, scope)
            self.client = gspread.authorize(creds)
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            try:
                self.sheet = spreadsheet.worksheet(self.worksheet_name)
            except gspread.WorksheetNotFound:
                self.sheet = spreadsheet.add_worksheet(title=self.worksheet_name, rows=1000, cols=12)
                self.sheet.append_row([
                    "Timestamp", "Bank", "Nominal", "Deskripsi", "Pengirim",
                    "Email Account", "Subject", "Message ID", "Raw Date"
                ])
            logger.info("Berhasil terhubung ke Google Sheets")
            return True
        except Exception as e:
            logger.error(f"Gagal connect Google Sheets: {e}")
            return False

    def append_transaction(self, tx: dict) -> bool:
        if not self.sheet:
            if not self.connect():
                return False
        try:
            row = [
                datetime.now().isoformat(timespec="seconds"),
                tx.get("bank", ""),
                tx.get("amount", 0),
                tx.get("description", "")[:300],
                tx.get("sender", ""),
                tx.get("account", ""),
                tx.get("subject", "")[:200],
                tx.get("message_id", ""),
                tx.get("date", ""),
            ]
            self.sheet.append_row(row, value_input_option="USER_ENTERED")
            logger.info(f"Transaksi disimpan ke Google Sheets: {tx.get('amount')}")
            return True
        except Exception as e:
            logger.error(f"Gagal tulis Google Sheets: {e}")
            return False