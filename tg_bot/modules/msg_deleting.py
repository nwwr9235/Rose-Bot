import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, MessageHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.helper_funcs.chat_status import user_admin, can_delete
from tg_bot.modules.log_channel import loggable


@run_async
@user_admin
@loggable
def purge(bot: Bot, update: Update, args: List[str]) -> str:
    msg = update.effective_message
    if msg.reply_to_message:
        user = update.effective_user
        chat = update.effective_chat
        if can_delete(chat, bot.id):
            message_id = msg.reply_to_message.message_id
            delete_to = msg.message_id - 1
            if args and args[0].isdigit():
                new_del = message_id + int(args[0])
                if new_del < delete_to:
                    delete_to = new_del
            else:
                delete_to = msg.message_id - 1
            for m_id in range(delete_to, message_id - 1, -1):
                try:
                    bot.deleteMessage(chat.id, m_id)
                except BadRequest as err:
                    if err.message == "Message can't be deleted":
                        bot.send_message(chat.id, "لا يمكن حذف جميع الرسائل. قد تكون الرسائل قديمة جداً، أو قد لا أملك صلاحيات الحذف، أو قد لا تكون هذه مجموعة خارقة.")
                    elif err.message != "Message to delete not found":
                        LOGGER.exception("خطأ أثناء تنظيف رسائل الدردشة.")

            try:
                msg.delete()
            except BadRequest as err:
                if err.message == "Message can't be deleted":
                    bot.send_message(chat.id, "لا يمكن حذف جميع الرسائل. قد تكون الرسائل قديمة جداً، أو قد لا أملك صلاحيات الحذف، أو قد لا تكون هذه مجموعة خارقة.")
                elif err.message != "Message to delete not found":
                    LOGGER.exception("خطأ أثناء تنظيف رسائل الدردشة.")

            bot.send_message(chat.id, "تم التنظيف بنجاح.")
            return "<b>{}:</b>" \
                   "\n#تنظيف" \
                   "\n<b>المشرف:</b> {}" \
                   "\nتم تنظيف <code>{}</code> رسالة.".format(html.escape(chat.title),
                                                               mention_html(user.id, user.first_name),
                                                               delete_to - message_id)

    else:
        msg.reply_text("قم بالرد على رسالة لتحديد من أين تبدأ التنظيف.")

    return ""


@run_async
@user_admin
@loggable
def del_message(bot: Bot, update: Update) -> str:
    if update.effective_message.reply_to_message:
        user = update.effective_user
        chat = update.effective_chat
        if can_delete(chat, bot.id):
            update.effective_message.reply_to_message.delete()
            update.effective_message.delete()
            return "<b>{}:</b>" \
                   "\n#حذف" \
                   "\n<b>المشرف:</b> {}" \
                   "\nتم حذف الرسالة.".format(html.escape(chat.title),
                                               mention_html(user.id, user.first_name))
    else:
        update.effective_message.reply_text("ماذا تريد أن تحذف؟")

    return ""


# ================== المساعدة ==================
__help__ = """
*للمشرفين فقط:*
- /del: حذف الرسالة التي قمت بالرد عليها
- /purge: حذف جميع الرسائل بين هذه الرسالة والرسالة التي تم الرد عليها.
- /purge <عدد X>: حذف الرسالة التي تم الرد عليها، و X رسالة بعدها.

*الأوامر العربية (بدون /):*
حذف: حذف الرسالة التي تم الرد عليها
تنظيف: حذف جميع الرسائل من الرسالة التي تم الرد عليها إلى آخر رسالة
تنظيف <عدد>: حذف الرسالة التي تم الرد عليها وعدد محدد من الرسائل بعدها
"""

__mod_name__ = "الحذف والتنظيف"

DELETE_HANDLER = CommandHandler("del", del_message, filters=Filters.group)
PURGE_HANDLER = CommandHandler("purge", purge, filters=Filters.group, pass_args=True)

# معالجات الأوامر العربية
DELETE_AR_HANDLER = CommandHandler("حذف", del_message, filters=Filters.group)
PURGE_AR_HANDLER = CommandHandler("تنظيف", purge, filters=Filters.group, pass_args=True)

dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(PURGE_HANDLER)

dispatcher.add_handler(DELETE_AR_HANDLER)
dispatcher.add_handler(PURGE_AR_HANDLER)
