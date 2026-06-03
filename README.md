Tentu, ini panduan lengkap dari awal untuk menjalankan bot Telegram Anda di VPS Ubuntu 24.04.

---

📋 Langkah 1: Persiapan VPS dan Akses Awal

Pertama, Anda perlu mengakses server Anda dan memperbarui sistemnya.

```bash
# Login ke VPS Anda (ganti dengan IP dan user Anda)
ssh root@alamat_ip_vps_anda
```

Setelah berhasil login, update dan upgrade semua paket sistem, lalu install Python 3 dan Git yang diperlukan.

```bash
# Update sistem
sudo apt update && sudo apt upgrade -y

# Install Python 3, pip, venv, dan git
sudo apt install python3 python3-pip python3-venv git -y
```

---

🔧 Langkah 2: Mengunduh Kode Bot dari GitHub

Selanjutnya, clone repository bot Anda dan masuk ke dalam direktori yang baru dibuat.

```bash
# Clone repository dari GitHub
git clone https://github.com/nurodinahmad34/botusaha.git

# Masuk ke folder bot
cd botusaha

# (Opsional) Jika perlu, pindahkan semua isi folder ke /root/telegram_bot untuk konsistensi
mkdir -p /root/telegram_bot
cp -r . /root/telegram_bot/
cd /root/telegram_bot
```

Repository Anda sudah berisi file bot.py, jadi tidak perlu membuatnya lagi.

---

⚙️ Langkah 3: Menyiapkan Virtual Environment dan Dependensi

Untuk menghindari konflik dengan Python sistem (terutama karena kebijakan PEP 668 di Ubuntu 24.04), kita akan menggunakan virtual environment (venv) yang terisolasi.

```bash
# Buat virtual environment
python3 -m venv venv

# Aktifkan environment tersebut
source venv/bin/activate
```

Sekarang, install semua library yang dibutuhkan. Repositori Anda mungkin sudah memiliki file requirements.txt. Jika ada, gunakan perintah berikut:

```bash
# Install dari requirements.txt (jika ada)
pip install -r requirements.txt
```

Jika file requirements.txt tidak ada, install library yang diperlukan secara manual:

```bash
# Install library yang diperlukan
pip install python-telegram-bot pandas openpyxl
```

Setelah selesai, keluar dari virtual environment untuk sementara.

```bash
deactivate
```

---

🤖 Langkah 4: Konfigurasi Token Bot dan Data Admin

Sebelum bot dapat berjalan, Anda harus mengisi token bot dan ID admin Anda di dalam file bot.py.

```bash
# Buka file bot.py dengan editor nano
nano bot.py
```

Cari dan ganti dua baris konfigurasi penting berikut:

1. Token Bot: Gantilah dengan token asli dari BotFather.
   ```python
   TOKEN = "8951065565:AAEZRPZqcV1LKB8iXgBVRC9jw-5oWwXoei4"
   ```
   Gantilah "895106...Xoei4" dengan token sebenarnya.
2. ID Admin: Gantilah dengan ID Telegram Anda.
   ```python
   ADMIN_IDS = [5347438783]
   ```
   Gantilah angka 5347438783 dengan ID Telegram Anda. Jika ada lebih dari satu admin, formatnya menjadi [id1, id2, id3].

Simpan perubahan dengan menekan CTRL + X, kemudian Y, lalu ENTER.

---

▶️ Langkah 5: Uji Coba Bot Secara Manual

Sangat penting untuk menguji bot secara langsung untuk memastikan kode berjalan tanpa error sebelum kita menjadikannya layanan otomatis.

```bash
# Aktifkan virtual environment
source venv/bin/activate

# Jalankan bot
python3 bot.py
```

Jika semua berjalan lancar, Anda akan melihat pesan sukses di terminal. Coba kirim pesan /start ke bot Anda di Telegram. Jika bot merespons, berarti berhasil! Hentikan bot sementara dengan menekan CTRL + C. Keluar dari virtual environment.

```bash
deactivate
```

---

🚀 Langkah 6: Membuat dan Menjalankan Layanan systemd

Langkah ini akan membuat bot Anda berjalan terus-menerus, bahkan setelah server reboot atau Anda keluar dari sesi SSH.

1. Buat file service:

Buat dan buka file service baru dengan nama telegram-bot.service:

```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

2. Isi file service:

Salin dan tempelkan konfigurasi di bawah ini ke dalam file tersebut. Pastikan untuk mengganti /root/telegram_bot jika direktori Anda berbeda.

```ini
[Unit]
Description=Telegram Finance Bot
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/telegram_bot
Environment="PATH=/root/telegram_bot/venv/bin"
ExecStart=/root/telegram_bot/venv/bin/python3 /root/telegram_bot/bot.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=telegram-bot

[Install]
WantedBy=multi-user.target
```

Simpan file dengan CTRL + X, Y, lalu ENTER.

3. Aktifkan dan jalankan service:

Jalankan perintah-perintah berikut untuk memulai bot dan mengaturnya agar berjalan otomatis.

```bash
# Memberi tahu systemd bahwa ada service baru
sudo systemctl daemon-reload

# Mengatur service agar berjalan otomatis saat booting
sudo systemctl enable telegram-bot

# Menjalankan service bot
sudo systemctl start telegram-bot

# Mengecek status service
sudo systemctl status telegram-bot
```

Jika statusnya active (running), selamat! Bot Anda sekarang online 24/7.

---

📊 Lampiran: Perintah Penting untuk Mengelola Bot

Berikut adalah perintah-perintah yang berguna untuk memonitor dan mengelola bot Anda di VPS.

Tujuan Perintah
Melihat status bot sudo systemctl status telegram-bot
Menghentikan bot sudo systemctl stop telegram-bot
Menjalankan ulang bot sudo systemctl restart telegram-bot
Melihat log secara langsung sudo journalctl -u telegram-bot -f
Melihat 100 log terakhir sudo journalctl -u telegram-bot -n 100

---

⚠️ Pemecahan Masalah Umum

1. Bot tidak merespon / status service failed: Periksa log untuk mencari tahu penyebab error dengan perintah sudo journalctl -u telegram-bot -n 50.
2. Error ModuleNotFoundError: Pastikan Anda mengaktifkan virtual environment (source venv/bin/activate) sebelum menjalankan pip install.
3. Gagal menyimpan file catatan_usaha.xlsx: Pastikan bot memiliki izin untuk menulis di direktori kerjanya. Jalankan chmod 755 /root/telegram_bot dan chown -R root:root /root/telegram_bot (jika user adalah root).

Jika ada kendala, silakan beri tahu ya, saya siap bantu.
