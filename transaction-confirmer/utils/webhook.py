import requests
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class WebhookSender:
    def __init__(self, url: str, secret: str = ""):
        self.url = url
        self.secret = secret

    def send(self, tx: dict) -> bool:
        if not self.url:
            return False
        try:
            headers = {"Content-Type": "application/json"}
            if self.secret:
                headers["X-Webhook-Secret"] = self.secret
            payload = {
                "event": "transaction.credit",
                "data": tx,
            }
            resp = requests.post(self.url, json=payload, headers=headers, timeout=15)
            if 200 <= resp.status_code < 300:
                logger.info("Webhook berhasil dikirim")
                return True
            else:
                logger.error(f"Webhook gagal: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Error webhook: {e}")
            return False