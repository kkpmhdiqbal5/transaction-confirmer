# Mesin Pengonfirmasi Transaksi Masuk (Email Bank + Manual E-Wallet)

Sistem ringan untuk memantau email notifikasi bank dan mendeteksi transaksi **masuk** secara otomatis.  
Juga mendukung **input manual** untuk e-wallet (GoPay, OVO, DANA, ShopeePay, dll).

Cocok dijalankan di platform gratis seperti **Silly Development**, **Waifly**, atau sejenisnya.

## Fitur

- Multi email account (setiap bank bisa pakai email berbeda)
- Hanya memproses email dari **alamat pengirim khusus** yang kamu daftarkan
- Deteksi transaksi masuk (kredit) dari email bank
- **Input manual** untuk e-wallet / transaksi lain
- Notifikasi Telegram
- Simpan ke Google Sheets
- Webhook ke sistem lain
- Semua bisa dikonfigurasi lewat `config.json` (tanpa ubah kode)

---

## Cara Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Buat file konfigurasi

```bash
cp config.example.json config.json
```

Lalu edit `config.json`. File contoh sudah berisi:

- Contoh multi email (Gmail BCA, Gmail Mandiri+BRI, Outlook BNI)
- Daftar bank umum: **BCA, Mandiri, BRI, BNI, CIMB, Permata, Danamon**
- Pengaturan Telegram, Google Sheets, dan Webhook

#### a. Email Accounts (contoh)

```json
"email_accounts": [
  {
    "name": "Gmail BCA",
    "email": "akun.bca.saya@gmail.com",
    "password": "xxxx xxxx xxxx xxxx",
    "imap_server": "imap.gmail.com",
    "imap_port": 993,
    "use_ssl": true,
    "folders": ["INBOX"],
    "banks": ["BCA"]
  }
]
```

**Catatan Gmail:**
- Aktifkan 2-Step Verification
- Buat **App Password** di: https://myaccount.google.com/apppasswords
- Pakai App Password tersebut (bukan password biasa)

#### b. Daftar Bank & Sender yang diizinkan

Sudah tersedia contoh untuk BCA, Mandiri, BRI, BNI, CIMB, Permata, Danamon.  
Kamu bisa menambah / mengedit kapan saja.

```json
"BCA": {
  "allowed_senders": [
    "kartukreditbca@klikbca.com",
    "adminbca@klikbca.com",
    "noreply@bca.co.id"
  ],
  "keywords_credit": ["dana masuk", "kredit", "transfer masuk", "penerimaan"]
}
```

#### c. Telegram (opsional)

```json
"telegram": {
  "enabled": true,
  "bot_token": "123456789:ABCdef...",
  "chat_id": "123456789"
}
```

#### d. Google Sheets (opsional)

1. Buat Service Account di Google Cloud Console
2. Download `credentials.json` dan letakkan di folder yang sama
3. Share Google Sheet-mu ke email service account tersebut (beri akses Editor)
4. Isi `spreadsheet_id` dan set `"enabled": true`

### 3. Jalankan pemantauan email

```bash
python main.py
```

Script akan berjalan terus dan mengecek email sesuai `check_interval_seconds` (default 120 detik / 2 menit).

---

## Input Manual untuk E-Wallet

Karena e-wallet biasanya **tidak kirim email**, gunakan script ini:

```bash
python add_manual.py --source "GoPay" --amount 50000 --desc "Pembayaran order #123" --sender "Budi"
```

Atau versi pendek:

```bash
python add_manual.py -s OVO -a 125000 -d "Top up dari pelanggan" -n "Siti"
python add_manual.py -s DANA -a 75000 -d "Order #INV-2026-088"
python add_manual.py -s ShopeePay -a 99000 -d "Pembayaran Shopee"
python add_manual.py -s Manual -a 200000 -d "Transfer tunai"
```

**Parameter:**
| Flag | Keterangan | Wajib |
|------|------------|-------|
| `-s` / `--source` | Sumber (GoPay, OVO, DANA, ShopeePay, Manual, dll) | Ya |
| `-a` / `--amount` | Nominal (contoh: 50000) | Ya |
| `-d` / `--desc` | Keterangan / deskripsi | Tidak |
| `-n` / `--sender` | Nama pengirim / pelanggan | Tidak |

Transaksi manual akan:
- Dikirim ke Telegram (jika aktif)
- Disimpan ke Google Sheets (jika aktif)
- Dikirim ke Webhook (jika aktif)

---

## Menambah Bank Baru

Cukup edit `config.json` → bagian `"banks"`. Tidak perlu ubah kode.

Contoh menambah bank baru:

```json
"BankJago": {
  "allowed_senders": ["noreply@jago.com"],
  "keywords_credit": ["dana masuk", "kredit", "transfer masuk"]
}
```

Lalu tambahkan `"BankJago"` di list `banks` pada email account yang ingin memantaunya.

---

## Catatan Platform Free (Sillydev / Waifly dll)

- Pastikan platform mendukung long-running Python process
- Spek RAM biasanya 256–300 MB → sistem ini sudah dibuat ringan
- Simpan `config.json` dan `processed_ids.json` dengan aman
- Jangan commit `config.json` yang berisi password ke Git publik

---

## Keamanan

- Jangan pernah share `config.json` yang sudah diisi password
- Gunakan **App Password**, jangan password utama email
- File `processed_ids.json` menyimpan ID email yang sudah diproses (untuk hindari duplikat)

---

## File Penting

| File | Fungsi |
|------|--------|
| `main.py` | Script utama pemantauan email |
| `add_manual.py` | Input transaksi manual / e-wallet |
| `config.example.json` | Contoh konfigurasi lengkap |
| `config.json` | Konfigurasi kamu (buat dari example) |
| `requirements.txt` | Daftar library |

---

Dibuat untuk kebutuhan konfirmasi transaksi otomatis.  
Silakan atur semuanya lewat `config.json`.
