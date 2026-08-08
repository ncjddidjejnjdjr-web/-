import os
import asyncio
import logging
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("❌ خطا: BOT_TOKEN تنظیم نشده است!")
    exit(1)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def catch_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📩 پیام دریافت شد از {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("✅ ربات تست زنده است! پیام شما دریافت شد.")

async def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, catch_all))

    await app.bot.delete_webhook(drop_pending_updates=True)
    print("🔴 وب‌هوک پاک شد.")

    await app.initialize()
    await app.updater.start_polling()
    print("🤖 ربات تست (حل Conflict) روشن شد.")
    await asyncio.Future()

async def run_web_server():
    app = web.Application()
    app.router.add_get('/', lambda _: web.Response(text="زنده است"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 سرور وب روی پورت {port} باز شد.")
    await asyncio.Future()

async def main():
    await asyncio.gather(run_bot(), run_web_server())

if __name__ == '__main__':
    asyncio.run(main())
