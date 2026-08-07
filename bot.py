import os
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

if not TOKEN or not OPENAI_API_KEY:
    print("❌ خطا: متغیرهای محیطی تنظیم نشده‌اند!")
    exit(1)

# ========== تنظیمات OpenRouter (هوش مصنوعی زنده) ==========
client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://openrouter.ai/api/v1")
model = "meta-llama/llama-3.3-70b-instruct"  # مدل قدرتمند و رایگان

ASKING = 0
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data['user_info'] = {'id': user.id, 'full_name': user.full_name, 'username': user.username or "ندارد"}
    context.user_data['question_count'] = 0
    context.user_data['history'] = []

    # پرامپت سیستم برای تولید فقط ۱ سوال (خلاقانه و جدید)
    system_prompt = (
        "تو یک استاد بازی 'بن‌بست فکری' هستی. "
        "قراره فقط و فقط ۱ سوال چالش‌برانگیز، غیرقابل پیش‌بینی و کاملاً جدید بپرسی. "
        "اگر کاربر پاسخ صحیح داد، جمله‌ات را با علامت '[WIN]' تمام کن. "
        "اگر پاسخ غلط بود، جمله‌ات را با علامت '[END]' تمام کن. "
        "سوال باید طوری باشد که کاربر را به فکر فرو ببرد ولی جوابی منطقی داشته باشد."
    )
    context.user_data['history'].append({"role": "system", "content": system_prompt})
    
    await update.message.reply_text("🧠 در حال ساختن ۱ سوال بن‌بست فکری...")
    
    try:
        response = client.chat.completions.create(model=model, messages=context.user_data['history'])
        ai_reply = response.choices[0].message.content
        context.user_data['history'].append({"role": "assistant", "content": ai_reply})
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در برقراری ارتباط: {e}")
        return ConversationHandler.END

    await update.message.reply_text(
        f"🎯 **فقط ۱ سوال برای اثبات هوش تو!**\n\n"
        f"🏆 جایزه: اگر درست جواب بدی، لینک کانال خصوصی به تو داده می‌شود.\n\n"
        f"------------\n"
        f"{ai_reply}"
    )
    return ASKING

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_answer = update.message.text.strip()
    context.user_data['question_count'] += 1
    context.user_data['history'].append({"role": "user", "content": user_answer})
    
    # ارسال پاسخ به هوش مصنوعی برای بررسی
    try:
        response = client.chat.completions.create(model=model, messages=context.user_data['history'])
        ai_reply = response.choices[0].message.content
        context.user_data['history'].append({"role": "assistant", "content": ai_reply})
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در پردازش: {e}")
        return ASKING

    # === بررسی نتیجه ===
    if "[WIN]" in ai_reply:
        # کاربر برنده شد
        await send_report_to_admin(update, context, "برنده شد (فقط ۱ سوال)")
        try:
            link = await context.bot.create_chat_invite_link(CHANNEL_ID)
            await update.message.reply_text(
                f"🎉 **تبریک! تو این ۱ سوال رو درست جواب دادی!**\n\n"
                f"🏆 **جایزه تو (لینک کانال):**\n{link.invite_link}"
            )
        except:
            await update.message.reply_text(
                f"🎉 تبریک! لینک کانال:\n\n{STATIC_INVITE_LINK}"
            )
        context.user_data.clear()
        return ConversationHandler.END

    elif "[END]" in ai_reply:
        # کاربر باخت
        await send_report_to_admin(update, context, "باخت (پاسخ غلط به ۱ سوال)")
        await update.message.reply_text(
            f"❌ **باختی!** تو نتونستی از این ۱ بن‌بست عبور کنی.\n"
            f"🧠 {ai_reply.replace('[END]','')}\n\n"
            f"برای تلاش مجدد، /start رو بزن."
        )
        context.user_data.clear()
        return ConversationHandler.END

    else:
        # اگر هوش مصنوعی علامت‌ها رو اشتباه تشخیص داد، دوباره منتظر پاسخ می‌مونیم
        await update.message.reply_text(f"{ai_reply}\n\nلطفاً پاسخ خود را بفرستید.")
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
        await context.bot.send_photo(ADMIN_CHAT_ID, photos.photos[0][-1].file_id, caption=report)
    else:
        await context.bot.send_message(ADMIN_CHAT_ID, report + "\n⚠️ بدون پروفایل")

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
        print("ربات ۱ سوالی با Webhook روشن شد!")
        application.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=WEBHOOK_URL)
    else:
        print("⚠️ هشدار: رندر تنظیم نشده! ربات با polling اجرا می‌شود.")
        application.run_polling()
