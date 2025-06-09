import os
import json
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler,
    MessageHandler, filters, ConversationHandler
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
    creds = Credentials.from_service_account_info(json.loads(CREDS_JSON),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds).open_by_key(SPREADSHEET_ID).sheet1

def get_time():
    return datetime.now(pytz.timezone("Asia/Tashkent"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users[user_id] = {}
    lavozim_btns = [
        [KeyboardButton("🧾 Kassir"), KeyboardButton("📦 Sklad xodimi")],
        [KeyboardButton("🧍 Sotuvchi")]
    ]
    await update.message.reply_text(
        "Assalomu alaykum, ANT Xodim botiga xush kelibsiz!\n\nIltimos, lavozimingizni tanlang:",
        reply_markup=ReplyKeyboardMarkup(lavozim_btns, resize_keyboard=True)
    )
    return ASK_ROLE

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]['role'] = update.message.text
    await update.message.reply_text("Iltimos, ism familiyangizni to‘liq kiriting:")
    return ASK_NAME

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]['name'] = update.message.text
    contact_btn = KeyboardButton("📞 Raqamni yuborish", request_contact=True)
    await update.message.reply_text("Iltimos, telefon raqamingizni yuboring:", reply_markup=ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True))
    return ASK_PHONE

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]['phone'] = update.message.contact.phone_number
    menu_btns = [
        [KeyboardButton("📍 Ishga keldim")],
        [KeyboardButton("🏁 Ishdan ketdim")],
        [KeyboardButton("👤 Profilim")]
    ]
    await update.message.reply_text("✅ Ma'lumotlar qabul qilindi. Endi kerakli amalni tanlang:", reply_markup=ReplyKeyboardMarkup(menu_btns, resize_keyboard=True))
    return ConversationHandler.END

async def kelish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Iltimos, ishga kelganingiz haqida rasm yuboring", reply_markup=ReplyKeyboardRemove())
    return KELISH_RASM

async def ketish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Iltimos, ishdan ketganingiz haqida rasm yuboring", reply_markup=ReplyKeyboardRemove())
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
        file_path = file.file_path
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    except:
        await update.message.reply_text("❗ Rasmni olishda xatolik. Qayta urinib ko‘ring.")
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
        sheet.append_row([
            sana, str(user_id), data.get("name"), data.get("role"), data.get("phone"),
            "", "", "", "", ""
        ])
        row_index = len(rows) + 2

    if holat == "Kelgan":
        sheet.update_cell(row_index, 6, vaqt_str)
    elif holat == "Ketgan":
        sheet.update_cell(row_index, 7, vaqt_str)
        kelgan_vaqt = sheet.cell(row_index, 6).value
        if kelgan_vaqt:
            t1 = datetime.strptime(kelgan_vaqt, "%H:%M")
            t2 = datetime.strptime(vaqt_str, "%H:%M")
            hours = round((t2 - t1).seconds / 3600, 2)
            sheet.update_cell(row_index, 8, str(hours))

    sheet.update_cell(row_index, 9, holat)
    sheet.update_cell(row_index, 10, file_url)

    caption = f"📅 {sana}\n👤 {data.get('name')}\n📞 {data.get('phone')}\n📌 {holat} — {vaqt_str}"
    await context.bot.send_photo(chat_id=GROUP_CHAT_ID, photo=file.file_id, caption=caption)
    await update.message.reply_text("✅ Ma'lumotlar qabul qilindi.")
    return ConversationHandler.END

async def rasm_kelish(update, context): return await process_rasm(update, context, "Kelgan")
async def rasm_ketish(update, context): return await process_rasm(update, context, "Ketgan")

async def profil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sheet = get_sheet()
    rows = sheet.get_all_records()
    kunlar, soatlar = 0, 0.0
    for row in rows:
        if str(row.get("Telegram ID")) == str(user_id):
            kunlar += 1
            ish_vaqt = row.get("Ishlagan vaqt (soat)", "")
            try:
                soatlar += float(ish_vaqt)
            except:
                pass
    await update.message.reply_text(f"👤 {update.effective_user.full_name}\n📆 Ishlagan kunlar: {kunlar}\n🕒 Umumiy ish vaqti: {round(soatlar, 2)} soat")

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
