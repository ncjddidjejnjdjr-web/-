import os
import asyncio
import logging
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("❌ خطا: متغیر محیطی BOT_TOKEN تنظیم نشده است!")
    exit(1)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --------------------------------------------------
# هندلرهای ربات
# --------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ ربات زنده است! برای تست هر پیامی بفرستید.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📩 شما گفتید: {update.message.text}")

# --------------------------------------------------
# تنظیمات ربات
# --------------------------------------------------
async def run_bot():
    # ساخت اپلیکیشن
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # حذف وب‌هوک قبلی (برای جلوگیری از Conflict)
    await app.bot.delete_webhook(drop_pending_updates=True)
    print("🔴 وب‌هوک قبلی پاک شد.")

    # شروع پولینگ
    await app.initialize()
    await app.updater.start_polling()
    print("🤖 ربات روشن شد و منتظر پیام‌هاست...")
    
    # اینجا برنامه را متوقف نمی‌کنیم، بلکه آن را به عنوان یک Task نگه می‌داریم
    # تا به‌همراه سرور اجرا شود.
    # در واقع `run_polling` به‌صورت غیرمسدودکننده کار می‌کند.
    # ما باید یک `Future` برای جلوگیری از پایان برنامه ایجاد کنیم.
    stop_signal = asyncio.Future()
    await stop_signal

# --------------------------------------------------
# وب‌سرور aiohttp برای رندر (روی پورت ۱۰۰۰۰)
# --------------------------------------------------
async def handle_health(request):
    return web.Response(text="ربات زنده است!")

async def run_web_server():
    app = web.Application()
    app.router.add_get('/', handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 سرور وب روی پورت {port} باز شد.")
    # مانند ربات، این هم به یک Future نیاز دارد تا متوقف نشود
    await asyncio.Future()

# --------------------------------------------------
# اجرای همزمان هر دو در یک حلقه
# --------------------------------------------------
async def main():
    # اجرای ربات و سرور به‌صورت همزمان
    await asyncio.gather(
        run_bot(),
        run_web_server()
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("ربات متوقف شد.")
