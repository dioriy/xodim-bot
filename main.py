
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

# Store user data and states
users = {}
user_states = {}

# Conversation states
ASK_ROLE, ASK_NAME, ASK_PHONE, KELISH_RASM, KETISH_RASM = range(5)

def get_sheet():
    """Initialize Google Sheets connection"""
    try:
        creds = Credentials.from_service_account_info(
            json.loads(CREDS_JSON),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        return gspread.authorize(creds).open_by_key(SPREADSHEET_ID).worksheet("davomat")
    except Exception as e:
        print(f"Google Sheets error: {e}")
        return None

def get_time():
    """Get current time in Tashkent timezone"""
    return datetime.now(pytz.timezone("Asia/Tashkent"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user_id = update.effective_user.id
    users[user_id] = {}
    user_states[user_id] = None
    
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
    """Handle role selection"""
    user_id = update.effective_user.id
    users[user_id]['role'] = update.message.text
    await update.message.reply_text("Iltimos, ism familiyangizni to'liq kiriting:")
    return ASK_NAME

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle name input"""
    user_id = update.effective_user.id
    users[user_id]['name'] = update.message.text
    contact_btn = KeyboardButton("📞 Raqamni yuborish", request_contact=True)
    await update.message.reply_text(
        "Iltimos, telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True)
    )
    return ASK_PHONE

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone number and show main menu"""
    user_id = update.effective_user.id
    users[user_id]['phone'] = update.message.contact.phone_number
    user_states[user_id] = None
    
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
    """Handle 'came to work' button"""
    user_id = update.effective_user.id
    user_states[user_id] = "kelish"
    await update.message.reply_text("📸 Iltimos, ishga kelganingiz haqida rasm yuboring:")
    return KELISH_RASM

async def ketish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'left work' button"""
    user_id = update.effective_user.id
    user_states[user_id] = "ketish"
    await update.message.reply_text("📸 Iltimos, ishdan ketganingiz haqida rasm yuboring:")
    return KETISH_RASM

async def handle_kelish_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo for coming to work"""
    return await process_photo(update, context, "kelish")

async def handle_ketish_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo for leaving work"""
    return await process_photo(update, context, "ketish")

async def process_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, action_type: str):
    """Process uploaded photo and save to Google Sheets"""
    user = update.effective_user
    user_id = user.id
    data = users.get(user_id)
    
    if not data or 'name' not in data:
        await update.message.reply_text("❗ Avval /start buyrug'i bilan ro'yxatdan o'ting.")
        return ConversationHandler.END

    try:
        # Get current time
        current_time = get_time()
        
        # Format data for Google Sheets
        sheet_data = [
            current_time.strftime("%Y-%m-%d"),  # Date
            current_time.strftime("%H:%M:%S"),  # Time
            data['name'],                       # Name
            data['role'],                       # Role
            data['phone'],                      # Phone
            "Keldi" if action_type == "kelish" else "Ketdi",  # Action
            user.username or "N/A",             # Telegram username
            str(user_id)                        # Telegram user ID
        ]
        
        # Save to Google Sheets
        sheet = get_sheet()
        if sheet:
            sheet.append_row(sheet_data)
            print(f"Data saved to Google Sheets: {sheet_data}")
        else:
            print("Failed to connect to Google Sheets")
        
        # Send to group chat if configured
        if GROUP_CHAT_ID:
            group_message = f"""
📝 Xodim hisoboti

👤 Ism: {data['name']}
🏢 Lavozim: {data['role']}
📞 Telefon: {data['phone']}
⏰ Vaqt: {current_time.strftime('%Y-%m-%d %H:%M:%S')}
🔄 Harakat: {"Ishga keldi" if action_type == "kelish" else "Ishdan ketdi"}
"""
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=group_message
            )
        
        # Send confirmation to user
        action_text = "ishga kelganingiz" if action_type == "kelish" else "ishdan ketganingiz"
        await update.message.reply_text(
            f"✅ Rasm qabul qilindi! {action_text.capitalize()} qayd etildi.\n"
            f"⏰ Vaqt: {current_time.strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=ReplyKeyboardMarkup([[ 
                KeyboardButton("📍 Ishga keldim"),
                KeyboardButton("🏁 Ishdan ketdim"),
                KeyboardButton("👤 Profilim")
            ]], resize_keyboard=True)
        )
        
        # Reset user state
        user_states[user_id] = None
        
    except Exception as e:
        print(f"Error processing photo: {e}")
        await update.message.reply_text(
            f"❗ Xatolik yuz berdi: {str(e)}\nIltimos, qaytadan urinib ko'ring."
        )
    
    return ConversationHandler.END

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile"""
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
        reply_markup=ReplyKeyboardMarkup([[ 
            KeyboardButton("📍 Ishga keldim"),
            KeyboardButton("🏁 Ishdan ketdim"),
            KeyboardButton("👤 Profilim")
        ]], resize_keyboard=True)
    )

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages outside conversation"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Check if user is registered
    if user_id not in users or 'name' not in users[user_id]:
        await update.message.reply_text("❗ Avval /start buyrug'i bilan ro'yxatdan o'ting.")
        return
    
    # Handle menu buttons
    if text == "📍 Ishga keldim":
        await kelish(update, context)
    elif text == "🏁 Ishdan ketdim":
        await ketish(update, context)
    elif text == "👤 Profilim":
        await show_profile(update, context)
    else:
        await update.message.reply_text(
            "Iltimos, quyidagi tugmalardan birini tanlang:",
            reply_markup=ReplyKeyboardMarkup([[ 
                KeyboardButton("📍 Ishga keldim"),
                KeyboardButton("🏁 Ishdan ketdim"),
                KeyboardButton("👤 Profilim")
            ]], resize_keyboard=True)
        )

async def handle_invalid_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos sent without proper state"""
    user_id = update.effective_user.id
    
    if user_id not in users or 'name' not in users[user_id]:
        await update.message.reply_text("❗ Avval /start buyrug'i bilan ro'yxatdan o'ting.")
        return
    
    await update.message.reply_text(
        "❗ Avval 'Ishga keldim' yoki 'Ishdan ketdim' tugmasini bosing, keyin rasm yuboring.",
        reply_markup=ReplyKeyboardMarkup([[ 
            KeyboardButton("📍 Ishga keldim"),
            KeyboardButton("🏁 Ishdan ketdim"),
            KeyboardButton("👤 Profilim")
        ]], resize_keyboard=True)
    )

def main():
    """Main function to run the bot"""
    print("Starting bot...")
    
    # Create application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Create conversation handler for registration
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
    
    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    application.add_handler(MessageHandler(filters.PHOTO, handle_invalid_photo))
    
    # Start bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
