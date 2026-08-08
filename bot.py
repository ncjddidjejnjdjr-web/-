import os
import asyncio
import logging
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_TARGET = os.getenv("ADMIN_TARGET", "7809557665")

if not TOKEN:
    print("❌ خطا: متغیر BOT_TOKEN تنظیم نشده است!")
    exit(1)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ======= این هندلر به هر چیزی که کاربر بفرستد جواب می‌دهد =======
async def catch_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # دریافت متن پیام (اگر استیکر یا عکس باشد، خالی برمی‌گردد)
    user_text = update.message.text if update.message.text else "استیکر یا عکس یا ویدیو"
    
    # 📢 چاپ دقیق در لاگ‌های رندر (تا ببینیم ربات پیام‌ها را می‌بیند یا نه!)
    print(f"📩 [لاگ ربات] پیام دریافت شد از {user_id}: '{user_text}'")
    
    # ارسال یک پاسخ ساده به کاربر (برای تست)
    await update.message.reply_text(f"پیام شما ('{user_text}') دریافت شد! ربات زنده است. ✅")

# ======= هندلر تست ارسال به ادمین =======
async def admin_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("📣 اجرای دستور تست ادمین...")
    try:
        await context.bot.send_message(chat_id=ADMIN_TARGET, text="این یک پیام تستی از ربات به ادمین است. زنده است!")
        await update.message.reply_text("پیام تست به ادمین ارسال شد.")
    except Exception as e:
        print(f"❌ خطا در ارسال به ادمین: {e}")

# ======= تنظیمات ربات =======
async def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # هندلر ALL برای گرفتن همه‌ی نوع پیام‌ها
    app.add_handler(MessageHandler(filters.ALL, catch_all))
    # هندلر دستور تست ادمین
    app.add_handler(CommandHandler("admin_test", admin_test))

    # حذف وب‌هوک (برای جلوگیری از Conflict)
    await app.bot.delete_webhook(drop_pending_updates=True)
    print("🔴 وب‌هوک قبلی پاک شد.")
    
    await app.initialize()
    await app.updater.start_polling()
    print("🤖 ربات تست (با لاگ‌گذاری) روشن شد و منتظر پیام‌هاست...")
    
    await asyncio.Future()

# ======= سرور وب برای رندر =======
async def run_web_server():
    app = web.Application()
    async def health(request):
        return web.Response(text="ربات زنده است!")
    app.router.add_get('/', health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 سرور وب روی پورت {port} باز شد.")
    await asyncio.Future()

# ======= اجرای همزمان =======
async def main():
    await asyncio.gather(run_bot(), run_web_server())

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("ربات متوقف شد.")
