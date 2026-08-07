import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from openai import OpenAI

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")
STATIC_INVITE_LINK = os.getenv("STATIC_INVITE_LINK")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TOKEN or not OPENAI_API_KEY:
    print("❌ خطا: متغیرهای محیطی تنظیم نشده‌اند!")
    exit(1)

# ========== تنظیمات هوش مصنوعی ==========
# اگر کلید DeepSeek دارید، خط زیر و model را فعال کنید:
# client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://api.deepseek.com")
# model = "deepseek-chat"

# اگر کلید OpenRouter دارید (پیشنهاد من)، این دو خط را فعال کنید:
client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://openrouter.ai/api/v1")
model = "google/gemini-2.0-flash-lite-preview-02-05"  # یا "meta-llama/llama-3.3-70b-instruct"

ASKING = 0
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data['user_info'] = {'id': user.id, 'full_name': user.full_name, 'username': user.username or "ندارد"}
    context.user_data['question_count'] = 0
    context.user_data['history'] = []

    system_prompt = "تو یک استاد بازی 'بن‌بست فکری' هستی. حداکثر ۱۰ سوال چالش‌برانگیز بپرس. اگر پاسخ غلط بود، جمله را با '[END]' تمام کن. اگر سوال دهم درست بود، با '[WIN]' تمام کن."
    context.user_data['history'].append({"role": "system", "content": system_prompt})
    
    await update.message.reply_text("🧠 در حال آماده‌سازی سوالات...")
    
    try:
        response = client.chat.completions.create(model=model, messages=context.user_data['history'])
        ai_reply = response.choices[0].message.content
        context.user_data['history'].append({"role": "assistant", "content": ai_reply})
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")
        return ConversationHandler.END

    await update.message.reply_text(f"🎯 به بازی خوش آمدی!\n🏆 جایزه: لینک کانال\n\n{ai_reply}")
    return ASKING

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_answer = update.message.text.strip()
    context.user_data['question_count'] += 1
    context.user_data['history'].append({"role": "user", "content": user_answer})
    
    try:
        response = client.chat.completions.create(model=model, messages=context.user_data['history'])
        ai_reply = response.choices[0].message.content
        context.user_data['history'].append({"role": "assistant", "content": ai_reply})
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")
        return ASKING

    if "[END]" in ai_reply:
        await send_report_to_admin(update, context, "باخت")
        await update.message.reply_text(f"❌ باختی!\n{ai_reply.replace('[END]','')}\nبرای تلاش مجدد /start بزن.")
        context.user_data.clear()
        return ConversationHandler.END
    elif "[WIN]" in ai_reply or context.user_data['question_count'] >= 10:
        await send_report_to_admin(update, context, "برنده شد")
        try:
            link = await context.bot.create_chat_invite_link(CHANNEL_ID)
            await update.message.reply_text(f"🎉 تبریک! جایزه:\n{link.invite_link}")
        except:
            await update.message.reply_text(f"🎉 تبریک! لینک:\n{STATIC_INVITE_LINK}")
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await update.message.reply_text(f"{ai_reply}\n(سوال {context.user_data['question_count']})")
        return ASKING

async def send_report_to_admin(update, context, status):
    user = update.effective_user
    info = context.user_data['user_info']
    report = f"📋 گزارش\n👤 @{info['username']}\n🆔 {info['id']}\n🏆 {status}\n\n"
    for msg in context.user_data['history']:
        if msg['role'] == 'user':
            report += f"👤 کاربر: {msg['content']}\n"
        elif msg['role'] == 'assistant':
            report += f"🤖 ربات: {msg['content']}\n"
    photos = await context.bot.get_user_profile_photos(user.id)
    if photos.total_count > 0:
        await context.bot.send_photo(ADMIN_CHAT_ID, photos.photos[0][-1].file_id, caption=report)
    else:
        await context.bot.send_message(ADMIN_CHAT_ID, report)

async def cancel(update, context):
    await update.message.reply_text("❌ لغو شد.")
    context.user_data.clear()
    return ConversationHandler.END

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler([CommandHandler('start', start_quiz)], {ASKING: [MessageHandler(filters.TEXT, handle_answer)]}, [CommandHandler('cancel', cancel)])
    application.add_handler(conv)
    PORT = int(os.environ.get('PORT', 10000))
    WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")
    if WEBHOOK_URL:
        print("ربات روشن شد!")
        application.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=WEBHOOK_URL)
    else:
        application.run_polling()
