import os
import pandas as pd
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========== KONFIGURASI ==========
TOKEN = "8951065565:AAEZRPZqcV1LKB8iXgBVRC9jw-5oWwXoei4"
DATA_FILE = "catatan_usaha.xlsx"
BACKUP_FOLDER = "backup"
ADMIN_IDS = [5347438783]

# Buat folder backup
if not os.path.exists(BACKUP_FOLDER):
    os.makedirs(BACKUP_FOLDER)

# Inisialisasi file Excel jika belum ada
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["tanggal", "user_id", "username", "jenis", "kategori", "jumlah", "keterangan"])
    df.to_excel(DATA_FILE, index=False)

# Data user yang diizinkan
AUTHORIZED_USERS = {}

def load_authorized_users():
    global AUTHORIZED_USERS
    if os.path.exists("users.xlsx"):
        df_users = pd.read_excel("users.xlsx")
        for _, row in df_users.iterrows():
            AUTHORIZED_USERS[int(row["user_id"])] = {"nama": row["nama"], "role": row["role"]}
    else:
        for admin_id in ADMIN_IDS:
            AUTHORIZED_USERS[admin_id] = {"nama": "Admin", "role": "admin"}
        save_authorized_users()

def save_authorized_users():
    df_users = pd.DataFrame([{
        "user_id": uid, 
        "nama": info["nama"], 
        "role": info["role"]
    } for uid, info in AUTHORIZED_USERS.items()])
    df_users.to_excel("users.xlsx", index=False)

load_authorized_users()

def is_authorized(user_id):
    return user_id in AUTHORIZED_USERS

def is_admin(user_id):
    return user_id in AUTHORIZED_USERS and AUTHORIZED_USERS[user_id]["role"] == "admin"

def backup_data():
    if os.path.exists(DATA_FILE):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_FOLDER, f"backup_{timestamp}.xlsx")
        df = pd.read_excel(DATA_FILE)
        df.to_excel(backup_file, index=False)
        for old_file in os.listdir(BACKUP_FOLDER):
            old_path = os.path.join(BACKUP_FOLDER, old_file)
            if os.path.exists(old_path) and os.path.getctime(old_path) < (datetime.now() - timedelta(days=30)).timestamp():
                os.remove(old_path)

def simpan_transaksi(user_id, username, jenis, kategori, jumlah, keterangan=""):
    df = pd.read_excel(DATA_FILE)
    baru = pd.DataFrame([{
        "tanggal": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": user_id,
        "username": username,
        "jenis": jenis,
        "kategori": kategori,
        "jumlah": float(jumlah),
        "keterangan": keterangan
    }])
    df = pd.concat([df, baru], ignore_index=True)
    df.to_excel(DATA_FILE, index=False)
    backup_data()

