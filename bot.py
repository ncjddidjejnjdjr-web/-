import os
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("❌ توکن تنظیم نشده است!")
    exit(1)

async def reply_to_anything(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! ربات سالم است. (تست ساده)")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("شما /start را زدید. ربات کار می‌کند!")

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # هندلر برای هر متن
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_to_anything))
    # هندلر برای /start
    app.add_handler(CommandHandler("start", start))
    
    await app.initialize()
    await app.updater.start_polling()
    print("🤖 ربات تست روشن شد و آماده دریافت پیام است!")
    
    # سرور aiohttp برای رندر
    from aiohttp import web
    async def health(request):
        return web.Response(text="ربات زنده است!")
    web_app = web.Application()
    web_app.router.add_get('/', health)
    runner = web.AppRunner(web_app)
    await runner.setup()
    PORT = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"🌐 سرور وب روی پورت {PORT} باز شد.")
    
    await asyncio.Future()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("ربات متوقف شد.")
