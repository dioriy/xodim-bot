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
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

ASK_ROLE, ASK_NAME, ASK_PHONE, MAIN_MENU, WAIT_PHOTO, WAIT_LOCATION = range(6)
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
    await update.message.reply_text("Ism familiyangizni kiriting:", reply_markup=ReplyKeyboardRemove())
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
    status = context.user_data.get('status')
    photo_id = update.message.photo[-1].file_id

    context.user_data['photo_id'] = photo_id

    await update.message.reply_text(
        "📍 Lokatsiyangizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("Lokatsiyani yuborish", request_location=True)]],
            resize_keyboard=True
        )
    )
    # Qaysi status ekanini keyingi bosqichga olib o‘tish
    context.user_data['kelish_uchun'] = (status == "kelish")
    return WAIT_LOCATION

async def save_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_info.get(user_id, {})
    t = now()
    photo_id = context.user_data.get('photo_id')
    loc = update.message.location
    sheet = get_sheet()
    kelish_uchun = context.user_data.get('kelish_uchun', True)

    if kelish_uchun:  # Ishga keldi
        sheet.append_row([
            t.strftime("%Y-%m-%d"),          # Sana
            t.strftime("%H:%M:%S"),          # Kelgan vaqt
            "",                              # Ketgan vaqt
            str(user_id),                    # Telegram ID
            data.get('name'),                # Ism familiya
            data.get('role'),                # Lavozim
            data.get('phone'),               # Telefon raqam
            "",                              # Ishlagan vaqt (soat)
            "Keldi",                         # Holat
            f"{loc.latitude},{loc.longitude}"# Lokatsiya
        ])
        group_msg = f"""📝 Xodim hisoboti

👤 Ism: {data.get('name')}
🏢 Lavozim: {data.get('role')}
📞 Telefon: {data.get('phone')}
⏰ Vaqt: {t.strftime('%Y-%m-%d %H:%M:%S')}
🔄 Harakat: Ishga keldi
"""
        await context.bot.send_photo(
            chat_id=GROUP_CHAT_ID,
            photo=photo_id,
            caption=group_msg
        )
        await context.bot.send_location(
            chat_id=GROUP_CHAT_ID,
            latitude=loc.latitude,
            longitude=loc.longitude
        )
    else:  # Ishdan ketdi
        rows = sheet.get_all_values()
        today = t.strftime("%Y-%m-%d")
        found_row = None
        for idx in range(len(rows)-1, 0, -1):
            row = rows[idx]
            if (
                row[0].strip() == today and
                str(row[3]).strip() == str(user_id).strip() and
                row[8].strip().lower() == "keldi" and
                row[2].strip() == ""
            ):
                found_row = idx+1  # Google Sheets 1-based
                break

        if found_row:
            ketgan_vaqt = t.strftime("%H:%M:%S")
            kelgan_vaqt = rows[found_row-1][1]
            fmt = "%H:%M:%S"
            try:
                t1 = datetime.strptime(kelgan_vaqt, fmt)
                t2 = datetime.strptime(ketgan_vaqt, fmt)
                farq = (t2-t1).total_seconds()/3600
                ishlagan_soat = round(farq if farq > 0 else (farq + 24), 2)
            except Exception:
                ishlagan_soat = ""

            sheet.update(f"C{found_row}", [[ketgan_vaqt]])
            sheet.update(f"H{found_row}", [[ishlagan_soat]])
            sheet.update(f"I{found_row}", [["Ketdi"]])
            sheet.update(f"J{found_row}", [[f"{loc.latitude},{loc.longitude}"]])

            group_msg = f"""📝 Xodim hisoboti

👤 Ism: {data.get('name')}
🏢 Lavozim: {data.get('role')}
📞 Telefon: {data.get('phone')}
⏰ Vaqt: {t.strftime('%Y-%m-%d %H:%M:%S')}
🔄 Harakat: Ishdan ketdi
"""
            await context.bot.send_photo(
                chat_id=GROUP_CHAT_ID,
                photo=photo_id,
                caption=group_msg
            )
            await context.bot.send_location(
                chat_id=GROUP_CHAT_ID,
                latitude=loc.latitude,
                longitude=loc.longitude
            )
        else:
            await update.message.reply_text("❌ Avval 'Ishga keldim'ni bosing!")
            return MAIN_MENU

    await update.message.reply_text("✅ Qayd etildi. Amal tanlang:",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("📍 Ishga keldim"), KeyboardButton("🏁 Ishdan ketdim"), KeyboardButton("👤 Profilim")]
        ], resize_keyboard=True)
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
            WAIT_PHOTO: [MessageHandler(filters.PHOTO, save_photo)],
            WAIT_LOCATION: [MessageHandler(filters.LOCATION, save_location)]
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False
    )
    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
