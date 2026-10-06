#!/usr/bin/env python3
"""
Mesin Pengonfirmasi Transaksi Masuk dari Email Bank
Versi ringan - cocok untuk free hosting (Sillydev, Waifly, dll)
"""

import json
import time
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Pastikan folder project ada di path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from utils.email_client import EmailClient
from utils.telegram_notifier import TelegramNotifier
from utils.google_sheets import GoogleSheetsLogger
from utils.webhook import WebhookSender
from parsers import parse_transaction

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tx-confirmer")

# File untuk menyimpan message_id yang sudah diproses (hindari duplikat)
PROCESSED_FILE = BASE_DIR / "processed_ids.json"


def load_config() -> dict:
    config_path = BASE_DIR / "config.json"
    if not config_path.exists():
        example = BASE_DIR / "config.example.json"
        logger.error(
            f"File config.json tidak ditemukan!\n"
            f"Salin {example} menjadi config.json lalu isi datanya."
        )
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_processed_ids() -> set:
    if PROCESSED_FILE.exists():
        try:
            with open(PROCESSED_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_processed_ids(ids: set):
    # Simpan maksimal 5000 ID terakhir biar file tidak membengkak
    ids_list = list(ids)[-5000:]
    with open(PROCESSED_FILE, "w") as f:
        json.dump(ids_list, f)


def process_account(account_cfg: dict, banks_cfg: dict, processed: set) -> list:
    """Proses satu akun email, kembalikan list transaksi baru."""
    client = EmailClient(account_cfg)
    new_transactions = []

    try:
        emails = client.fetch_recent_emails(since_hours=48, limit=40)
        logger.info(f"[{account_cfg.get('name')}] Ditemukan {len(emails)} email terbaru")

        allowed_banks = account_cfg.get("banks", list(banks_cfg.keys()))

        for em in emails:
            msg_id = em.get("message_id")
            if msg_id in processed:
                continue

            for bank_name in allowed_banks:
                bank_cfg = banks_cfg.get(bank_name)
                if not bank_cfg:
                    continue

                tx = parse_transaction(em, bank_name, bank_cfg)
                if tx:
                    new_transactions.append(tx)
                    processed.add(msg_id)
                    logger.info(
                        f"✓ Transaksi baru | {bank_name} | "
                        f"Rp {tx['amount']:,.0f} | {tx.get('subject', '')[:60]}"
                    )
                    break  # Satu email cukup satu bank
            else:
                # Email tidak match bank manapun, tetap tandai biar tidak diproses ulang
                processed.add(msg_id)

    finally:
        client.disconnect()

    return new_transactions


def main():
    logger.info("=" * 50)
    logger.info("Mesin Pengonfirmasi Transaksi dimulai")
    logger.info("=" * 50)

    config = load_config()
    interval = config.get("check_interval_seconds", 120)
    banks_cfg = config.get("banks", {})
    accounts = config.get("email_accounts", [])

    if not accounts:
        logger.error("Tidak ada email_accounts di config.json")
        sys.exit(1)

    # Inisialisasi notifiers
    tg = None
    if config.get("telegram", {}).get("enabled"):
        tg_cfg = config["telegram"]
        tg = TelegramNotifier(tg_cfg.get("bot_token", ""), tg_cfg.get("chat_id", ""))
        logger.info("Telegram notifier aktif")

    sheets = None
    if config.get("google_sheets", {}).get("enabled"):
        gs_cfg = config["google_sheets"]
        sheets = GoogleSheetsLogger(
            gs_cfg.get("credentials_file", "credentials.json"),
            gs_cfg.get("spreadsheet_id", ""),
            gs_cfg.get("worksheet_name", "Transaksi"),
        )
        logger.info("Google Sheets logger aktif")

    webhook = None
    if config.get("webhook", {}).get("enabled"):
        wh_cfg = config["webhook"]
        webhook = WebhookSender(wh_cfg.get("url", ""), wh_cfg.get("secret", ""))
        logger.info("Webhook aktif")

    processed = load_processed_ids()
    logger.info(f"Memuat {len(processed)} message ID yang sudah diproses")

    while True:
        try:
            logger.info(f"--- Pengecekan dimulai ({datetime.now().strftime('%H:%M:%S')}) ---")
            all_new = []

            for acc in accounts:
                txs = process_account(acc, banks_cfg, processed)
                all_new.extend(txs)

            # Kirim notifikasi & simpan
            for tx in all_new:
                if tg:
                    tg.send(tg.format_transaction(tx))
                if sheets:
                    sheets.append_transaction(tx)
                if webhook:
                    webhook.send(tx)

            if all_new:
                save_processed_ids(processed)
                logger.info(f"Total {len(all_new)} transaksi baru diproses")
            else:
                logger.info("Tidak ada transaksi baru")

        except KeyboardInterrupt:
            logger.info("Dihentikan oleh user")
            break
        except Exception as e:
            logger.exception(f"Error di loop utama: {e}")

        logger.info(f"Menunggu {interval} detik...")
        time.sleep(interval)


if __name__ == "__main__":
    main()