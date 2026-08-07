import os
import re
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from openai import OpenAI

# ========== تنظیمات محیطی ==========
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")
STATIC_INVITE_LINK = os.getenv("STATIC_INVITE_LINK")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not STATIC_INVITE_LINK:
    STATIC_INVITE_LINK = "لینک کانال در تنظیمات تعریف نشده است. با ادمین تماس بگیرید."

if not TOKEN or not OPENAI_API_KEY:
    print("❌ خطا: متغیرهای محیطی تنظیم نشده‌اند!")
    exit(1)

# ========== تنظیمات OpenRouter ==========
client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://openrouter.ai/api/v1")
model = "meta-llama/llama-3.3-70b-instruct"

ASKING = 0
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# تابع قدرتمند پاکسازی متن از برچسب‌ها
def clean_response_for_user(text):
    # 1. حذف کامل خطوط کد و شرط‌های برنامه‌نویسی
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # اگر خط شامل کلمات برنامه‌نویسی مثل if, else, chose, print بود، حذفش کن
        if re.search(r'\b(if|else|print|chose|WIN|END)\b', line, re.IGNORECASE):
            continue
        cleaned_lines.append(line)
    text = '\n'.join(cleaned_lines)

    # 2. حذف کاراکترهای ویژه مثل * _ # ` و براکت‌های []
    text = re.sub(r'[\*\_\#\`\[\]]', '', text)
    
    # 3. پاک کردن فاصله‌های اضافی
    text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    return text

async def send_joined_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """گزارش فوری شروع مکالمه توسط کاربر (فقط برای ادمین)"""
    user = update.effective_user
    info_text = (
        f"🚀 **کاربر جدید وارد شد!**\n"
        f"👤 @{user.username or 'ندارد'}\n"
        f"🆔 {user.id}\n"
        f"📛 {user.full_name}"
    )
    photos = await context.bot.get_user_profile_photos(user.id)
    if photos.total_count > 0:
        await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=photos.photos[0][-1].file_id, caption=info_text, parse_mode='Markdown')
    else:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=info_text + "\n⚠️ بدون پروفایل", parse_mode='Markdown')

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ۱. ارسال فوری گزارش به ادمین
    await send_joined_report(update, context)

    user = update.effective_user
    context.user_data['user_info'] = {'id': user.id, 'full_name': user.full_name, 'username': user.username or "ندارد"}
    context.user_data['history'] = []

    # پرامپت بسیار سختگیرانه (برای جلوگیری از لو رفتن جواب و کد)
    system_prompt = (
        "تو یک استاد بازی 'بن‌بست فکری' هستی. "
        "فقط ۱ سوال فکری، مفهومی، فلسفی یا منطقی بپرس. "
        "سوال باید ۴ گزینه‌ای باشد (A, B, C, D) و ۳ گزینه انحرافی داشته باشد. "
        "🔴 مهم: هرگز جواب صحیح را به کاربر نگو. "
        "🔴 هرگز از کدهای برنامه‌نویسی، شرط‌های if/else، براکت `[]` یا کاراکترهای `*`, `_`, `#`, `` ` `` استفاده نکن. "
        "🔴 در انتهای پاسخ، دقیقاً در ابتدای یک خط جدید (و فقط یک خط) بنویس: `WIN:` یا `END:` و بلافاصله یک نظر کوتاه در مورد پاسخ کاربر بده. "
        "مثال فرمت صحیح:\n"
        "سوال ...\nA) ...\nB) ...\nC) ...\nD) ...\n\n"
        "WIN: آفرین! تو حسابی فکر کردی."
    )
    context.user_data['history'].append({"role": "system", "content": system_prompt})
    
    # ۲. انیمیشن تایپ کردن + پیام آماده‌سازی
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text("🧠 در حال ساختن سوال بن‌بست فکری... یک لحظه صبر کن.")
    
    try:
        response = client.chat.completions.create(model=model, messages=context.user_data['history'])
        ai_raw = response.choices[0].message.content
        context.user_data['history'].append({"role": "assistant", "content": ai_raw})
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در برقراری ارتباط با هوش مصنوعی: {e}")
        return ConversationHandler.END

    # ۳. پاکسازی و نمایش سوال (جواب صحیح و [WIN/END] حذف می‌شوند)
    clean_question = clean_response_for_user(ai_raw)
    
    await update.message.reply_text(
        f"🎯 **فقط ۱ سوال فکری**\n\n"
        f"🏆 جایزه: اگر گزینه صحیح (A, B, C یا D) رو بزنی، لینک کانال خصوصی دریافت می‌کنی.\n\n"
        f"------------\n"
        f"{clean_question}"
    )
    return ASKING

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_answer = update.message.text.strip().upper()
    context.user_data['history'].append({"role": "user", "content": user_answer})
    
    # انیمیشن تایپ کردن
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        response = client.chat.completions.create(model=model, messages=context.user_data['history'])
        ai_raw = response.choices[0].message.content
        context.user_data['history'].append({"role": "assistant", "content": ai_raw})
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در پردازش: {e}")
        return ASKING

    # ===== تشخیص هوشمند (با استفاده از startswith به جای contains) =====
    is_win = ai_raw.startswith("WIN:")
    is_end = ai_raw.startswith("END:")
    
    # تمیز کردن متن برای نمایش به کاربر (تمام برچسب‌ها حذف می‌شوند)
    clean_user_msg = clean_response_for_user(ai_raw)

    if is_win:
        await send_report_to_admin(update, context, "برنده شد (۱ سوال)")
        try:
            link = await context.bot.create_chat_invite_link(CHANNEL_ID)
            await update.message.reply_text(
                f"🎉 **تبریک! گزینه صحیح رو زدی!**\n\n"
                f"🏆 **جایزه (لینک کانال):**\n{link.invite_link}"
            )
        except:
            await update.message.reply_text(f"🎉 تبریک! لینک کانال:\n\n{STATIC_INVITE_LINK}")
        context.user_data.clear()
        return ConversationHandler.END

    elif is_end:
        await send_report_to_admin(update, context, "باخت (گزینه اشتباه)")
        await update.message.reply_text(
            f"❌ **باختی!** گزینه درست رو انتخاب نکردی.\n"
            f"🧠 {clean_user_msg}\n\n"
            f"برای تلاش مجدد، /start رو بزن."
        )
        context.user_data.clear()
        return ConversationHandler.END

    else:
        # اگر هوش مصنوعی تشخیص نداد، بدون نمایش کد اضافی، دوباره سوال می‌کنیم
        await update.message.reply_text(f"{clean_user_msg}\n\nلطفاً فقط یکی از گزینه‌های A, B, C یا D رو بفرست.")
        return ASKING

