
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
ASK_ROLE, ASK_NAME, ASK_PHONE, KELISH_RASM, KETISH_RASM = range(5)

def get_sheet():
    try:
        creds = Credentials.from_service_account_info(
            json.loads(CREDS_JSON),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        return gspread.authorize(creds).open_by_key(SPREADSHEET_ID).worksheet("davomat")
    except Exception as e:
        print(f"Google Sheets xatolik: {e}")
        return None

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
    await update.message.reply_text("Iltimos, ism familiyangizni to'liq kiriting:")
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
    else:
        users[update.effective_user.id]['phone'] = update.message.text
    
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
    user_id = update.effective_user.id
    if user_id not in users or 'name' not in users[user_id]:
        await update.message.reply_text("❗ Avval /start buyrug'i bilan ro'yxatdan o'ting.")
        return ConversationHandler.END
    
    await update.message.reply_text("📸 Iltimos, ishga kelganingiz haqida rasm yuboring")
    return KELISH_RASM

async def ketish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users or 'name' not in users[user_id]:
        await update.message.reply_text("❗ Avval /start buyrug'i bilan ro'yxatdan o'ting.")
        return ConversationHandler.END
    
    await update.message.reply_text("📸 Iltimos, ishdan ketganingiz haqida rasm yuboring")
    return KETISH_RASM

async def kelish_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❗ Iltimos, rasm yuboring!")
        return KELISH_RASM
    
    await process_rasm(update, context, "kelish")
    return ConversationHandler.END

async def ketish_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❗ Iltimos, rasm yuboring!")
        return KETISH_RASM
    
    await process_rasm(update, context, "ketish")
    return ConversationHandler.END

async def process_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE, holat: str):
    user = update.effective_user
    user_id = user.id
    data = users.get(user_id)
    
    if not data or 'name' not in data:
        await update.message.reply_text("❗ Avval /start buyrug'i bilan ro'yxatdan o'ting.")
        return ConversationHandler.END

    try:
        vaqt = get_time()
        vaqt_str = vaqt.strftime("%Y-%m-%d %H:%M:%S")
        
        sheet = get_sheet()
        if sheet:
            sheet.append_row([
                data['name'],
                data['role'], 
                data['phone'],
                holat,
                vaqt_str
            ])
        
        # Guruhga xabar yuborish
        if GROUP_CHAT_ID:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            
            caption = f"""
👤 Xodim: {data['name']}
💼 Lavozim: {data['role']}
📞 Telefon: {data['phone']}
📅 Vaqt: {vaqt_str}
📍 Holat: {"Ishga keldi" if holat == "kelish" else "Ishdan ketdi"}
            """
            
            await context.bot.send_photo(
                chat_id=GROUP_CHAT_ID,
                photo=file.file_id,
                caption=caption.strip()
            )
        
        await update.message.reply_text(
            f"✅ {holat.capitalize()} vaqti muvaffaqiyatli qayd qilindi!\n"
            f"⏰ Vaqt: {vaqt_str}",
            reply_markup=ReplyKeyboardMarkup([[ 
                KeyboardButton("📍 Ishga keldim"),
                KeyboardButton("🏁 Ishdan ketdim"),
                KeyboardButton("👤 Profilim")
            ]], resize_keyboard=True)
        )
        
    except Exception as e:
        print(f"Xatolik: {e}")
        await update.message.reply_text(
            f"❗️ Xatolik yuz berdi: {str(e)}",
            reply_markup=ReplyKeyboardMarkup([[ 
                KeyboardButton("📍 Ishga keldim"),
                KeyboardButton("🏁 Ishdan ketdim"),
                KeyboardButton("👤 Profilim")
            ]], resize_keyboard=True)
        )

async def profil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = users.get(user_id)
    
    if not data or 'name' not in data:
        await update.message.reply_text("❗ Avval /start buyrug'i bilan ro'yxatdan o'ting.")
        return
    
    profil_text = f"""
👤 Ism: {data['name']}
💼 Lavozim: {data['role']}
📞 Telefon: {data['phone']}
    """
    
    await update.message.reply_text(profil_text.strip())

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Amal bekor qilindi",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def main():
    if not BOT_TOKEN:
        print("❗ BOT_TOKEN topilmadi!")
        return
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Ro'yxatdan o'tish conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_PHONE: [MessageHandler(filters.CONTACT | filters.TEXT, show_menu)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Kelish conversation handler
    kelish_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📍 Ishga keldim$"), kelish)],
        states={
            KELISH_RASM: [MessageHandler(filters.PHOTO, kelish_rasm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Ketish conversation handler
    ketish_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🏁 Ishdan ketdim$"), ketish)],
        states={
            KETISH_RASM: [MessageHandler(filters.PHOTO, ketish_rasm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv_handler)
    app.add_handler(kelish_handler)
    app.add_handler(ketish_handler)
    app.add_handler(MessageHandler(filters.Regex("^👤 Profilim$"), profil))
    
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
