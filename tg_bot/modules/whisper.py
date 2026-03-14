# tg_bot/modules/whisper.py
import time
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler, run_async
from tg_bot import dispatcher

LOGGER = logging.getLogger(__name__)

__mod_name__ = "الهمسات"

# تخزين مؤقت للبيانات
waiting_whispers = {}
completed_whispers = {}
button_map = {}


@run_async
def whisper_cmd(bot, update):
    """معالج الأمر 'ه' - يبدأ عملية الهمسة (يدعم /ه و ه)"""
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    LOGGER.info(f"أمر همسة من {user.id} في المجموعة {chat.id}")

    # يجب الرد على شخص
    if not message.reply_to_message:
        message.reply_text("❌ يجب الرد على رسالة الشخص الذي تريد إرسال الهمسة له.")
        return

    target = message.reply_to_message.from_user

    if target.id == user.id:
        message.reply_text("❌ لا يمكنك إرسال همسة لنفسك.")
        return

    # إنشاء معرف مؤقت
    process_id = f"{chat.id}_{user.id}_{int(time.time())}"

    waiting_whispers[process_id] = {
        "from_user": user.id,
        "to_user": target.id,
        "from_name": user.first_name,
        "to_name": target.first_name,
        "chat_id": chat.id,
        "step": "waiting_for_message"
    }

    # رابط بدء المحادثة الخاصة
    bot_username = bot.username
    deep_link = f"https://t.me/{bot_username}?start=whisper_{process_id}"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✍️ اكتب الهمسة هنا", url=deep_link)
    ]])

    message.reply_text(
        f"🔐 **همسة إلى {target.first_name}**\n\n"
        f"اضغط على الزر أدناه للدخول إلى المحادثة الخاصة وكتابة الهمسة.",
        reply_markup=keyboard
    )


@run_async
def whisper_private_start(bot, update):
    """معالج بدء المحادثة الخاصة مع البوت"""
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if chat.type != "private":
        return

    text = message.text
    LOGGER.info(f"بدء خاص من {user.id} بالنص: {text}")

    # إذا كان هناك deep link
    if text.startswith("/start whisper_"):
        process_id = text.split("_", 1)[1]
        data = waiting_whispers.get(process_id)

        if not data or data["from_user"] != user.id:
            message.reply_text("❌ هذه الهمسة غير موجودة أو انتهت صلاحيتها.")
            return

        message.reply_text(
            f"👤 أنت ترسل همسة إلى {data['to_name']}.\n"
            f"اكتب الآن الرسالة التي تريد إرسالها:"
        )
        waiting_whispers[process_id]["step"] = "awaiting_message"

    else:
        # رسالة عادية في الخاص
        found = False
        to_delete = []
        for pid, data in waiting_whispers.items():
            if data["from_user"] == user.id and data.get("step") == "awaiting_message":
                # هذه هي الهمسة المنتظرة
                whisper_text = message.text.strip()
                if not whisper_text:
                    message.reply_text("❌ الهمسة لا يمكن أن تكون فارغة.")
                    return

                # إنشاء معرف نهائي
                final_id = f"final_{int(time.time())}_{user.id}"
                completed_whispers[final_id] = {
                    "from_user": user.id,
                    "to_user": data["to_user"],
                    "from_name": data["from_name"],
                    "to_name": data["to_name"],
                    "message": whisper_text,
                    "chat_id": data["chat_id"]
                }

                # زر العرض في المجموعة
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔓 عرض الهمسة", callback_data=f"show_{final_id}")
                ]])
                button_map[f"show_{final_id}"] = final_id

                try:
                    bot.send_message(
                        chat_id=data["chat_id"],
                        text=f"🔔 **همسة إلى {data['to_name']}**\n"
                             f"المرسل {data['from_name']} كتب الهمسة. اضغط الزر لعرضها.",
                        reply_markup=keyboard
                    )
                    message.reply_text("✅ تم حفظ الهمسة وإرسال الإشعار في المجموعة.")
                except Exception as e:
                    LOGGER.error(f"فشل إرسال الإشعار للمجموعة: {e}")
                    message.reply_text("❌ فشل إرسال الإشعار للمجموعة. قد لا يكون البوت مشرفاً.")
                    return

                to_delete.append(pid)
                found = True
                break

        # حذف العمليات المؤقتة المنتهية
        for pid in to_delete:
            if pid in waiting_whispers:
                del waiting_whispers[pid]

        if not found:
            message.reply_text("👋 مرحباً! لاستخدام الهمسات، أضفني إلى مجموعة واكتب `ه` مع الرد على شخص.")


@run_async
def whisper_show_button(bot, update):
    """معالج الضغط على زر عرض الهمسة"""
    query = update.callback_query
    user = update.effective_user
    data = query.data

    if not data.startswith("show_"):
        return

    final_id = data[5:]
    whisper = completed_whispers.get(final_id)

    if not whisper:
        query.answer("❌ هذه الهمسة غير موجودة.", show_alert=True)
        query.message.delete()
        return

    if user.id != whisper["to_user"]:
        query.answer("❌ هذه الهمسة ليست لك!", show_alert=True)
        return

    try:
        bot.send_message(
            chat_id=user.id,
            text=f"🔐 **همسة سرية** 🔐\n\n"
                 f"من: {whisper['from_name']}\n"
                 f"الرسالة: {whisper['message']}",
            parse_mode="Markdown"
        )
        query.answer("✅ تم إرسال الهمسة لك في الخاص!", show_alert=False)
        query.message.delete()
        bot.send_message(
            chat_id=whisper["chat_id"],
            text=f"✅ المستخدم {whisper['to_name']} استلم الهمسة."
        )
        # تنظيف الذاكرة
        del completed_whispers[final_id]
        if data in button_map:
            del button_map[data]
    except Exception as e:
        LOGGER.error(f"فشل إرسال الهمسة: {e}")
        query.answer("❌ فشل إرسال الهمسة. تأكد من أنك بدأت محادثة مع البوت.", show_alert=True)


@run_async
def start_private(bot, update):
    """رسالة بداية بسيطة في الخاص"""
    if update.effective_chat.type == "private":
        update.effective_message.reply_text(
            "👋 مرحباً! هذا البوت يدعم الهمسات.\n"
            "لإرسال همسة، أضفني إلى مجموعة، ثم اكتب `/ه` أو `ه` مع الرد على الشخص."
        )


# إضافة المعالجات
dispatcher.add_handler(CommandHandler("ه", whisper_cmd, filters=Filters.group))  # الأمر /ه
dispatcher.add_handler(MessageHandler(Filters.regex(r'^ه$') & Filters.group, whisper_cmd))  # الأمر ه بدون /
dispatcher.add_handler(CommandHandler("start", start_private))
dispatcher.add_handler(MessageHandler(Filters.text & Filters.private, whisper_private_start))
dispatcher.add_handler(CallbackQueryHandler(whisper_show_button, pattern=r"^show_"))
