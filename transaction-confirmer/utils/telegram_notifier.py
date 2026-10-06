import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def send(self, message: str, parse_mode: str = "HTML") -> bool:
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram belum dikonfigurasi")
            return False
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                logger.info("Notifikasi Telegram terkirim")
                return True
            else:
                logger.error(f"Gagal kirim Telegram: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Error Telegram: {e}")
            return False

    def format_transaction(self, tx: dict) -> str:
        amount = tx.get("amount", 0)
        amount_str = f"Rp {amount:,.0f}".replace(",", ".")
        return (
            f"<b>💰 Transaksi Masuk Terdeteksi</b>\n\n"
            f"<b>Bank:</b> {tx.get('bank', '-')}\n"
            f"<b>Nominal:</b> {amount_str}\n"
            f"<b>Waktu:</b> {tx.get('date', '-')}\n"
            f"<b>Keterangan:</b> {tx.get('description', '-')[:200]}\n"
            f"<b>Pengirim:</b> {tx.get('sender', '-')}\n"
            f"<b>Email:</b> {tx.get('account', '-')}\n"
            f"<b>Subject:</b> {tx.get('subject', '-')[:100]}"
        )