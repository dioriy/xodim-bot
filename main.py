import os
import json
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials
from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler,
    MessageHandler, ConversationHandler, filters
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

users = {}

(
    ASK_ROLE, ASK_NAME, ASK_PHONE,
    KELISH_RASM, KETISH_RASM
) = range(5)

def get_sheet():
    creds_dict = json.loads(CREDS_JSON)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1

def get_time():
    tz = pytz.timezone("Asia/Tashkent")
    return datetime.now(tz)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users[user_id] = {}
    keyboard = [
        [KeyboardButton("🧾 Kassir"), KeyboardButton("📦 Sklad xodimi")],
        [KeyboardButton("🧍 Sotuvchi")]
    ]
    await update.message.reply_text(
        "Assalomu alaykum, ANT Xodim botiga xush kelibsiz!\n\nIltimos, lavozimingizni tanlang:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ASK_ROLE

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users[user_id]['role'] = update.message.text
    await update.message.reply_text("Iltimos, ism familiyangizni to‘liq kiriting:", reply_markup=ReplyKeyboardRemove())
    return ASK_NAME

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users[user_id]['name'] = update.message.text
    contact_btn = KeyboardButton("📞 Raqamni yuborish", request_contact=True)
    await update.message.reply_text(
        "Iltimos, telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True)
    )
    return ASK_PHONE

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    contact = update.message.contact
    users[user_id]['phone'] = contact.phone_number
    await update.message.reply_text(
        "✅ Ma'lumotlar qabul qilindi.\n\nKerakli amalni tanlang:",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("📍 Ishga keldim")],
            [KeyboardButton("🏁 Ishdan ketdim")],
            [KeyboardButton("👤 Profilim")]
        ], resize_keyboard=True)
    )
    return ConversationHandler.END

async def kelish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Iltimos, ishga kelganingiz haqida rasm yuboring", reply_markup=ReplyKeyboardRemove())
    return KELISH_RASM

async def ketish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Iltimos, ishdan ketganingiz haqida rasm yuboring", reply_markup=ReplyKeyboardRemove())
    return KETISH_RASM

async def process_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE, holat: str):
    user = update.effective_user
    photo = update.message.photo[-1]
    file = await photo.get_file()
    vaqt = get_time()
    sana = vaqt.strftime("%Y-%m-%d")
    vaqt_str = vaqt.strftime("%H:%M")
    user_id = user.id

    data = users.get(user_id, {})
    sheet = get_sheet()
    rows = sheet.get_all_records()
    row_index = None
    for i, row in enumerate(rows, start=2):
        if str(row["Telegram ID"]) == str(user_id) and row["Sana"] == sana:
            row_index = i
            break

    if not row_index:
        sheet.append_row([
            sana, str(user_id), data.get("name"), data.get("role"), data.get("phone"),
            "", "", "", "", ""
        ])
        rows = sheet.get_all_records()
        row_index = len(rows) + 1

    if holat == "Kelgan":
        sheet.update_cell(row_index, 6, vaqt_str)
    elif holat == "Ketgan":
        sheet.update_cell(row_index, 7, vaqt_str)
        kelgan_vaqt = sheet.cell(row_index, 6).value
        if kelgan_vaqt:
            fmt = "%H:%M"
            t1 = datetime.strptime(kelgan_vaqt, fmt)
            t2 = datetime.strptime(vaqt_str, fmt)
            soat = round((t2 - t1).seconds / 3600, 2)
            sheet.update_cell(row_index, 8, str(soat))

    sheet.update_cell(row_index, 9, holat)
    sheet.update_cell(row_index, 10, file.file_id)

    caption = f"📅 {sana}\n👤 {data.get('name')}\n📲 {data.get('phone')}\n📌 {holat} — {vaqt_str}"
    await context.bot.send_photo(chat_id=GROUP_CHAT_ID, photo=file.file_id, caption=caption)
    await update.message.reply_text(f"✅ {holat} vaqti yozildi.")
    return ConversationHandler.END

async def profil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    sheet = get_sheet()
    rows = sheet.get_all_records()
    kunlar = 0
    soatlar = 0.0
    for row in rows:
        if str(row["Telegram ID"]) == str(user.id):
            kunlar += 1
            vaqt = row.get("Ishlagan vaqt (soat)", "")
            if vaqt:
                try:
                    soatlar += float(vaqt)
                except:
                    pass
    await update.message.reply_text(
        f"👤 {user.full_name}\n📆 Ishlagan kunlar: {kunlar}\n🕒 Umumiy ish vaqti: {round(soatlar, 2)} soat"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Bekor qilindi", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_PHONE: [MessageHandler(filters.CONTACT, show_menu)],
            KELISH_RASM: [MessageHandler(filters.PHOTO, lambda u, c: process_rasm(u, c, "Kelgan"))],
            KETISH_RASM: [MessageHandler(filters.PHOTO, lambda u, c: process_rasm(u, c, "Ketgan"))],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.Regex("^📍 Ishga keldim$"), kelish))
    app.add_handler(MessageHandler(filters.Regex("^🏁 Ishdan ketdim$"), ketish))
    app.add_handler(MessageHandler(filters.Regex("^👤 Profilim$"), profil))

    print("✅ Bot polling started...")
    app.run_polling()

if __name__ == "__main__":
    main()
