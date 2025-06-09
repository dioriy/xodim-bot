import os
import json
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials
from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
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
ASK_ROLE, ASK_NAME, ASK_PHONE, KELISH_RASM, KETISH_RASM = range(5)

def get_sheet():
    creds = Credentials.from_service_account_info(
        json.loads(CREDS_JSON),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds).open_by_key(SPREADSHEET_ID).sheet1

def get_time():
    return datetime.now(pytz.timezone("Asia/Tashkent"))

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
    users[update.effective_user.id]['role'] = update.message.text
    await update.message.reply_text("Iltimos, ism familiyangizni to‘liq kiriting:")
    return ASK_NAME

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]['name'] = update.message.text
    contact_btn = KeyboardButton("📞 Raqamni yuborish", request_contact=True)
    await update.message.reply_text(
        "Iltimos, telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True)
    )
    return ASK_PHONE

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]['phone'] = update.message.contact.phone_number
    await update.message.reply_text(
        "✅ Ma'lumotlar qabul qilindi. Endi kerakli amalni tanlang:",
        reply_markup=ReplyKeyboardMarkup([[
            KeyboardButton("📍 Ishga keldim"),
            KeyboardButton("🏁 Ishdan ketdim"),
            KeyboardButton("👤 Profilim")
        ]], resize_keyboard=True)
    )
    return ConversationHandler.END

async def kelish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Iltimos, ishga kelganingiz haqida rasm yuboring")
    return KELISH_RASM

async def ketish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Iltimos, ishdan ketganingiz haqida rasm yuboring")
    return KETISH_RASM

async def process_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE, holat: str):
    user = update.effective_user
    user_id = user.id
    data = users.get(user_id)
    if not data or 'name' not in data:
        await update.message.reply_text("❗ Avval /start buyrug‘i bilan ro‘yxatdan o‘ting.")
        return ConversationHandler.END

    try:
        photo = update.message.photo[-1]
        file = await photo.get_file()
    except Exception as e:
        await update.message.reply_text(f"❗ Rasmni olishda xatolik: {e}")
        return ConversationHandler.END

    vaqt = get_time()
    sana = vaqt.strftime("%Y-%m-%d")
    vaqt_str = vaqt.strftime("%H:%M")

    sheet = get_sheet()
    rows = sheet.get_all_records()
    row_index = None
    for i, row in enumerate(rows, start=2):
        if str(row.get("Telegram ID")) == str(user_id) and row.get("Sana") == sana:
            row_index = i
            break

    if not row_index:
        sheet.append_row([sana, str(user_id), data.get("name"), data.get("role"), data.get("phone"),
                          "", "", "", "", ""])
        rows = sheet.get_all_records()
        row_index = len(rows) + 1

    if holat == "Kelgan":
        sheet.update_cell(row_index, 6, vaqt_str)
    elif holat == "Ketgan":
        sheet.update_cell(row_index, 7, vaqt_str)
        kelgan = sheet.cell(row_index, 6).value
        if kelgan:
            t1 = datetime.strptime(kelgan, "%H:%M")
            t2 = datetime.strptime(vaqt_str, "%H:%M")
            worked = round((t2 - t1).seconds / 3600, 2)
            sheet.update_cell(row_index, 8, str(worked))

    sheet.update_cell(row_index, 9, holat)
    sheet.update_cell(row_index, 10, "Telegramga yuborilgan")

    try:
        caption = f"📅 {sana}\n👤 {data.get('name')}\n📞 {data.get('phone')}\n📌 {holat} — {vaqt_str}"
        await context.bot.send_photo(chat_id=GROUP_CHAT_ID, photo=file.file_id, caption=caption)
    except Exception as e:
        await update.message.reply_text(f"❗ Rasmni yuborishda xatolik: {e}")
        return ConversationHandler.END

    await update.message.reply_text("✅ Ma'lumotlar qabul qilindi.")
    return ConversationHandler.END

async def rasm_kelish(update, context): return await process_rasm(update, context, "Kelgan")
async def rasm_ketish(update, context): return await process_rasm(update, context, "Ketgan")

async def profil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sheet = get_sheet()
    rows = sheet.get_all_records()
    kun = 0
    soat = 0.0
    for r in rows:
        if str(r.get("Telegram ID")) == str(user_id):
            kun += 1
            ish = r.get("Ishlagan vaqt (soat)", "")
            if ish:
                try: soat += float(ish)
                except: pass
    await update.message.reply_text(f"👤 {update.effective_user.full_name}\n📆 Kunlar: {kun}\n⏱ Umumiy ish soati: {round(soat,2)} soat")

async def cancel(update, context):
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
            KELISH_RASM: [MessageHandler(filters.PHOTO, rasm_kelish)],
            KETISH_RASM: [MessageHandler(filters.PHOTO, rasm_ketish)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.Regex("^📍 Ishga keldim$"), kelish))
    app.add_handler(MessageHandler(filters.Regex("^🏁 Ishdan ketdim$"), ketish))
    app.add_handler(MessageHandler(filters.Regex("^👤 Profilim$"), profil))

    print("✅ Bot polling started...")
    app.run_polling()

if __name__ == "__main__":
    main()