def buat_laporan(periode="all"):
    if not os.path.exists(DATA_FILE):
        return "⚠️ Belum ada data.", pd.DataFrame()
    
    df = pd.read_excel(DATA_FILE)
    
    if df.empty:
        return "⚠️ Belum ada transaksi. Silakan catat pemasukan/pengeluaran terlebih dahulu.", df
    
    df["jumlah"] = pd.to_numeric(df["jumlah"], errors="coerce")
    now = datetime.now()
    
    if periode == "minggu":
        start_date = now - timedelta(days=7)
        df_periode = df[pd.to_datetime(df["tanggal"]) >= start_date]
        judul = "📅 LAPORAN MINGGU INI (7 Hari Terakhir)"
    elif periode == "bulan":
        start_date = now - timedelta(days=30)
        df_periode = df[pd.to_datetime(df["tanggal"]) >= start_date]
        judul = "📅 LAPORAN BULAN INI (30 Hari Terakhir)"
    else:
        df_periode = df
        judul = "📊 LAPORAN SEMUA WAKTU"
    
    total_masuk = df_periode[df_periode["jenis"] == "Pemasukan"]["jumlah"].sum()
    total_keluar = df_periode[df_periode["jenis"] == "Pengeluaran"]["jumlah"].sum()
    selisih = total_masuk - total_keluar
    
    total_masuk = 0 if pd.isna(total_masuk) else total_masuk
    total_keluar = 0 if pd.isna(total_keluar) else total_keluar
    selisih = 0 if pd.isna(selisih) else selisih
    
    if selisih > 0:
        status_selisih = "✅ LABA (Untung)"
    elif selisih < 0:
        status_selisih = "⚠️ RUGI (Defisit)"
    else:
        status_selisih = "⚖️ IMPAS (Balik Modal)"
    
    teks = f"{judul}\n"
    teks += f"{'='*35}\n"
    teks += f"💰 TOTAL PEMASUKAN : Rp {total_masuk:,.0f}\n"
    teks += f"💸 TOTAL PENGELUARAN: Rp {total_keluar:,.0f}\n"
    teks += f"{'='*35}\n"
    teks += f"📈 SELISIH : Rp {selisih:,.0f}\n"
    teks += f"{status_selisih}\n"
    teks += f"{'='*35}\n"
    teks += f"📝 Total Transaksi: {len(df_periode)} kali\n\n"
    
    if len(df_periode) > 0:
        teks += "📋 5 Transaksi Terakhir:\n"
        for _, row in df_periode.tail(5).iterrows():
            tgl = str(row['tanggal'])[:10]
            jenis_icon = "➕" if row['jenis'] == "Pemasukan" else "➖"
            teks += f"{jenis_icon} {tgl} | {row['kategori']} | Rp {row['jumlah']:,.0f}\n"
    else:
        teks += "Belum ada transaksi di periode ini.\n"
    
    return teks, df_periode

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    if not is_authorized(user_id):
        await update.message.reply_text(
            f"❌ Anda belum terdaftar.\n"
            f"🆔 ID Telegram Anda: {user_id}\n\n"
            f"Silakan kirim ID ini ke admin untuk didaftarkan."
        )
        return
    
    role = AUTHORIZED_USERS[user_id]["role"]
    keyboard = [
        [InlineKeyboardButton("➕ Catat Pemasukan", callback_data="pemasukan")],
        [InlineKeyboardButton("➖ Catat Pengeluaran", callback_data="pengeluaran")],
        [InlineKeyboardButton("📊 Laporan Semua", callback_data="laporan_all")],
        [InlineKeyboardButton("📅 Laporan Minggu Ini", callback_data="laporan_minggu")],
        [InlineKeyboardButton("🗓️ Laporan Bulan Ini", callback_data="laporan_bulan")],
        [InlineKeyboardButton("📎 Export Excel (Print)", callback_data="export")],
    ]
    
    if role == "admin":
        keyboard.append([InlineKeyboardButton("👥 Kelola Pengguna", callback_data="kelola_user")])
    
    await update.message.reply_text(
        f"✅ Halo {username}! ({role})\n"
        f"Bot pencatat keuangan siap digunakan.\n\n"
        f"📌 Pilih menu di bawah:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    if not is_authorized(user_id):
        await query.edit_message_text("❌ Anda tidak memiliki akses.")
        return
    
    if data in ["pemasukan", "pengeluaran"]:
        jenis = "Pemasukan" if data == "pemasukan" else "Pengeluaran"
        context.user_data["jenis_catatan"] = jenis
        await query.edit_message_text(
            f"✏️ FORMAT PENCATATAN {jenis}:\n\n"
            f"Kirim: jumlah | kategori | keterangan\n\n"
            f"Contoh:\n"
            f"50000 | Makan Siang | dengan klien"
        )
    
    elif data == "laporan_all":
        teks, _ = buat_laporan("all")
        await query.edit_message_text(teks)
    
    elif data == "laporan_minggu":
        teks, _ = buat_laporan("minggu")
        await query.edit_message_text(teks)
    
    elif data == "laporan_bulan":
        teks, _ = buat_laporan("bulan")
        await query.edit_message_text(teks)
    
    elif data == "export":
        _, df = buat_laporan("all")
        if df.empty:
            await query.edit_message_text("Belum ada data untuk diexport.")
            return
        export_file = f"laporan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(export_file, index=False)
        with open(export_file, "rb") as f:
            await query.message.reply_document(f, filename=export_file, caption="📊 Laporan keuangan lengkap. File Excel siap dibuka & diprint.")
        os.remove(export_file)
    
    elif data == "kelola_user" and is_admin(user_id):
        keyboard = [
            [InlineKeyboardButton("➕ Tambah User", callback_data="tambah_user_prompt")],
            [InlineKeyboardButton("📋 Daftar User", callback_data="daftar_user")],
            [InlineKeyboardButton("❌ Hapus User", callback_data="hapus_user_prompt")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="back_to_menu")]
        ]
        await query.edit_message_text("👥 MANAJEMEN PENGGUNA:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "tambah_user_prompt" and is_admin(user_id):
        context.user_data["admin_action"] = "tambah_user"
        await query.edit_message_text(
            "📝 KIRIMKAN ID TELEGRAM USER\n\n"
            "Cara dapat ID: suruh user kirim /id ke bot ini\n\n"
            "Contoh kirim: 123456789"
        )
    
    elif data == "hapus_user_prompt" and is_admin(user_id):
        context.user_data["admin_action"] = "hapus_user"
        await query.edit_message_text(
            "🗑️ KIRIMKAN ID TELEGRAM USER YANG INGIN DIHAPUS\n\n"
            "Contoh kirim: 123456789\n\n"
            "⚠️ Admin utama tidak bisa dihapus."
        )
    
    elif data == "daftar_user" and is_admin(user_id):
        if not AUTHORIZED_USERS:
            await query.edit_message_text("Belum ada user terdaftar.")
        else:
            teks = "📋 DAFTAR PENGGUNA TERDAFTAR:\n\n"
            for uid, info in AUTHORIZED_USERS.items():
                teks += f"🆔 ID: {uid}\n📛 Nama: {info['nama']}\n👑 Role: {info['role']}\n{'─'*20}\n"
            await query.edit_message_text(teks)
    
    elif data == "back_to_menu":
        await start(update, context)

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk semua pesan teks (bukan command)"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # CEK APAKAH INI ADMIN ACTION (tambah/hapus user)
    admin_action = context.user_data.get("admin_action")
    if admin_action and is_admin(user_id):
        try:
            target_id = int(text)
            
            if admin_action == "tambah_user":
                if target_id in AUTHORIZED_USERS:
                    await update.message.reply_text(f"⚠️ User {target_id} sudah terdaftar.")
                else:
                    AUTHORIZED_USERS[target_id] = {"nama": f"User_{target_id}", "role": "user"}
                    save_authorized_users()
                    await update.message.reply_text(f"✅ User {target_id} BERHASIL ditambahkan!")
                    try:
                        await context.bot.send_message(target_id, "🎉 SELAMAT! Anda telah ditambahkan sebagai pengguna bot keuangan.\n\nKetik /start untuk mulai menggunakan bot.")
                        await update.message.reply_text(f"📤 Notifikasi sudah dikirim.")
                    except:
                        await update.message.reply_text(f"⚠️ Notifikasi gagal dikirim.")
                context.user_data["admin_action"] = None
                return
            
            elif admin_action == "hapus_user":
                if target_id in ADMIN_IDS:
                    await update.message.reply_text("❌ Tidak bisa menghapus admin utama.")
                elif target_id in AUTHORIZED_USERS:
                    del AUTHORIZED_USERS[target_id]
                    save_authorized_users()
                    await update.message.reply_text(f"✅ User {target_id} BERHASIL dihapus!")
                else:
                    await update.message.reply_text(f"❌ User {target_id} tidak ditemukan.")
                context.user_data["admin_action"] = None
                return
                
        except ValueError:
            await update.message.reply_text("❌ Harus berupa angka (ID Telegram). Coba lagi.")
            return
    
    # CEK APAKAH INI PENCATATAN TRANSAKSI
    if "jenis_catatan" in context.user_data:
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Akses ditolak.")
            return
        
        jenis = context.user_data["jenis_catatan"]
        
        try:
            if "|" not in text:
                raise ValueError("Harus menggunakan tanda | (pipe)")
            
            parts = text.split("|")
            if len(parts) < 2:
                raise ValueError("Format: jumlah | kategori")
            
            jumlah = float(parts[0].strip())
            kategori = parts[1].strip()
            keterangan = parts[2].strip() if len(parts) > 2 else ""
            
            if jumlah <= 0:
                raise ValueError("Jumlah harus lebih dari 0")
            
            username = update.effective_user.username or update.effective_user.first_name
            simpan_transaksi(user_id, username, jenis, kategori, jumlah, keterangan)
            
            await update.message.reply_text(
                f"✅ {jenis} BERHASIL DICATAT!\n\n"
                f"💰 Jumlah: Rp {jumlah:,.0f}\n"
                f"📂 Kategori: {kategori}\n"
                f"📝 Keterangan: {keterangan if keterangan else '-'}"
            )
            
            del context.user_data["jenis_catatan"]
            
        except ValueError as e:
            await update.message.reply_text(
                f"❌ FORMAT SALAH!\n\n"
                f"Gunakan: jumlah | kategori | keterangan\n"
                f"Contoh: 50000 | Makan Siang | dengan klien\n\n"
                f"Error: {str(e)}"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
        return
    
    # JIKA BUKAN ADMIN ACTION DAN BUKAN PENCATATAN
    if is_authorized(user_id):
        await update.message.reply_text(
            "⚠️ Silakan pilih menu terlebih dahulu.\n"
            "Ketik /start untuk melihat menu."
        )
    else:
        await update.message.reply_text(
            f"❌ Anda belum terdaftar.\n"
            f"🆔 ID Anda: {user_id}\n\n"
            f"Kirimkan ID ini ke admin untuk didaftarkan."
        )

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    await update.message.reply_text(
        f"🆔 ID TELEGRAM ANDA\n\n"
        f"📛 Nama: {username}\n"
        f"🔢 ID: {user_id}\n\n"
        f"📌 Kirimkan ID ini ke admin untuk didaftarkan."
    )

async def bantuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *PANDUAN BOT KEUANGAN*\n\n"
        "*Perintah:*\n"
        "/start - Menu utama\n"
        "/id - Lihat ID Telegram sendiri\n"
        "/bantuan - Panduan ini\n\n"
        "*Mencatat Transaksi:*\n"
        "1. Pilih 'Catat Pemasukan' atau 'Catat Pengeluaran'\n"
        "2. Kirim: jumlah | kategori | keterangan\n"
        "Contoh: 50000 | Makan Siang | dengan klien\n\n"
        "*Laporan:*\n"
        "✅ Menampilkan TOTAL PEMASUKAN & PENGELUARAN\n"
        "✅ Menampilkan SELISIH (Untung/Rugi)\n\n"
        "*Fitur Admin:*\n"
        "• Tambah/Hapus pengguna via ID Telegram\n"
        "• Backup otomatis setiap transaksi",
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bantuan", bantuan))
    app.add_handler(CommandHandler("id", get_id))
    
    # Callback query handler untuk tombol
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Message handler untuk semua pesan teks (URUTAN PENTING!)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))
    
    print("="*50)
    print("🤖 TELEGRAM BOT KEUANGAN BERJALAN")
    print("="*50)
    print("✅ Multi-user & role admin")
    print("✅ Laporan: Semua | Minggu | Bulan")
    print("✅ Menampilkan TOTAL & SELISIH")
    print("✅ Backup otomatis per transaksi")
    print("✅ Tambah/hapus user via ID")
    print("="*50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
