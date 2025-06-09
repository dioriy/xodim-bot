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
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds).open_by_key(SPREADSHEET_ID).sheet1

def get_time():
    return datetime.now(pytz.timezone("Asia/Tashkent"))

KEL = KET = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[KeyboardButton("📍 Kelish")], [KeyboardButton("🏁 Ketish")], [KeyboardButton("👤 Profilim")]]
    await update.message.reply_text("Assalomu alaykum! Amalni tanlang:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def kel_start(update, context):
    await update.message.reply_text("Rasm yubor...", reply_markup=ReplyKeyboardRemove()); return KEL

async def kel_done(update, context):
    u = update.effective_user; ph = update.message.photo[-1]; file = await ph.get_file()
    t = get_time(); tstr = t.strftime("%H:%M"); date = t.strftime("%Y-%m-%d")
    sh = get_sheet(); rs = sh.get_all_records()
    r = next((i for i,rec in enumerate(rs, start=2) if str(rec["Telegram ID"])==str(u.id) and rec["Sana"]==date), None)
    if r: sh.update_cell(r,4,tstr)
    else: sh.append_row([date,str(u.id),u.full_name,tstr,"",""])
    await context.bot.send_photo(chat_id=GROUP_CHAT_ID, photo=file.file_id, caption=f"✅ Kelgan — {u.full_name}\n🕒 {tstr}", parse_mode="Markdown")
    await update.message.reply_text("Kelish yozildi."); return ConversationHandler.END

async def ket_start(update, context):
    await update.message.reply_text("Rasm yubor...", reply_markup=ReplyKeyboardRemove()); return KET

async def ket_done(update, context):
    u = update.effective_user; ph = update.message.photo[-1]; file = await ph.get_file()
    t = get_time(); tstr = t.strftime("%H:%M"); date = t.strftime("%Y-%m-%d")
    sh = get_sheet(); rs = sh.get_all_records()
    r = next((i for i,rec in enumerate(rs, start=2) if str(rec["Telegram ID"])==str(u.id) and rec["Sana"]==date), None)
    if r:
        sh.update_cell(r,5,tstr)
        t0 = sh.cell(r,4).value
        if t0:
            h = round((datetime.strptime(tstr,"%H:%M")-datetime.strptime(t0,"%H:%M")).seconds/3600,2)
            sh.update_cell(r,6,str(h))
    else:
        sh.append_row([date,str(u.id),u.full_name,"",tstr,""])
    await context.bot.send_photo(chat_id=GROUP_CHAT_ID, photo=file.file_id, caption=f"🏁 Ketgan — {u.full_name}\n🕒 {tstr}", parse_mode="Markdown")
    await update.message.reply_text("Ketish yozildi."); return ConversationHandler.END

async def profil(update, context):
    u = update.effective_user; sh=get_sheet(); rs=sh.get_all_records()
    days=0; hrs=0.0
    for rec in rs:
        if str(rec["Telegram ID"])==str(u.id):
            days+=1; try: hrs+=float(rec.get("Ishlagan vaqt (soat)",0))
            except: pass
    await update.message.reply_text(f"👤 {u.full_name}\n📆 Kunlar: {days}\n🕒 Soatlar: {round(hrs,2)}")

async def cancel(update,context):
    await update.message.reply_text("Bekor",reply_markup=ReplyKeyboardRemove()); return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    ch = ConversationHandler(entry_points=[MessageHandler(filters.Regex("^📍 Kelish$"),kel_start),
                                            MessageHandler(filters.Regex("^🏁 Ketish$"),ket_start)],
                             states={KEL:[MessageHandler(filters.PHOTO,kel_done)],KET:[MessageHandler(filters.PHOTO,ket_done)]},
                             fallbacks=[CommandHandler("cancel", cancel)])
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ch)
    app.add_handler(MessageHandler(filters.Regex("^👤 Profilim$"),profil))
    print("Bot polling started...")  # bu yerda log yozuvi
    app.run_polling()

if __name__=="__main__": main()
