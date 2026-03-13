# tg_bot/modules/whisper.py
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler, run_async
from tg_bot import dispatcher, LOGGER

__mod_name__ = "الهمسات"

# قاموس مؤقت لتخزين الهمسات (بدون قاعدة بيانات)
# المفتاح: معرف الهمسة الفريد (chat_id + user_id + timestamp)
# القيمة: {"from_user": sender_id, "to_user": target_id, "message": text, "chat_id": group_chat_id}
whispers = {}

# قاموس لربط الأزرار بالهمسات
button_map = {}


@run_async
def whisper_cmd(bot, update):
    """
    معالج الأمر "همسة"
    الاستخدام: بالرد على رسالة شخص، اكتب "همسة رسالتك السرية"
    """
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    # التأكد من أن الأمر تم استخدامه بالرد على رسالة
    if not message.reply_to_message:
        message.reply_text("❌ يجب الرد على رسالة الشخص الذي تريد إرسال الهمسة له.")
        return

    target_user = message.reply_to_message.from_user

    # التأكد من أن المستخدم لا يرسل همسة لنفسه
    if target_user.id == user.id:
        message.reply_text("❌ لا يمكنك إرسال همسة لنفسك.")
        return

    # استخراج نص الهمسة
    text = message.text.strip()
    # إزالة كلمة "همسة" من البداية
    if text.startswith("همسة"):
        whisper_text = text[5:].strip()  # 5 هو طول كلمة "همسة" مع المسافة
    else:
        whisper_text = text

    if not whisper_text:
        message.reply_text("❌ يجب كتابة الهمسة بعد الأمر.\nمثال: همسة مرحبا")
        return

    # إنشاء معرف فريد للهمسة
    whisper_id = f"{chat.id}_{user.id}_{int(time.time())}"

    # تخزين الهمسة في الذاكرة
    whispers[whisper_id] = {
        "from_user": user.id,
        "to_user": target_user.id,
        "message": whisper_text,
        "chat_id": chat.id,
        "from_name": user.first_name,
        "to_name": target_user.first_name
    }

    # إنشاء زر للموافقة على استلام الهمسة
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔓 عرض الهمسة", callback_data=f"whisper_{whisper_id}")
    ]])

    # ربط الزر بالهمسة
    button_map[f"whisper_{whisper_id}"] = whisper_id

    # إرسال إشعار في المجموعة
    notification = (
        f"🔔 **همسة سرية** 🔔\n\n"
        f"المستخدم {user.first_name} أرسل لك همسة يا {target_user.first_name}!\n"
        f"اضغط على الزر أدناه لعرضها 👇"
    )
    message.reply_text(notification, reply_markup=keyboard)


@run_async
def whisper_button(bot, update):
    """
    معالج الضغط على زر عرض الهمسة
    """
    query = update.callback_query
    user = update.effective_user
    callback_data = query.data

    # استخراج معرف الهمسة من callback_data
    if not callback_data.startswith("whisper_"):
        return

    whisper_id = button_map.get(callback_data)
    if not whisper_id:
        query.answer("❌ هذه الهمسة غير موجودة أو انتهت صلاحيتها.", show_alert=True)
        query.message.delete()
        return

    whisper_data = whispers.get(whisper_id)
    if not whisper_data:
        query.answer("❌ هذه الهمسة غير موجودة أو انتهت صلاحيتها.", show_alert=True)
        query.message.delete()
        return

    # التحقق من أن المستخدم الذي ضغط على الزر هو المستهدف فقط
    if user.id != whisper_data["to_user"]:
        query.answer("❌ هذه الهمسة ليست لك!", show_alert=True)
        return

    # إرسال الهمسة بشكل خاص للمستخدم
    try:
        whisper_text = (
            f"🔐 **همسة سرية** 🔐\n\n"
            f"من: {whisper_data['from_name']}\n"
            f"الرسالة: {whisper_data['message']}"
        )
        bot.send_message(
            chat_id=user.id,
            text=whisper_text,
            parse_mode="Markdown"
        )

        # إشعار النجاح
        query.answer("✅ تم إرسال الهمسة لك في الخاص!", show_alert=False)

        # حذف رسالة الإشعار من المجموعة
        query.message.delete()

        # إرسال تأكيد في المجموعة أن الهمسة وصلت
        bot.send_message(
            chat_id=whisper_data["chat_id"],
            text=f"✅ المستخدم {whisper_data['to_name']} استلم الهمسة بنجاح."
        )

        # حذف الهمسة من الذاكرة بعد استخدامها
        del whispers[whisper_id]
        del button_map[callback_data]

    except Exception as e:
        LOGGER.error(f"خطأ في إرسال الهمسة: {e}")
        query.answer("❌ فشل إرسال الهمسة. تأكد أن البوت يمكنه مراسلتك في الخاص.", show_alert=True)


@run_async
def start_private(bot, update):
    """
    رسالة ترحيب عند بدء المحادثة الخاصة
    """
    if update.effective_chat.type == "private":
        update.effective_message.reply_text(
            "👋 مرحباً! هذا البوت يدعم إرسال الهمسات.\n"
            "لاستخدام الميزة، أضفني إلى مجموعة واكتب:\n"
            "`همسة رسالتك` مع الرد على شخص."
        )


# إضافة المعالجات
dispatcher.add_handler(MessageHandler(Filters.regex(r'^همسة\s+') & Filters.group, whisper_cmd))
dispatcher.add_handler(CallbackQueryHandler(whisper_button, pattern=r"whisper_"))
dispatcher.add_handler(CommandHandler("start", start_private))
