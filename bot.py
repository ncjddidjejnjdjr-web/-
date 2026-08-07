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

if not STATIC_INVITE_LINK:
    STATIC_INVITE_LINK = "لینک کانال در تنظیمات تعریف نشده است. با ادمین تماس بگیرید."

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TOKEN or not OPENAI_API_KEY:
    print("❌ خطا: متغیرهای محیطی تنظیم نشده‌اند!")
    exit(1)

# ========== تنظیمات OpenRouter ==========
client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://openrouter.ai/api/v1")
model = "meta-llama/llama-3.3-70b-instruct"

# تابع پاک‌کننده علامت‌های Markdown (جهت رفع علامت‌های عجیب `**`)
def clean_markdown(text):
    # حذف ستاره‌ها، خط زیر، هشتگ و بک‌تیک
    return re.sub(r'[\*\_\#\`]', '', text)

ASKING = 0
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data['user_info'] = {'id': user.id, 'full_name': user.full_name, 'username': user.username or "ندارد"}
    context.user_data['history'] = []

    # پرامپت جدید: فکری و مفهومی + ۴ گزینه‌ای + بدون فرمت Markdown
    system_prompt = (
        "تو یک استاد بازی 'بن‌بست فکری' هستی. "
        "فقط ۱ سوال فکری، مفهومی، فلسفی یا منطقی بپرس. "
        "از سوالات علمی، ریاضی و محاسباتی جداً خودداری کن. "
        "سوال باید ۴ گزینه‌ای باشد (A, B, C, D) و ۳ گزینه انحرافی (منحرف‌کننده) داشته باشد. "
        "پاسخ صحیح را با حرف (مثلاً A) مشخص کن. "
        "در انتهای پیام، اگر کاربر گزینه صحیح را انتخاب کرد، علامت '[WIN]' و اگر غلط انتخاب کرد، علامت '[END]' را بگذار. "
        "مهم: از هرگونه کاراکتر ویژه برای قالب‌بندی (مانند * # _ `) استفاده نکن. متن را ساده بنویس."
    )
    context.user_data['history'].append({"role": "system", "content": system_prompt})
    
    await update.message.reply_text("🧠 در حال ساختن ۱ سوال فکری و مفهومی...")
    
    try:
        response = client.chat.completions.create(model=model, messages=context.user_data['history'])
        ai_reply = clean_markdown(response.choices[0].message.content)
        context.user_data['history'].append({"role": "assistant", "content": ai_reply})
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در برقراری ارتباط: {e}")
        return ConversationHandler.END

    await update.message.reply_text(
        f"🎯 **فقط ۱ سوال فکری برای اثبات هوش تو!**\n\n"
        f"🏆 جایزه: اگر گزینه صحیح (A, B, C یا D) رو بزنی، لینک کانال خصوصی به تو داده می‌شود.\n\n"
        f"------------\n"
        f"{ai_reply}"
    )
    return ASKING

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_answer = update.message.text.strip().upper()
    context.user_data['history'].append({"role": "user", "content": user_answer})
    
    try:
        response = client.chat.completions.create(model=model, messages=context.user_data['history'])
        ai_reply = clean_markdown(response.choices[0].message.content)
        context.user_data['history'].append({"role": "assistant", "content": ai_reply})
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در پردازش: {e}")
        return ASKING

    # بررسی نتیجه
    if "[WIN]" in ai_reply:
        await send_report_to_admin(update, context, "برنده شد (فقط ۱ سوال)")
        try:
            link = await context.bot.create_chat_invite_link(CHANNEL_ID)
            await update.message.reply_text(
                f"🎉 **تبریک! تو گزینه صحیح رو زدی!**\n\n"
                f"🏆 **جایزه تو (لینک کانال):**\n{link.invite_link}"
            )
        except:
            # اگر لینک ساخته نشد، از STATIC_INVITE_LINK استفاده کن
            await update.message.reply_text(
                f"🎉 تبریک! لینک کانال:\n\n{STATIC_INVITE_LINK}"
            )
        context.user_data.clear()
        return ConversationHandler.END

    elif "[END]" in ai_reply:
        await send_report_to_admin(update, context, "باخت (گزینه اشتباه)")
        await update.message.reply_text(
            f"❌ **باختی!** گزینه درست رو انتخاب نکردی.\n"
            f"🧠 {ai_reply.replace('[END]','')}\n\n"
            f"برای تلاش مجدد، /start رو بزن."
        )
        context.user_data.clear()
        return ConversationHandler.END

    else:
        # اگر هوش مصنوعی تشخیص نداد دوباره می‌پرسیم
        await update.message.reply_text(f"{ai_reply}\n\nلطفاً فقط یکی از گزینه‌های A, B, C یا D رو بفرست.")
        return ASKING

async def send_report_to_admin(update, context, status):
    user = update.effective_user
    info = context.user_data['user_info']
    report = f"📋 **گزارش (۱ سوال)**\n👤 @{info['username']}\n🆔 {info['id']}\n🏆 وضعیت: {status}\n\n"
    for msg in context.user_data['history']:
        if msg['role'] == 'user':
            report += f"👤 کاربر: {msg['content']}\n"
        elif msg['role'] == 'assistant':
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
        print("ربات ۱ سوالی فکری با Webhook روشن شد!")
        application.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=WEBHOOK_URL)
    else:
        print("⚠️ هشدار: رندر تنظیم نشده! ربات با polling اجرا می‌شود.")
        application.run_polling()
