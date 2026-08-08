import os
import threading
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("❌ توکن تنظیم نشده است!")
    exit(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ ربات تست سالم است! دستور /start کار می‌کند.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📩 پیام شما دریافت شد: {update.message.text}")

def run_telegram_bot():
    # ایجاد یک حلقه رویداد جدید برای جلوگیری از خطای set_wakeup_fd
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("🤖 ربات ساده تلگرام در حال اجرا است...")
    app.run_polling()

app = Flask(__name__)

@app.route('/')
def home():
    return "ربات تست زنده است!"

if __name__ == '__main__':
    # اجرای ربات در یک ترد جداگانه
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()

    # اجرای وب‌سرور (Flask) در ترد اصلی برای باز نگه داشتن پورت
    port = int(os.environ.get('PORT', 10000))
    print(f"🌐 وب‌سرور روی پورت {port} باز شد.")
    app.run(host='0.0.0.0', port=port)
