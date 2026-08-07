import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler

# ============== خواندن تنظیمات از متغیرهای محیطی ==============
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))  # تبدیل به عدد
CHANNEL_ID = os.getenv("CHANNEL_ID")  # مثلاً @MyChannel
STATIC_INVITE_LINK = os.getenv("STATIC_INVITE_LINK")  # لینک کانال

if not TOKEN:
    print("❌ خطا: متغیر محیطی BOT_TOKEN تنظیم نشده است!")
    exit(1)
# ==============================================================

# سوالات و جواب‌ها
QUESTIONS = [
    {"q": "جمله را کامل کنید: من ادم ... هستم", "a": "کونی", "hint": "کلمه ۴ حرفی محاوره‌ای"},
    {"q": "حاصل ۲ + ۲ چند است؟", "a": "4", "hint": "عدد ساده"},
    {"q": "نام پایتون از چه موجودی است؟", "a": "مار", "hint": "یک خزنده"}
]

ASKING = 0
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data['user_info'] = {'id': user.id, 'full_name': user.full_name, 'username': user.username or "ندارد"}
    context.user_data['current_q_index'] = 0
    context.user_data['answers'] = []
    context.user_data['is_correct'] = True
    first_q = QUESTIONS[0]
    await update.message.reply_text(f"🎯 به سوالات پاسخ دهید.\n\n{first_q['q']}\n\n💡 برای راهنمایی 'راهنمایی' را بفرستید.")
    return ASKING

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_answer = update.message.text.strip()
    current_index = context.user_data['current_q_index']
    current_q = QUESTIONS[current_index]
    
    if user_answer.lower() == "راهنمایی":
        await update.message.reply_text(f"💡 راهنمایی: {current_q['hint']}\n\nحالا پاسخ را بفرستید.")
        return ASKING
    
    is_correct = user_answer.lower() == current_q['a'].lower()
    context.user_data['answers'].append({'question': current_q['q'], 'user_answer': user_answer, 'correct': is_correct})
    if not is_correct:
        context.user_data['is_correct'] = False
    
    next_index = current_index + 1
    if next_index < len(QUESTIONS):
        context.user_data['current_q_index'] = next_index
        await update.message.reply_text(f"سوال بعدی:\n\n{QUESTIONS[next_index]['q']}\n\n💡 'راهنمایی' را بفرستید.")
        return ASKING
    else:
        await send_report_to_admin(update, context)
        if context.user_data['is_correct']:
            try:
                invite_link = await context.bot.create_chat_invite_link(CHANNEL_ID)
                await update.message.reply_text(f"✅ تبریک! لینک ورود:\n\n{invite_link.invite_link}")
            except:
                await update.message.reply_text(f"✅ تبریک! لینک ورود:\n\n{STATIC_INVITE_LINK}")
        else:
            await update.message.reply_text("❌ پاسخ‌ها درست نبود. برای تلاش مجدد /start را بزنید.")
        context.user_data.clear()
        return ConversationHandler.END

async def send_report_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    info = context.user_data['user_info']
    answers = context.user_data['answers']
    overall = "✅ درست" if context.user_data['is_correct'] else "❌ غلط"
    
    photos = await context.bot.get_user_profile_photos(user.id)
    photo_file_id = photos.photos[0][-1].file_id if photos.total_count > 0 else None
    
    report = f"📋 گزارش جدید\n👤 @{info['username']}\n🆔 {info['id']}\n📛 {info['full_name']}\n🏆 نتیجه: {overall}\n\n"
    for i, ans in enumerate(answers, 1):
        report += f"{i}. {ans['question']}\n   پاسخ: {ans['user_answer']} {'✅' if ans['correct'] else '❌'}\n"
    
    if photo_file_id:
        await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=photo_file_id, caption=report, parse_mode='Markdown')
    else:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=report + "\n⚠️ بدون پروفایل", parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ لغو شد.")
    context.user_data.clear()
    return ConversationHandler.END

if name == 'main':
    application = ApplicationBuilder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_quiz)],
        states={ASKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]},
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(conv_handler)

    # ========== تنظیم Webhook برای Render ==========
    PORT = int(os.environ.get('PORT', 10000))  # Render پورت 10000 را به شما می‌دهد
    # آدرس رندر شما به صورت https://نام-اپ-شما.onrender.com خواهد بود
    # این آدرس را در رندر پیدا می‌کنید. بهتر است بعد از دپلوی در رندر تنظیم شود.
    # اما برای اطمینان، ما آدرس را در متغیر محیطی RENDER_EXTERNAL_URL می‌گیریم
    WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")  # این را رندر خودکار می‌دهد

    if WEBHOOK_URL:
        print(f"ربات با Webhook روی {WEBHOOK_URL} روشن شد!")
        application.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=WEBHOOK_URL)
    else:
        print("⚠️ هشدار: RENDER_EXTERNAL_URL تنظیم نشده! لطفاً بعد از دپلوی، یک بار این آدرس را در رندر کپی کنید.")
        # در غیر اینصورت با پولینگ (فقط برای تست موقت) اجرا می‌شود
        application.run_polling()
