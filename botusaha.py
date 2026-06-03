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

if not os.path.exists(BACKUP_FOLDER):
    os.makedirs(BACKUP_FOLDER)

if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["tanggal", "user_id", "username", "jenis", "kategori", "jumlah", "keterangan"])
    df.to_excel(DATA_FILE, index=False)

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

def reset_all_transactions():
    df = pd.DataFrame(columns=["tanggal", "user_id", "username", "jenis", "kategori", "jumlah", "keterangan"])
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
    teks = f"{judul}\n{'='*35}\n💰 TOTAL PEMASUKAN : Rp {total_masuk:,.0f}\n💸 TOTAL PENGELUARAN: Rp {total_keluar:,.0f}\n{'='*35}\n📈 SELISIH : Rp {selisih:,.0f}\n{status_selisih}\n{'='*35}\n📝 Total Transaksi: {len(df_periode)} kali\n\n"
    if len(df_periode) > 0:
        teks += "📋 5 Transaksi Terakhir:\n"
        for _, row in df_periode.tail(5).iterrows():
            tgl = str(row['tanggal'])[:10]
            jenis_icon = "➕" if row['jenis'] == "Pemasukan" else "➖"
            teks += f"{jenis_icon} {tgl} | {row['kategori']} | Rp {row['jumlah']:,.0f}\n"
    else:
        teks += "Belum ada transaksi di periode ini.\n"
    return teks, df_periode

