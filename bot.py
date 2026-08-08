import os
import asyncio
import logging
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("❌ توکن تنظیم نشده است!")
    exit(1)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ========== هندلر دستور /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📢 [لاگ رندر] دستور /start دریافت شد از کاربر {update.effective_user.id}")
    await update.message.reply_text("👋 سلام! ربات تست زنده است. این پیام در لاگ ثبت شد.")

# ========== هندلر پاسخ به هر پیام ==========
async def catch_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📢 [لاگ رندر] پیام دریافت شد: '{update.message.text}' از کاربر {update.effective_user.id}")
    await update.message.reply_text(f"📩 دریافت شد: '{update.message.text}'")

# ========== تنظیمات ربات ==========
async def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, catch_all))

    await app.bot.delete_webhook(drop_pending_updates=True)
    print("🔴 وب‌هوک پاک شد.")

    await app.initialize()
    await app.updater.start_polling()
    print("🤖 ربات روشن شد و منتظر پیام‌هاست.")
    await asyncio.Future()

# ========== سرور وب برای رندر ==========
async def run_web_server():
    app = web.Application()
    async def health(request):
        return web.Response(text="ربات زنده است")
    app.router.add_get('/', health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 سرور وب روی پورت {port} باز شد.")
    await asyncio.Future()

# ========== اجرای همزمان ==========
async def main():
    await asyncio.gather(run_bot(), run_web_server())

if __name__ == '__main__':
    asyncio.run(main())
