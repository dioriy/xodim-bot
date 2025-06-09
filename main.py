import os
import json
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

# Bosqichlar
ASK_ROLE, ASK_NAME, ASK_PHONE, MAIN_MENU, WAIT_PHOTO, = range(5)
user_info = {}

def get_sheet():
    creds = Credentials.from_service_account_info(
        json.loads(CREDS_JSON),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds).open_by_key(SPREADSHEET_ID).worksheet("davomat")

def now():
    return datetime.now(pytz.timezone("Asia/Tashkent"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info[user_id] = {}
    btns = [
        [KeyboardButton("🧾 Kassir"), KeyboardButton("📦 Sklad xodimi")],
        [KeyboardButton("🧍 Sotuvchi")]
    ]
    await update.message.reply_text(
        "Assalomu alaykum! Lavozimingizni tanlang:",
        reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True)
    )
    return ASK_ROLE

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info[user_id]['role'] = update.message.text
    await update.message.reply_text("Ism familiyangizni kiriting:")
    return ASK_NAME

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info[user_id]['name'] = update.message.text
    btn = KeyboardButton("📞 Raqamni yuborish", request_contact=True)
    await update.message.reply_text(
        "Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup([[btn]], resize_keyboard=True)
    )
    return ASK_PHONE

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info[user_id]['phone'] = update.message.contact.phone_number
    btns = [[
        KeyboardButton("📍 Ishga keldim"),
        KeyboardButton("🏁 Ishdan ketdim"),
        KeyboardButton("👤 Profilim")
    ]]
    await update.message.reply_text(
        "✅ Ma'lumotlar saqlandi. Amal tanlang:",
        reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True)
    )
    return MAIN_MENU

async def main_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = update.message.text
    if msg == "📍 Ishga keldim":
        context.user_data['status'] = "kelish"
        await update.message.reply_text("📸 Ishga kelganingizni tasdiqlovchi rasm yuboring:")
        return WAIT_PHOTO
    elif msg == "🏁 Ishdan ketdim":
        context.user_data['status'] = "ketish"
        await update.message.reply_text("📸 Ishdan ketganingizni tasdiqlovchi rasm yuboring:")
        return WAIT_PHOTO
    elif msg == "👤 Profilim":
        data = user_info.get(user_id, {})
        prof = f"""👤 Sizning profilingiz:
📝 Ism: {data.get('name')}
🏢 Lavozim: {data.get('role')}
📞 Telefon: {data.get('phone')}
🆔 Telegram ID: {user_id}
"""
        await update.message.reply_text(prof)
        return MAIN_MENU
    else:
        await update.message.reply_text("Tugmalardan birini tanlang.")
        return MAIN_MENU

async def save_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_info.get(user_id, {})
    status = context.user_data.get('status')
    if not data or not status:
        await update.message.reply_text("Avval 'Ishga keldim' yoki 'Ishdan ketdim' tugmasini bosing!")
        return MAIN_MENU
    # Rasm va ma'lumotlarni saqlash
    t = now()
    sheet = get_sheet()
    sheet.append_row([
        t.strftime("%Y-%m-%d"),
        t.strftime("%H:%M:%S"),
        data.get('name'), data.get('role'), data.get('phone'),
        "Keldi" if status == "kelish" else "Ketdi",
        update.effective_user.username or "",
        str(user_id)
    ])
    photo_id = update.message.photo[-1].file_id
    group_msg = f"""📝 Xodim hisoboti

👤 Ism: {data.get('name')}
🏢 Lavozim: {data.get('role')}
📞 Telefon: {data.get('phone')}
⏰ Vaqt: {t.strftime('%Y-%m-%d %H:%M:%S')}
🔄 Harakat: {"Ishga keldi" if status=="kelish" else "Ishdan ketdi"}"""
    await context.bot.send_photo(
        chat_id=GROUP_CHAT_ID,
        photo=photo_id,
        caption=group_msg
    )
    await update.message.reply_text("✅ Qayd etildi. Amal tanlang:",
        reply_markup=ReplyKeyboardMarkup([[
            KeyboardButton("📍 Ishga keldim"),
            KeyboardButton("🏁 Ishdan ketdim"),
            KeyboardButton("👤 Profilim")
        ]], resize_keyboard=True)
    )
    context.user_data['status'] = None
    return MAIN_MENU

async def photo_outside(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Avval 'Ishga keldim' yoki 'Ishdan ketdim' tugmasini bosing!")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_PHONE: [MessageHandler(filters.CONTACT, main_menu)],
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_text),
                MessageHandler(filters.PHOTO, photo_outside)
            ],
            WAIT_PHOTO: [MessageHandler(filters.PHOTO, save_photo)]
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False
    )
    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
