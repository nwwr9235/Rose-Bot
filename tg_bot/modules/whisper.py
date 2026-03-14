# tg_bot/modules/whisper.py
import time
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler, run_async
from tg_bot import dispatcher

LOGGER = logging.getLogger(__name__)

__mod_name__ = "الهمسات"

# تخزين الهمسات في الذاكرة (يمكن استبدالها بقاعدة بيانات لاحقاً)
whispers = {}
button_map = {}


@run_async
def whisper_cmd(bot, update):
    """معالج الأمر 'همسة'"""
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    LOGGER.info(f"تم استدعاء whisper_cmd في المجموعة {chat.id} بواسطة {user.id}")

    if not message.reply_to_message:
        message.reply_text("❌ يجب الرد على رسالة الشخص الذي تريد إرسال الهمسة له.")
        return

    target = message.reply_to_message.from_user

    if target.id == user.id:
        message.reply_text("❌ لا يمكنك إرسال همسة لنفسك.")
        return

    # استخراج نص الهمسة بعد الأمر
    text = message.text
    if text.startswith('همسة'):
        whisper_text = text[5:].strip()
    elif text.startswith('/whisper'):
        whisper_text = text[8:].strip()
    else:
        message.reply_text("❌ استخدم: همسة <رسالتك> مع الرد على شخص.")
        return

    if not whisper_text:
        message.reply_text("❌ يجب كتابة الهمسة بعد الأمر.\nمثال: همسة مرحبا")
        return

    # إنشاء معرف فريد
    whisper_id = f"{chat.id}_{user.id}_{int(time.time())}"

    whispers[whisper_id] = {
        'from_user': user.id,
        'to_user': target.id,
        'message': whisper_text,
        'chat_id': chat.id,
        'from_name': user.first_name,
        'to_name': target.first_name
    }

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔓 عرض الهمسة", callback_data=f"whisper_{whisper_id}")
    ]])

    button_map[f"whisper_{whisper_id}"] = whisper_id

    notification = (
        f"🔔 **همسة سرية** 🔔\n\n"
        f"المستخدم {user.first_name} أرسل لك همسة يا {target.first_name}!\n"
        f"اضغط على الزر أدناه لعرضها 👇"
    )
    message.reply_text(notification, reply_markup=keyboard)
    LOGGER.info(f"تم إنشاء همسة {whisper_id}")


@run_async
def whisper_button(bot, update):
    query = update.callback_query
    user = update.effective_user
    data = query.data

    if not data.startswith("whisper_"):
        return

    whisper_id = button_map.get(data)
    if not whisper_id:
        query.answer("❌ هذه الهمسة غير موجودة أو انتهت صلاحيتها.", show_alert=True)
        query.message.delete()
        return

    w = whispers.get(whisper_id)
    if not w:
        query.answer("❌ هذه الهمسة غير موجودة.", show_alert=True)
        query.message.delete()
        return

    if user.id != w['to_user']:
        query.answer("❌ هذه الهمسة ليست لك!", show_alert=True)
        return

    try:
        bot.send_message(
            chat_id=user.id,
            text=f"🔐 **همسة سرية** 🔐\n\nمن: {w['from_name']}\nالرسالة: {w['message']}",
            parse_mode='Markdown'
        )
        query.answer("✅ تم إرسال الهمسة لك في الخاص!", show_alert=False)
        query.message.delete()
        bot.send_message(
            chat_id=w['chat_id'],
            text=f"✅ المستخدم {w['to_name']} استلم الهمسة بنجاح."
        )
        # تنظيف الذاكرة
        del whispers[whisper_id]
        del button_map[data]
    except Exception as e:
        LOGGER.error(f"فشل إرسال الهمسة: {e}")
        query.answer("❌ فشل إرسال الهمسة. تأكد من أنك بدأت محادثة مع البوت.", show_alert=True)


@run_async
def start_private(bot, update):
    if update.effective_chat.type == "private":
        update.effective_message.reply_text(
            "👋 مرحباً! هذا البوت يدعم إرسال الهمسات.\n"
            "لاستخدام الميزة، أضفني إلى مجموعة واكتب:\n"
            "`همسة رسالتك` مع الرد على شخص."
        )


# إضافة المعالجات
dispatcher.add_handler(MessageHandler(Filters.regex(r'^همسة\s+.*') & Filters.group, whisper_cmd))
dispatcher.add_handler(CommandHandler("whisper", whisper_cmd, filters=Filters.group))
dispatcher.add_handler(CallbackQueryHandler(whisper_button, pattern=r"whisper_"))
dispatcher.add_handler(CommandHandler("start", start_private))
