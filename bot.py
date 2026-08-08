import os
import asyncio
from telegram import Bot

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("❌ توکن تنظیم نشده است!")
    exit(1)

async def clear_webhook():
    print("🧹 در حال پاک کردن تمام وب‌هوک‌های قبلی...")
    bot = Bot(token=TOKEN)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ وب‌هوک با موفقیت پاک شد! حالا ربات را متوقف می‌کنم.")
    except Exception as e:
        print(f"⚠️ خطا در پاک کردن وب‌هوک: {e}")

if __name__ == '__main__':
    asyncio.run(clear_webhook())
