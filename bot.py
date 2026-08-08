import os
import threading
import asyncio
import logging
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USERNAME = "@Sefvhra"

if not TOKEN:
    print("❌ توکن تنظیم نشده است!")
    exit(1)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ================== هندلرهای ربات ==================
async def send_login_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    report_text = (
        f"🚀 **کاربر جدید وارد شد!**\n"
        f"🆔 آیدی عددی: `{user.id}`\n"
        f"👤 نام کاربری: @{user.username or 'ندارد'}\n"
        f"📛 نام کامل: {user.full_name}"
    )
    try:
        photos = await context.bot.get_user_profile_photos(user.id)
        if photos.total_count > 0:
            await context.bot.send_photo(
                chat_id=ADMIN_USERNAME,
                photo=photos.photos[0][-1].file_id,
                caption=report_text,
                parse_mode='Markdown'
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_USERNAME,
                text=report_text + "\n⚠️ بدون پروفایل",
                parse_mode='Markdown'
            )
        print(f"📤 گزارش ورود کاربر {user.id} به {ADMIN_USERNAME} ارسال شد.")
    except Exception as e:
        print(f"⚠️ خطا در ارسال گزارش به ادمین: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_login_report(update, context)
    await update.message.reply_text("👋 سلام! ربات روشن است. هر پیامی بفرستید تا پاسخ دریافت کنید.")

async def catch_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📩 پیام شما دریافت شد: {update.message.text}")

# ================== راه‌اندازی ربات در یک Thread جداگانه ==================
def run_bot():
    # یک حلقه رویداد جدید برای این Thread ایجاد می‌کنیم
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, catch_all))

    # حذف وب‌هوک قبلی (برای جلوگیری از Conflict)
    loop.run_until_complete(app.bot.delete_webhook(drop_pending_updates=True))
    print("🔴 وب‌هوک پاک شد.")

    print("🤖 ربات روشن شد و منتظر پیام‌هاست.")
    app.run_polling()  # این در همان حلقه اجرا می‌شود

# ================== سرور Flask برای رندر ==================
app = Flask(__name__)

@app.route('/')
def health():
    return "ربات زنده است!"

# ================== اجرای اصلی ==================
if __name__ == '__main__':
    # اجرای ربات در یک Thread جداگانه
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # اجرای سرور Flask در Thread اصلی
    port = int(os.environ.get('PORT', 10000))
    print(f"🌐 سرور وب روی پورت {port} باز شد.")
    app.run(host='0.0.0.0', port=port)
