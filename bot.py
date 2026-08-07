import os
import re
import logging
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from openai import OpenAI

# ========== تنظیمات محیطی ==========
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_TARGET = os.getenv("ADMIN_TARGET", "7809557665")  # عدد خودتان
CHANNEL_ID = os.getenv("CHANNEL_ID")
STATIC_INVITE_LINK = os.getenv("STATIC_INVITE_LINK")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not STATIC_INVITE_LINK:
    STATIC_INVITE_LINK = "لینک کانال تنظیم نشده است."

if not TOKEN or not OPENAI_API_KEY:
    print("❌ متغیرهای محیطی BOT_TOKEN یا OPENAI_API_KEY تنظیم نشده‌اند!")
    exit(1)

client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://openrouter.ai/api/v1")
model = "meta-llama/llama-3.3-70b-instruct"

ASKING = 0
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# تابع پاکسازی متن
def clean_response_for_user(text):
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        if re.search(r'\b(if|else|print|chose|WIN|END)\b', line, re.IGNORECASE):
            continue
        cleaned.append(line)
    text = '\n'.join(cleaned)
    text = re.sub(r'[\*\_\#\`]', '', text)
    text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    return text

async def send_joined_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        info = f"🚀 **کاربر جدید**\n👤 @{user.username or 'ندارد'}\n🆔 {user.id}\n📛 {user.full_name}"
        photos = await context.bot.get_user_profile_photos(user.id)
        if photos.total_count > 0:
            await context.bot.send_photo(chat_id=ADMIN_TARGET, photo=photos.photos[0][-1].file_id, caption=info, parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=ADMIN_TARGET, text=info + "\n⚠️ بدون پروفایل", parse_mode='Markdown')
    except Exception:
        pass

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_joined_report(update, context)

    user = update.effective_user
    context.user_data['user_info'] = {'id': user.id, 'full_name': user.full_name, 'username': user.username or "ندارد"}
    context.user_data['history'] = []

    system_prompt = (
        "تو استاد فارسی‌زبان بازی 'بن‌بست فکری' هستی. "
        "فقط ۱ سوال فکری، مفهومی، فلسفی یا منطقی به فارسی بپرس. "
        "سوال ۴ گزینه‌ای با A, B, C, D و ۳ گزینه انحرافی. "
        "از توضیح اضافی بپرهیز. پاسخ صحیح را لو نده. "
        "در انتهای یک خط جدید بنویس WIN: یا END: و یک جمله تحلیل."
    )
    context.user_data['history'].append({"role": "system", "content": system_prompt})

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text("🧠 در حال ساختن ۱ سوال... یک لحظه صبر کن.")

    try:
        response = client.chat.completions.create(model=model, messages=context.user_data['history'])
        ai_raw = response.choices[0].message.content
        context.user_data['history'].append({"role": "assistant", "content": ai_raw})
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")
        return ConversationHandler.END

    clean_q = clean_response_for_user(ai_raw)
    await update.message.reply_text(
        f"🎯 فقط ۱ سوال فکری\n\n"
        f"🏆 جایزه: گزینه صحیح (A, B, C یا D) = لینک کانال خصوصی\n\n"
        f"------------\n"
        f"{clean_q}"
    )
    return ASKING

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_answer = update.message.text.strip().upper()
    context.user_data['history'].append({"role": "user", "content": user_answer})

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = client.chat.completions.create(model=model, messages=context.user_data['history'])
        ai_raw = response.choices[0].message.content
        context.user_data['history'].append({"role": "assistant", "content": ai_raw})
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")
        return ASKING

    is_win = re.search(r'^\s*WIN:', ai_raw, re.MULTILINE)
    is_end = re.search(r'^\s*END:', ai_raw, re.MULTILINE)
    clean_msg = clean_response_for_user(ai_raw)

    if is_win:
        await send_report_to_admin(update, context, "برنده شد")
        try:
            link = await context.bot.create_chat_invite_link(CHANNEL_ID)
            await update.message.reply_text(f"🎉 **تبریک!**\n\n🏆 لینک کانال:\n{link.invite_link}")
        except:
            await update.message.reply_text(f"🎉 لینک کانال:\n\n{STATIC_INVITE_LINK}")
        context.user_data.clear()
        return ConversationHandler.END

    elif is_end:
        await send_report_to_admin(update, context, "باخت")
        await update.message.reply_text(f"❌ **باختی!**\n{clean_msg}\n\nبرای تلاش مجدد /start بزن.")
        context.user_data.clear()
        return ConversationHandler.END

    else:
        await update.message.reply_text(f"{clean_msg}\n\n⚠️ فقط یکی از A, B, C یا D را بفرست.")
        return ASKING

async def send_report_to_admin(update, context, status):
    try:
        user = update.effective_user
        info = context.user_data['user_info']
        report = f"📋 **گزارش**\n👤 @{info['username']}\n🆔 {info['id']}\n🏆 وضعیت: {status}\n\n"
        for msg in context.user_data['history']:
            if msg['role'] == 'user':
                report += f"👤 کاربر: {msg['content']}\n"
            elif msg['role'] == 'assistant':
                report += f"🤖 ربات: {msg['content']}\n"
        photos = await context.bot.get_user_profile_photos(user.id)
        if photos.total_count > 0:
            await context.bot.send_photo(chat_id=ADMIN_TARGET, photo=photos.photos[0][-1].file_id, caption=report, parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=ADMIN_TARGET, text=report + "\n⚠️ بدون پروفایل", parse_mode='Markdown')
    except Exception:
        pass

async def cancel(update, context):
    await update.message.reply_text("❌ لغو شد.")
    context.user_data.clear()
    return ConversationHandler.END

# ========== وب سرور aiohttp (برای رندر) ==========
async def handle_health(request):
    return web.Response(text="ربات زنده است!")

# ========== اجرای اصلی (یک حلقه واحد) ==========
async def main():
    # ۱. راه‌اندازی وب‌سرور aiohttp برای باز نگه داشتن پورت ۱۰۰۰۰
    app = web.Application()
    app.router.add_get('/', handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    PORT = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"🌐 وب‌سرور روی پورت {PORT} باز شد (ربات زنده نگه داشته می‌شود).")

    # ۲. راه‌اندازی ربات تلگرام
    bot_app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        [CommandHandler('start', start_quiz)], 
        {ASKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]}, 
        [CommandHandler('cancel', cancel)]
    )
    bot_app.add_handler(conv)

    # مقداردهی اولیه و شروع پولینگ به صورت هم‌زمان
    await bot_app.initialize()
    await bot_app.updater.start_polling()
    print("🤖 ربات تلگرام روشن شد و منتظر پیام‌هاست!")

    # ۳. حلقه را تا ابد باز نگه دار (جایگزین run_polling مسدودکننده)
    await asyncio.Future()  # اینجا بی‌نهایت منتظر می‌ماند

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("ربات متوقف شد.")
