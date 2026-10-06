#!/usr/bin/env python3
"""
Script untuk menambah transaksi manual (e-wallet / input manual).
Contoh:
  python add_manual.py --source "GoPay" --amount 50000 --desc "Pembayaran order #123" --sender "Budi"
  python add_manual.py -s OVO -a 125000 -d "Top up dari pelanggan" -n "Siti"
"""

import argparse
import json
import sys
import logging
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from utils.telegram_notifier import TelegramNotifier
from utils.google_sheets import GoogleSheetsLogger
from utils.webhook import WebhookSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("manual-tx")


def load_config() -> dict:
    config_path = BASE_DIR / "config.json"
    if not config_path.exists():
        logger.error("config.json tidak ditemukan. Salin dari config.example.json dulu.")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Tambah transaksi manual (e-wallet / lainnya)")
    parser.add_argument("--source", "-s", required=True, help="Sumber: GoPay, OVO, DANA, ShopeePay, Manual, dll")
    parser.add_argument("--amount", "-a", type=float, required=True, help="Nominal (contoh: 50000)")
    parser.add_argument("--desc", "-d", default="", help="Keterangan / deskripsi")
    parser.add_argument("--sender", "-n", default="", help="Nama pengirim / pelanggan")
    parser.add_argument("--date", default=None, help="Waktu transaksi (ISO format). Default: sekarang")
    args = parser.parse_args()

    if args.amount <= 0:
        logger.error("Nominal harus lebih dari 0")
        sys.exit(1)

    config = load_config()

    tx = {
        "bank": args.source.upper(),
        "amount": args.amount,
        "description": args.desc or f"Transaksi manual dari {args.source}",
        "sender": args.sender,
        "account": "MANUAL",
        "email": "manual-input",
        "subject": f"Manual: {args.source}",
        "date": args.date or datetime.now().isoformat(timespec="seconds"),
        "message_id": f"manual-{datetime.now().timestamp()}",
        "from": "manual",
        "raw_body_preview": args.desc,
    }

    logger.info(f"Menambahkan transaksi manual: {args.source} | Rp {args.amount:,.0f}")

    # Telegram
    if config.get("telegram", {}).get("enabled"):
        tg_cfg = config["telegram"]
        tg = TelegramNotifier(tg_cfg.get("bot_token", ""), tg_cfg.get("chat_id", ""))
        msg = tg.format_transaction(tx)
        # Tambah label manual
        msg = msg.replace("<b>💰 Transaksi Masuk Terdeteksi</b>", "<b>💰 Transaksi Manual / E-Wallet</b>")
        tg.send(msg)

    # Google Sheets
    if config.get("google_sheets", {}).get("enabled"):
        gs_cfg = config["google_sheets"]
        sheets = GoogleSheetsLogger(
            gs_cfg.get("credentials_file", "credentials.json"),
            gs_cfg.get("spreadsheet_id", ""),
            gs_cfg.get("worksheet_name", "Transaksi"),
        )
        sheets.append_transaction(tx)

    # Webhook
    if config.get("webhook", {}).get("enabled"):
        wh_cfg = config["webhook"]
        webhook = WebhookSender(wh_cfg.get("url", ""), wh_cfg.get("secret", ""))
        webhook.send(tx)

    logger.info("Transaksi manual berhasil diproses.")
    print("\n✅ Berhasil ditambahkan!")
    print(f"   Sumber   : {tx['bank']}")
    print(f"   Nominal  : Rp {tx['amount']:,.0f}".replace(",", "."))
    print(f"   Keterangan: {tx['description']}")
    if tx['sender']:
        print(f"   Pengirim : {tx['sender']}")


if __name__ == "__main__":
    main()