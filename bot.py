import os
import logging
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USERNAME = "@Sefvhra"  # اگر بعداً گزارش می‌خواهید

if not TOKEN:
    print("❌ توکن تنظیم نشده است!")
    exit(1)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ========== هندلرها (برای تست سریع) ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📢 [Webhook] دستور /start دریافت شد از {update.effective_user.id}")
    await update.message.reply_text("👋 ربات با Webhook روشن شد! پاسخ فوری است.")

async def catch_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📢 [Webhook] پیام: '{update.message.text}' از {update.effective_user.id}")
    await update.message.reply_text(f"📩 فوراً دریافت شد: '{update.message.text}'")

# ========== تنظیم ربات با Webhook ==========
async def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, catch_all))

    # پورت رندر و آدرس وب‌هوک
    PORT = int(os.environ.get('PORT', 10000))
    WEBHOOK_URL = "https://gard-9r3g.onrender.com"  # آدرس ثابت رندر

    print(f"🌐 در حال تنظیم Webhook روی {WEBHOOK_URL}...")
    
    # در اینجا وب‌هوک را مستقیماً تنظیم می‌کنیم. ربات با این روش دیگر Conflict نمی‌دهد.
    await application.bot.set_webhook(url=WEBHOOK_URL)
    print("✅ Webhook با موفقیت تنظیم شد!")

    # سرور aiohttp برای گوش دادن به درخواست‌های تلگرام روی همان پورت
    # این جایگزین run_polling می‌شود.
    await application.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=WEBHOOK_URL)

if __name__ == '__main__':
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("ربات متوقف شد.")
