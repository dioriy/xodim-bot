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

def get_sheet():
    creds_dict = json.loads(CREDS_JSON)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1

def get_tashkent_time():
    tz = pytz.timezone("Asia/Tashkent")
    return datetime.now(tz)

KELISH, KETISH = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("📍 Kelish")],
        [KeyboardButton("🏁 Ketish")],
        [KeyboardButton("👤 Profilim")]
    ]
    await update.message.reply_text(
        "Assalomu alaykum!\nKerakli amalni tanlang:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def kelish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Iltimos, rasm yuboring", reply_markup=ReplyKeyboardRemove())
    return KELISH

async def rasm_kelish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo = update.message.photo[-1]
    file = await photo.get_file()
    vaqt = get_tashkent_time()
    vaqt_str = vaqt.strftime("%H:%M")
    sana = vaqt.strftime("%Y-%m-%d")

    sheet = get_sheet()
    rows = sheet.get_all_records()
    row_index = None
    for i, row in enumerate(rows, start=2):
        if str(row["Telegram ID"]) == str(user.id) and row["Sana"] == sana:
            row_index = i
            break

    if row_index:
        sheet.update_cell(row_index, 4, vaqt_str)
    else:
        sheet.append_row([sana, str(user.id), user.full_name, vaqt_str, "", ""])

    caption = f"✅ *Kelgan* — {user.full_name}\n🕒 {vaqt_str}"
    await context.bot.send_photo(chat_id=GROUP_CHAT_ID, photo=file.file_id, caption=caption, parse_mode="Markdown")
    await update.message.reply_text("✅ Kelish vaqti yozildi.")
    return ConversationHandler.END

async def ketish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Ketish rasmi yuboring", reply_markup=ReplyKeyboardRemove())
    return KETISH

async def rasm_ketish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo = update.message.photo[-1]
    file = await photo.get_file()
    vaqt = get_tashkent_time()
    vaqt_str = vaqt.strftime("%H:%M")
    sana = vaqt.strftime("%Y-%m-%d")

    sheet = get_sheet()
    rows = sheet.get_all_records()
    row_index = None
    for i, row in enumerate(rows, start=2):
        if str(row["Telegram ID"]) == str(user.id) and row["Sana"] == sana:
            row_index = i
            break

    if row_index:
        sheet.update_cell(row_index, 5, vaqt_str)
        kelgan_vaqt = sheet.cell(row_index, 4).value
        if kelgan_vaqt:
            fmt = "%H:%M"
            t1 = datetime.strptime(kelgan_vaqt, fmt)
            t2 = datetime.strptime(vaqt_str, fmt)
            worked_hours = round((t2 - t1).seconds / 3600, 2)
            sheet.update_cell(row_index, 6, str(worked_hours))
    else:
        sheet.append_row([sana, str(user.id), user.full_name, "", vaqt_str, ""])

    caption = f"🏁 *Ketgan* — {user.full_name}\n🕒 {vaqt_str}"
    await context.bot.send_photo(chat_id=GROUP_CHAT_ID, photo=file.file_id, caption=caption, parse_mode="Markdown")
    await update.message.reply_text("📤 Ketish vaqti yozildi.")
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
            try:
                ishlagan = float(row.get("Ishlagan vaqt", 0))  # 6-ustun
                soatlar += ishlagan
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

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📍 Kelish$"), kelish),
            MessageHandler(filters.Regex("^🏁 Ketish$"), ketish)
        ],
        states={
            KELISH: [MessageHandler(filters.PHOTO, rasm_kelish)],
            KETISH: [MessageHandler(filters.PHOTO, rasm_ketish)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.Regex("^👤 Profilim$"), profil))

    print("✅ Bot polling started...")
    app.run_polling()

if __name__ == "__main__":
    main()
