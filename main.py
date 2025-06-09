
import os
import json
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
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
ASK_ROLE, ASK_NAME, ASK_PHONE, KELISH_RASM, KETISH_RASM, MAIN_MENU = range(6)

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
        "Assalomu alaykum, ANT Xodim botiga xush kelibsiz!\n\nIltimos, lavozimingizni tanlang:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ASK_ROLE

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id]['role'] = update.message.text
    await update.message.reply_text(
        "Iltimos, ism familiyangizni to'liq kiriting:",
        reply_markup=ReplyKeyboardRemove()
    )
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
    if update.message.contact:
        users[update.effective_user.id]['phone'] = update.message.contact.phone_number
    
    keyboard = [
        [KeyboardButton("📍 Ishga keldim"), KeyboardButton("🏁 Ishdan ketdim")],
        [KeyboardButton("👤 Profilim")]
    ]
    await update.message.reply_text(
        "✅ Ma'lumotlar qabul qilindi. Endi kerakli amalni tanlang:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return MAIN_MENU

async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "📍 Ishga keldim":
        await update.message.reply_text("📸 Iltimos, ishga kelganingiz haqida rasm yuboring")
        return KELISH_RASM
    elif text == "🏁 Ishdan ketdim":
        await update.message.reply_text("📸 Iltimos, ishdan ketganingiz haqida rasm yuboring")
        return KETISH_RASM
    elif text == "👤 Profilim":
        user_id = update.effective_user.id
        data = users.get(user_id, {})
        profile_text = f"👤 Profil ma'lumotlari:\n\n"
        profile_text += f"📋 Lavozim: {data.get('role', 'Noma\'lum')}\n"
        profile_text += f"👤 Ism: {data.get('name', 'Noma\'lum')}\n"
        profile_text += f"📞 Telefon: {data.get('phone', 'Noma\'lum')}"
        await update.message.reply_text(profile_text)
        return MAIN_MENU
    else:
        await update.message.reply_text("Iltimos, tugmalardan birini tanlang.")
        return MAIN_MENU

async def process_kelish_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_rasm(update, context, "kelish")
    return MAIN_MENU

async def process_ketish_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_rasm(update, context, "ketish")
    return MAIN_MENU

async def process_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE, holat: str):
    user = update.effective_user
    user_id = user.id
    data = users.get(user_id)
    
    if not data or 'name' not in data:
        await update.message.reply_text("❗ Avval /start buyrug'i bilan ro'yxatdan o'ting.")
        return

    try:
        if not update.message.photo:
            await update.message.reply_text("❗ Iltimos, rasm yuboring.")
            return

        photo = update.message.photo[-1]
        file = await photo.get_file()
        
        vaqt = get_time()
        sana = vaqt.strftime("%Y-%m-%d")
        soat = vaqt.strftime("%H:%M:%S")
        
        # Google Sheets ga yozish
        sheet = get_sheet()
        
        # Foydalanuvchi ma'lumotlarini olish
        ism = data.get('name', 'Noma\'lum')
        lavozim = data.get('role', 'Noma\'lum')
        telefon = data.get('phone', 'Noma\'lum')
        
        # Yangi qator qo'shish
        if holat == "kelish":
            qator = [sana, ism, lavozim, telefon, soat, "", "Kelish"]
            await update.message.reply_text("✅ Ishga kelganingiz qayd etildi!")
        else:
            qator = [sana, ism, lavozim, telefon, "", soat, "Ketish"]
            await update.message.reply_text("✅ Ishdan ketganingiz qayd etildi!")
        
        sheet.append_row(qator)
        
        # Guruhga xabar yuborish
        if GROUP_CHAT_ID:
            xabar = f"📊 Davomat:\n\n"
            xabar += f"👤 {ism}\n"
            xabar += f"📋 {lavozim}\n"
            xabar += f"📅 {sana}\n"
            xabar += f"🕐 {soat}\n"
            xabar += f"📍 {holat.capitalize()}"
            
            await context.bot.send_photo(
                chat_id=GROUP_CHAT_ID,
                photo=file.file_id,
                caption=xabar
            )
        
        # Menyu tugmalarini qaytarish
        keyboard = [
            [KeyboardButton("📍 Ishga keldim"), KeyboardButton("🏁 Ishdan ketdim")],
            [KeyboardButton("👤 Profilim")]
        ]
        await update.message.reply_text(
            "Yana kerakli amalni tanlang:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        
    except Exception as e:
        await update.message.reply_text(f"❗ Xatolik yuz berdi: {e}")
        print(f"Error: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Amal bekor qilindi. /start buyrug'i bilan qaytadan boshlang.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_PHONE: [MessageHandler(filters.CONTACT, show_menu)],
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_choice)],
            KELISH_RASM: [MessageHandler(filters.PHOTO, process_kelish_rasm)],
            KETISH_RASM: [MessageHandler(filters.PHOTO, process_ketish_rasm)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv_handler)
    
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