async def menu_utama(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None, edit=False):
    if user_id is None:
        user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.effective_message.reply_text(f"❌ Anda belum terdaftar.\n🆔 ID Telegram Anda: {user_id}\n\nSilakan kirim ID ini ke admin untuk didaftarkan.")
        return
    role = AUTHORIZED_USERS[user_id]["role"]
    username = update.effective_user.username or update.effective_user.first_name
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
        keyboard.append([InlineKeyboardButton("🔄 Reset Catatan", callback_data="reset_transactions")])
    text = f"✅ Halo {username}! ({role})\nBot pencatat keuangan siap digunakan.\n\n📌 Pilih menu di bawah:"
    if edit:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await menu_utama(update, context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if not is_authorized(user_id):
        await query.edit_message_text("❌ Anda tidak memiliki akses.")
        return

    if data == "back_to_menu":
        await menu_utama(update, context, user_id, edit=True)
        return

    if data in ["pemasukan", "pengeluaran"]:
        jenis = "Pemasukan" if data == "pemasukan" else "Pengeluaran"
        context.user_data["jenis_catatan"] = jenis
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="back_to_menu")]]
        await query.edit_message_text(
            f"✏️ FORMAT PENCATATAN {jenis}:\n\nKetik: jumlah spasi kategori\nContoh: 50000 makan siang\n\nOpsional: 50000 makan siang | dengan klien",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "laporan_all":
        teks, _ = buat_laporan("all")
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="back_to_menu")]]
        await query.edit_message_text(teks, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "laporan_minggu":
        teks, _ = buat_laporan("minggu")
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="back_to_menu")]]
        await query.edit_message_text(teks, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "laporan_bulan":
        teks, _ = buat_laporan("bulan")
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="back_to_menu")]]
        await query.edit_message_text(teks, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "export":
        _, df = buat_laporan("all")
        if df.empty:
            keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="back_to_menu")]]
            await query.edit_message_text("Belum ada data untuk diexport.", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        export_file = f"laporan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(export_file, index=False)
        with open(export_file, "rb") as f:
            await query.message.reply_document(f, filename=export_file, caption="📊 Laporan keuangan lengkap.")
        os.remove(export_file)
        await query.edit_message_text("✅ File Excel telah dikirim di atas.")
    elif data == "reset_transactions" and is_admin(user_id):
        keyboard = [
            [InlineKeyboardButton("✅ Ya, Reset", callback_data="reset_confirm")],
            [InlineKeyboardButton("❌ Batal", callback_data="back_to_menu")]
        ]
        await query.edit_message_text("⚠️ PERINGATAN! Hapus SEMUA transaksi? Data user tetap.", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "reset_confirm" and is_admin(user_id):
        reset_all_transactions()
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="back_to_menu")]]
        await query.edit_message_text("✅ Semua catatan transaksi telah dihapus.", reply_markup=InlineKeyboardMarkup(keyboard))
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
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="back_to_menu")]]
        await query.edit_message_text("📝 Kirimkan ID Telegram user.\nContoh: 123456789", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "hapus_user_prompt" and is_admin(user_id):
        context.user_data["admin_action"] = "hapus_user"
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="back_to_menu")]]
        await query.edit_message_text("🗑️ Kirimkan ID Telegram user yang ingin dihapus.\nAdmin utama tidak bisa dihapus.", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "daftar_user" and is_admin(user_id):
        if not AUTHORIZED_USERS:
            teks = "Belum ada user terdaftar."
        else:
            teks = "📋 DAFTAR PENGGUNA:\n\n"
            for uid, info in AUTHORIZED_USERS.items():
                teks += f"🆔 {uid} | {info['nama']} | {info['role']}\n"
        keyboard = [[InlineKeyboardButton("🔙 Kembali", callback_data="kelola_user")]]
        await query.edit_message_text(teks, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

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
                    await update.message.reply_text(f"✅ User {target_id} ditambahkan!")
                    try:
                        await context.bot.send_message(target_id, "🎉 Anda ditambahkan ke bot keuangan. Ketik /start")
                    except:
                        pass
            elif admin_action == "hapus_user":
                if target_id in ADMIN_IDS:
                    await update.message.reply_text("❌ Tidak bisa menghapus admin utama.")
                elif target_id in AUTHORIZED_USERS:
                    del AUTHORIZED_USERS[target_id]
                    save_authorized_users()
                    await update.message.reply_text(f"✅ User {target_id} dihapus!")
                else:
                    await update.message.reply_text("User tidak ditemukan.")
            context.user_data["admin_action"] = None
            # kembali ke menu
            await menu_utama(update, context)
        except ValueError:
            await update.message.reply_text("❌ Kirim angka ID saja.")
        return

    if "jenis_catatan" in context.user_data:
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Akses ditolak.")
            return
        jenis = context.user_data["jenis_catatan"]
        try:
            if "|" in text:
                parts = text.split("|")
                jumlah_kategori = parts[0].strip()
                keterangan = parts[1].strip() if len(parts) > 1 else ""
                words = jumlah_kategori.split()
                if len(words) < 2:
                    raise ValueError("Format: jumlah kategori")
                jumlah = float(words[0])
                kategori = " ".join(words[1:])
            else:
                words = text.split()
                if len(words) < 2:
                    raise ValueError("Format: jumlah kategori")
                jumlah = float(words[0])
                kategori = " ".join(words[1:])
                keterangan = ""
            if jumlah <= 0:
                raise ValueError("Jumlah > 0")
            username = update.effective_user.username or update.effective_user.first_name
            simpan_transaksi(user_id, username, jenis, kategori, jumlah, keterangan)
            await update.message.reply_text(f"✅ {jenis} dicatat!\nRp {jumlah:,.0f} - {kategori}")
            del context.user_data["jenis_catatan"]
            await menu_utama(update, context)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}\nGunakan: 50000 makan siang")
        return

    if is_authorized(user_id):
        await update.message.reply_text("⚠️ Silakan pilih menu di /start")
    else:
        await update.message.reply_text(f"❌ Anda belum terdaftar. ID Anda: {user_id}\nKirim ke admin.")

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"🆔 ID Anda: {user_id}")

async def bantuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - Menu\n/id - Lihat ID\nCatat: jumlah spasi kategori\nContoh: 50000 makan siang")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bantuan", bantuan))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))
    print("Bot berjalan dengan tombol kembali yang sudah diperbaiki.")
    app.run_polling()

if __name__ == "__main__":
    main()
