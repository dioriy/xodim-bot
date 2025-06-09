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
    ApplicationBuilder, ContextTypes, CommandHandler,
    MessageHandler, ConversationHandler, filters
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

users = {}

ASK_ROLE, ASK_NAME, ASK_PHONE, KELISH_RASM, KETISH_RASM = range(5)

def get_sheet():
    creds = Credentials.from_service_account_info(
        json.loads(CREDS_JSON),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds).open_by_key(SPREADSHEET_ID).worksheet("davomat")

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
        "Assalomu alaykum!\n\nLavozimingizni tanlang:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ASK_ROLE

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users[user_id]['role'] = update.message.text
    await update.message.reply_text("Ism familiyangizni kiriting:")
    return ASK_NAME

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users[user_id]['name'] = update.message.text
    contact_btn = KeyboardButton("📞 Raqamni yuborish", request_contact=True)
    await update.message.reply_text(
        "Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True)
    )
    return ASK_PHONE

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users[user_id]['phone'] = update.message.contact.phone_number
    await update.message.reply_text(
        "✅ Ma'lumotlar saqlandi. Amal tanlang:",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("📍 Ishga keldim"), KeyboardButton("🏁 Ishdan ketdim"), KeyboardButton("👤 Profilim")]
        ], resize_keyboard=True)
    )
    return ConversationHandler.END

async def kelish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Ishga kelganingizni tasdiqlovchi rasm yuboring:")
    return KELISH_RASM

async def ketish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Ishdan ketganingizni tasdiqlovchi rasm yuboring:")
    return KETISH_RASM

async def handle_kelish_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_photo(update, context, "kelish")

async def handle_ketish_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_photo(update, context, "ketish")

async def process_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, action_type: str):
    user = update.effective_user
    user_id = user.id
    data = users.get(user_id)
    if not data or 'name' not in data:
        await update.message.reply_text("❗ Avval /start buyrug'i bilan ro'yxatdan o'ting.")
        return ConversationHandler.END

    try:
        current_time = get_time()
        sheet_data = [
            current_time.strftime("%Y-%m-%d"),
            current_time.strftime("%H:%M:%S"),
            data['name'],
            data['role'],
            data['phone'],
            "Keldi" if action_type == "kelish" else "Ketdi",
            user.username or "N/A",
            str(user_id)
        ]

        sheet = get_sheet()
        sheet.append_row(sheet_data)

        # Rasmni guruhga tashlash
        photo_file_id = update.message.photo[-1].file_id
        group_message = f"""
📝 Xodim hisoboti

👤 Ism: {data['name']}
🏢 Lavozim: {data['role']}
📞 Telefon: {data['phone']}
⏰ Vaqt: {current_time.strftime('%Y-%m-%d %H:%M:%S')}
🔄 Harakat: {"Ishga keldi" if action_type == "kelish" else "Ishdan ketdi"}
"""
        await context.bot.send_photo(
            chat_id=GROUP_CHAT_ID,
            photo=photo_file_id,
            caption=group_message
        )

        action_text = "ishga kelganingiz" if action_type == "kelish" else "ishdan ketganingiz"
        await update.message.reply_text(
            f"✅ Qayd etildi.\n"
            f"⏰ {current_time.strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("📍 Ishga keldim"), KeyboardButton("🏁 Ishdan ketdim"), KeyboardButton("👤 Profilim")]
            ], resize_keyboard=True)
        )
    except Exception as e:
        await update.message.reply_text(
            f"❗ Xatolik: {str(e)}"
        )
    return ConversationHandler.END

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = users.get(user_id)
    if not data or 'name' not in data:
        await update.message.reply_text("❗ Avval /start buyrug'i bilan ro'yxatdan o'ting.")
        return
    profile_text = f"""
👤 Sizning profilingiz:

📝 Ism: {data['name']}
🏢 Lavozim: {data['role']}
📞 Telefon: {data['phone']}
🆔 Telegram ID: {user_id}
"""
    await update.message.reply_text(
        profile_text,
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("📍 Ishga keldim"), KeyboardButton("🏁 Ishdan ketdim"), KeyboardButton("👤 Profilim")]
        ], resize_keyboard=True)
    )

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if user_id not in users or 'name' not in users[user_id]:
        await update.message.reply_text("❗ Avval /start buyrug'i bilan ro'yxatdan o'ting.")
        return
    if text == "📍 Ishga keldim":
        return await kelish(update, context)
    elif text == "🏁 Ishdan ketdim":
        return await ketish(update, context)
    elif text == "👤 Profilim":
        await show_profile(update, context)
    else:
        await update.message.reply_text(
            "Iltimos, tugmalardan birini tanlang:",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("📍 Ishga keldim"), KeyboardButton("🏁 Ishdan ketdim"), KeyboardButton("👤 Profilim")]
            ], resize_keyboard=True)
        )

async def handle_invalid_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users or 'name' not in users[user_id]:
        await update.message.reply_text("❗ Avval /start buyrug'i bilan ro'yxatdan o'ting.")
        return
    await update.message.reply_text(
        "❗ Avval 'Ishga keldim' yoki 'Ishdan ketdim' tugmasini bosing, keyin rasm yuboring.",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("📍 Ishga keldim"), KeyboardButton("🏁 Ishdan ketdim"), KeyboardButton("👤 Profilim")]
        ], resize_keyboard=True)
    )

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_PHONE: [MessageHandler(filters.CONTACT, show_menu)],
            KELISH_RASM: [MessageHandler(filters.PHOTO, handle_kelish_photo)],
            KETISH_RASM: [MessageHandler(filters.PHOTO, handle_ketish_photo)],
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False
    )
    # ENG MUHIM QATORLAR!
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    application.add_handler(MessageHandler(filters.PHOTO, handle_invalid_photo))
    application.run_polling()

if __name__ == "__main__":
    main()
