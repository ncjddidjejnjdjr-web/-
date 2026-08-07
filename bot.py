import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from openai import OpenAI

# ============== تنظیمات محیطی ==============
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")
STATIC_INVITE_LINK = os.getenv("STATIC_INVITE_LINK")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not TOKEN or not DEEPSEEK_API_KEY:
    print("❌ خطا: متغیرهای محیطی BOT_TOKEN یا DEEPSEEK_API_KEY تنظیم نشده‌اند!")
    exit(1)

# تنظیم کلاینت DeepSeek (سازگار با OpenAI)
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"  # آدرس اصلی API دیپ‌سیک
)

# مراحل مکالمه
ASKING = 0
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data['user_info'] = {
        'id': user.id,
        'full_name': user.full_name,
        'username': user.username or "ندارد"
    }
    context.user_data['question_count'] = 0
    context.user_data['is_alive'] = True
    context.user_data['history'] = []

    # پرامپت سیستم مخصوص DeepSeek (به زبان فارسی)
    system_prompt = (
        "تو یک استاد بازی 'بن‌بست فکری' هستی. "
        "قراره یک مکالمه زنده و هوشمند با کاربر داشته باشی و حداکثر ۱۰ سوال چالش‌برانگیز، غیرقابل پیش‌بینی و خلاقانه بپرسی. "
        "سوالاتت باید کاربر رو به فکر فرو ببره، اما جواب‌ها منطقی باشن. "
        "بعد از هر پاسخ کاربر، تو باید تشخیص بدی که پاسخش درسته یا غلط. "
        "اگر پاسخ غلط بود، حتماً جمله‌ات رو با علامت '[END]' تمام کن. "
        "اگر پاسخ درست بود و سوال دهم رو هم پرسیدی و جواب داد، جمله‌ات رو با علامت '[WIN]' تمام کن. "
        "سبک حرف زدنت باید جذاب، هوشمندانه، کمی طنزآمیز و صمیمی باشه. "
        "اگر کاربر درخواست راهنمایی کرد، یک نکته کوچک بهش بده، اما جواب رو لو نده."
    )
    context.user_data['history'].append({"role": "system", "content": system_prompt})
    
    # دریافت اولین سوال از DeepSeek
    await update.message.reply_text("🧠 در حال آماده‌سازی سوالات بن‌بست فکری با هوش دیپ‌سیک... یک لحظه صبر کن.")
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",  # مدل مکالمه‌ای DeepSeek
            messages=context.user_data['history']
        )
        ai_reply = response.choices[0].message.content
        context.user_data['history'].append({"role": "assistant", "content": ai_reply})
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارتباط با هوش مصنوعی: {e}")
        return ConversationHandler.END
    
    # ارسال پیام شروع + جایزه
    await update.message.reply_text(
        f"🎯 **به بازی ۱۰ سوال بن‌بست فکری خوش آمدی!**\n\n"
        f"🏆 **جایزه:** اگر از هر ۱۰ سوال بدون افتادن در بن‌بست عبور کنی، لینک کانال خصوصی رو بهت می‌دم.\n\n"
        f"------------\n"
        f"{ai_reply}"
    )
    return ASKING

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_answer = update.message.text.strip()
    context.user_data['question_count'] += 1
    
    # ذخیره پاسخ کاربر
    context.user_data['history'].append({"role": "user", "content": user_answer})
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=context.user_data['history']
        )
        ai_reply = response.choices[0].message.content
        context.user_data['history'].append({"role": "assistant", "content": ai_reply})
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارتباط با هوش مصنوعی: {e}")
        return ASKING

    # بررسی وضعیت بازی بر اساس علامت‌های DeepSeek
    if "[END]" in ai_reply:
        # کاربر باخت
        await send_report_to_admin(update, context, status="باخت در سوال")
        await update.message.reply_text(
            f"❌ **باختی!** تو توی بن‌بست گیر کردی.\n"
            f"🧠 {ai_reply.replace('[END]', '')}\n\n"
            f"برای تلاش مجدد، /start رو بزن."
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    elif "[WIN]" in ai_reply or context.user_data['question_count'] >= 10:
        # کاربر برنده شد
        await send_report_to_admin(update, context, status="برنده شد (۱۰ سوال)")
        try:
            invite_link = await context.bot.create_chat_invite_link(CHANNEL_ID)
            await update.message.reply_text(
                f"🎉 **تبریک!** تو از هر ۱۰ بن‌بست فکری سالم بیرون اومدی!\n\n"
                f"🏆 **جایزه تو (لینک کانال):**\n{invite_link.invite_link}"
            )
        except:
            await update.message.reply_text(
                f"🎉 **تبریک!** لینک کانال:\n\n{STATIC_INVITE_LINK}"
            )
        context.user_data.clear()
        return ConversationHandler.END
    
    else:
        # سوال بعدی
        await update.message.reply_text(f"{ai_reply}\n\n(سوال {context.user_data['question_count']} از ۱۰)")
        return ASKING

async def send_report_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, status):
    user = update.effective_user
    info = context.user_data['user_info']
    
    photos = await context.bot.get_user_profile_photos(user.id)
    photo_file_id = photos.photos[0][-1].file_id if photos.total_count > 0 else None
    
    report = f"📋 **گزارش جدید (ربات زنده با DeepSeek)**\n"
    report += f"👤 @{info['username']}\n🆔 {info['id']}\n"
    report += f"🏆 وضعیت نهایی: {status}\n\n"
    report += "**📝 تاریخچه مکالمه کامل:**\n"
    for msg in context.user_data['history']:
        if msg['role'] == 'user':
            report += f"👤 کاربر: {msg['content']}\n"
        elif msg['role'] == 'assistant':
            report += f"🤖 ربات: {msg['content']}\n"
    
    if photo_file_id:
        await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=photo_file_id, caption=report, parse_mode='Markdown')
    else:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=report + "\n⚠️ بدون پروفایل", parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ بازی لغو شد.")
    context.user_data.clear()
    return ConversationHandler.END

# ========== بخش اجرا ==========
if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_quiz)],
        states={
            ASKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(conv_handler)

    PORT = int(os.environ.get('PORT', 10000))
    WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")

    if WEBHOOK_URL:
        print(f"ربات هوشمند زنده با DeepSeek روی {WEBHOOK_URL} روشن شد!")
        application.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=WEBHOOK_URL)
    else:
        print("⚠️ هشدار: رندر تنظیم نشده!")
        application.run_polling()
