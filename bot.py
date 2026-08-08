import os
import logging
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USERNAME = "@Sefvhra"

if not TOKEN:
    print("❌ توکن تنظیم نشده است!")
    exit(1)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

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

async def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, catch_all))

    PORT = int(os.environ.get('PORT', 10000))
    WEBHOOK_URL = os.getenv("RAILWAY_PUBLIC_DOMAIN")  # ریلوی خودکار این آدرس را می‌دهد

    if not WEBHOOK_URL:
        print("⚠️ متغیر RAILWAY_PUBLIC_DOMAIN تنظیم نشده! با Webhook کار نمی‌کند.")
        return

    print(f"🌐 در حال تنظیم Webhook روی https://{WEBHOOK_URL}...")
    await application.bot.set_webhook(url=f"https://{WEBHOOK_URL}")
    print("✅ Webhook تنظیم شد! ربات منتظر پیام‌هاست.")
    
    await application.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=f"https://{WEBHOOK_URL}")

if __name__ == '__main__':
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("ربات متوقف شد.")
