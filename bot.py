import os
import threading
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask

# تنظیمات
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get('PORT', 10000))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("دستور استارت دریافت شد!")
    await update.message.reply_text("ربات تست سالم است! پورت روی ۱۰۰۰۰ باز است.")

def run_bot():
    import asyncio
    async def main():
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        print("🤖 ربات تست روشن شد و منتظر پیام است...")
        await app.run_polling()
    asyncio.run(main())

def run_webserver():
    app = Flask(__name__)
    @app.route('/')
    def home():
        return "ربات تست زنده است!"
    
    print(f"🌐 سرور تست روی پورت {PORT} باز شد.")
    app.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    # اجرای ربات در یک نخ جداگانه
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # اجرای سرور وب در نخ اصلی
    run_webserver()
