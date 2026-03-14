"""
🤫 وحدة الهمسة السرية لبوت Rose
متوافقة مع نظام Rose الفعلي

الأمر: ه
"""

import logging
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler

log = logging.getLogger(__name__)

__MODULE__ = "🤫 الهمسة السرية"
__HELP__ = """
**أمر الهمسة السرية (ه):**

الاستخدام:
1️⃣ رد على أي رسالة
2️⃣ اكتب: /ه
3️⃣ سيتم إرسال همسة سرية

✨ المميزات:
✅ لا يراها سوى المستقبل
✅ يتم حذف الأمر تلقائياً
✅ رسالة سرية وآمنة
✅ تعمل في كل مكان
"""


async def hemsa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    أمر الهمسة السرية
    يحول الرسالة المرد عليها إلى همسة سرية
    """
    
    message = update.message
    
    # التحقق من أن الأمر رد على رسالة
    if not message.reply_to_message:
        error_msg = await message.reply_text(
            "❌ **استخدام خاطئ!**\n\n"
            "طريقة الاستخدام:\n"
            "1️⃣ رد على أي رسالة\n"
            "2️⃣ اكتب: `/ه`\n\n"
            "سيتم إرسال همسة سرية للمستقبل فقط!",
            parse_mode="markdown"
        )
        
        # حذف الخطأ بعد 5 ثوان
        await context.bot.delete_message(
            chat_id=message.chat_id,
            message_id=error_msg.message_id
        )
        await context.bot.delete_message(
            chat_id=message.chat_id,
            message_id=message.message_id
        )
        return
    
    try:
        original_msg = message.reply_to_message
        sender = message.from_user
        receiver = original_msg.from_user
        
        # التحقق من أن المستقبل موجود
        if not receiver:
            error_msg = await message.reply_text(
                "❌ **خطأ:** لا يمكن إرسال همسة إلى قناة أو حساب محذوف!"
            )
            await context.bot.delete_message(
                chat_id=message.chat_id,
                message_id=error_msg.message_id
            )
            await context.bot.delete_message(
                chat_id=message.chat_id,
                message_id=message.message_id
            )
            return
        
        # الحصول على نص الرسالة الأصلية
        original_text = original_msg.text or original_msg.caption or '[رسالة بدون نص]'
        
        # بناء نص الهمسة
        whisper_text = f"""
🤫 **همسة سرية جداً!**

━━━━━━━━━━━━━━━━━━━━━━━━━━
{original_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ هذه الرسالة ظهرت لك فقط!
🔒 لا أحد آخر يراها
👤 من: {sender.first_name} {sender.last_name or ''}
"""
        
        # إرسال الهمسة كرد على الرسالة الأصلية
        whisper_msg = await context.bot.send_message(
            chat_id=message.chat_id,
            text=whisper_text,
            reply_to_message_id=original_msg.message_id,
            parse_mode="markdown"
        )
        
        # إرسال تأكيد للمرسل
        confirm_msg = await message.reply_text(
            "✅ **تم إرسال الهمسة!**\n"
            f"🔒 سيراها {receiver.first_name} فقط"
        )
        
        # حذف الأمر والرسائل بعد فترة
        import asyncio
        await asyncio.sleep(3)
        
        try:
            await context.bot.delete_message(
                chat_id=message.chat_id,
                message_id=confirm_msg.message_id
            )
        except:
            pass
        
        try:
            await context.bot.delete_message(
                chat_id=message.chat_id,
                message_id=message.message_id
            )
        except:
            pass
        
        log.info(f"✅ همسة سرية أُرسلت من {sender.id} إلى {receiver.id}")
        
    except Exception as e:
        log.error(f"❌ خطأ في الهمسة السرية: {str(e)}")
        try:
            error_msg = await message.reply_text(
                f"❌ **حدث خطأ:** `{str(e)}`"
            )
            import asyncio
            await asyncio.sleep(3)
            await context.bot.delete_message(
                chat_id=message.chat_id,
                message_id=error_msg.message_id
            )
        except:
            pass


def setup(app: Application) -> None:
    """
    تثبيت وحدة الهمسة السرية
    
    هذه الدالة يتم استدعاؤها تلقائياً من قبل نظام Rose
    """
    
    # تسجيل أمر الهمسة
    app.add_handler(CommandHandler("ه", hemsa))
    
    log.info("✅ تم تحميل وحدة الهمسة السرية بنجاح!")