async def send_report_to_admin(update, context, status):
    user = update.effective_user
    info = context.user_data['user_info']
    
    # گزارش مخفیانه (فقط به ادمین)
    report = f"📋 **گزارش (۱ سوال)**\n👤 @{info['username']}\n🆔 {info['id']}\n🏆 وضعیت: {status}\n\n"
    for msg in context.user_data['history']:
        if msg['role'] == 'user':
            report += f"👤 کاربر: {msg['content']}\n"
        elif msg['role'] == 'assistant':
            # در گزارش برای خودمان تگ‌ها را نگه می‌داریم
            report += f"🤖 ربات: {msg['content']}\n"
    
    photos = await context.bot.get_user_profile_photos(user.id)
    if photos.total_count > 0:
        await context.bot.send_photo(ADMIN_CHAT_ID, photos.photos[0][-1].file_id, caption=report, parse_mode='Markdown')
    else:
        await context.bot.send_message(ADMIN_CHAT_ID, report + "\n⚠️ بدون پروفایل", parse_mode='Markdown')

async def cancel(update, context):
    await update.message.reply_text("❌ بازی لغو شد.")
    context.user_data.clear()
    return ConversationHandler.END

# ========== بخش اجرا ==========
if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        [CommandHandler('start', start_quiz)], 
        {ASKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]}, 
        [CommandHandler('cancel', cancel)]
    )
    application.add_handler(conv)
    
    PORT = int(os.environ.get('PORT', 10000))
    WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")
    if WEBHOOK_URL:
        print("ربات ۱ سوالی (بدون کد و باگ) با Webhook روشن شد!")
        application.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=WEBHOOK_URL)
    else:
        print("⚠️ هشدار: رندر تنظیم نشده!")
        application.run_polling()
