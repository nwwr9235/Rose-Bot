from functools import wraps
from typing import Optional

from tg_bot.modules.helper_funcs.misc import is_module_loaded

FILENAME = __name__.rsplit(".", 1)[-1]

if is_module_loaded(FILENAME):
    from telegram import Bot, Update, ParseMode, Message, Chat
    from telegram.error import BadRequest, Unauthorized
    from telegram.ext import CommandHandler, run_async, MessageHandler
    from telegram.utils.helpers import escape_markdown

    from tg_bot import dispatcher, LOGGER
    from tg_bot.modules.helper_funcs.chat_status import user_admin
    from tg_bot.modules.sql import log_channel_sql as sql


    def loggable(func):
        @wraps(func)
        def log_action(bot: Bot, update: Update, *args, **kwargs):
            result = func(bot, update, *args, **kwargs)
            chat = update.effective_chat
            message = update.effective_message
            if result:
                if chat.type == chat.SUPERGROUP and chat.username:
                    result += "\n<b>الرابط:</b> " \
                              "<a href=\"http://telegram.me/{}/{}\">اضغط هنا</a>".format(chat.username,
                                                                                           message.message_id)
                log_chat = sql.get_chat_log_channel(chat.id)
                if log_chat:
                    send_log(bot, log_chat, chat.id, result)
            elif result == "":
                pass
            else:
                LOGGER.warning("%s was set as loggable, but had no return statement.", func)

            return result

        return log_action


    def send_log(bot: Bot, log_chat_id: str, orig_chat_id: str, result: str):
        try:
            bot.send_message(log_chat_id, result, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            if excp.message == "Chat not found":
                bot.send_message(orig_chat_id, "تم حذف قناة السجل هذه - إلغاء التعيين.")
                sql.stop_chat_logging(orig_chat_id)
            else:
                LOGGER.warning(excp.message)
                LOGGER.warning(result)
                LOGGER.exception("تعذر التحليل")

                bot.send_message(log_chat_id, result + "\n\nتم تعطيل التنسيق بسبب خطأ غير متوقع.")


    @run_async
    @user_admin
    def logging(bot: Bot, update: Update):
        message = update.effective_message
        chat = update.effective_chat

        log_channel = sql.get_chat_log_channel(chat.id)
        if log_channel:
            log_channel_info = bot.get_chat(log_channel)
            message.reply_text(
                "هذه المجموعة ترسل جميع سجلاتها إلى: {} (`{}`)".format(escape_markdown(log_channel_info.title),
                                                                         log_channel),
                parse_mode=ParseMode.MARKDOWN)

        else:
            message.reply_text("لم يتم تعيين قناة سجل لهذه المجموعة!")


    @run_async
    @user_admin
    def setlog(bot: Bot, update: Update):
        message = update.effective_message
        chat = update.effective_chat
        if chat.type == chat.CHANNEL:
            message.reply_text("الآن، قم بإعادة توجيه /setlog إلى المجموعة التي تريد ربط هذه القناة بها!")

        elif message.forward_from_chat:
            sql.set_chat_log_channel(chat.id, message.forward_from_chat.id)
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("خطأ في حذف الرسالة في قناة السجل. يجب أن تعمل على أي حال.")

            try:
                bot.send_message(message.forward_from_chat.id,
                                 "تم تعيين هذه القناة كقناة سجل لـ {}.".format(
                                     chat.title or chat.first_name))
            except Unauthorized as excp:
                if excp.message == "Forbidden: bot is not a member of the channel chat":
                    bot.send_message(chat.id, "تم تعيين قناة السجل بنجاح!")
                else:
                    LOGGER.exception("خطأ في تعيين قناة السجل.")

            bot.send_message(chat.id, "تم تعيين قناة السجل بنجاح!")

        else:
            message.reply_text("خطوات تعيين قناة السجل هي:\n"
                               " - أضف البوت إلى القناة المطلوبة\n"
                               " - أرسل /setlog إلى القناة\n"
                               " - أعد توجيه /setlog إلى المجموعة\n")


    @run_async
    @user_admin
    def unsetlog(bot: Bot, update: Update):
        message = update.effective_message
        chat = update.effective_chat

        log_channel = sql.stop_chat_logging(chat.id)
        if log_channel:
            bot.send_message(log_channel, "تم فك ارتباط القناة من {}".format(chat.title))
            message.reply_text("تم إلغاء تعيين قناة السجل.")

        else:
            message.reply_text("لم يتم تعيين قناة سجل بعد!")


    def __stats__():
        return "{} قناة سجل محددة.".format(sql.num_logchannels())


    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)


    def __chat_settings__(chat_id, user_id):
        log_channel = sql.get_chat_log_channel(chat_id)
        if log_channel:
            log_channel_info = dispatcher.bot.get_chat(log_channel)
            return "هذه المجموعة ترسل جميع سجلاتها إلى: {} (`{}`)".format(escape_markdown(log_channel_info.title),
                                                                            log_channel)
        return "لم يتم تعيين قناة سجل لهذه المجموعة!"


    # ================== المساعدة ==================
    __help__ = """
*للمشرفين فقط:*
- /logchannel: الحصول على معلومات قناة السجل
- /setlog: تعيين قناة السجل.
- /unsetlog: إلغاء تعيين قناة السجل.

تعيين قناة السجل يتم عن طريق:
- إضافة البوت إلى القناة المطلوبة (كمشرف!)
- إرسال /setlog في القناة
- إعادة توجيه /setlog إلى المجموعة

*الأوامر العربية (بدون /):*
قناة السجل: عرض معلومات قناة السجل الحالية
تعيين قناة سجل: تعيين قناة السجل
إلغاء قناة سجل: إلغاء تعيين قناة السجل
"""

    __mod_name__ = "قنوات السجل"

    LOG_HANDLER = CommandHandler("logchannel", logging)
    SET_LOG_HANDLER = CommandHandler("setlog", setlog)
    UNSET_LOG_HANDLER = CommandHandler("unsetlog", unsetlog)

    # معالجات الأوامر العربية
    LOG_AR_HANDLER = CommandHandler("قناة السجل", logging)
    SET_LOG_AR_HANDLER = CommandHandler("تعيين قناة سجل", setlog)
    UNSET_LOG_AR_HANDLER = CommandHandler("إلغاء قناة سجل", unsetlog)

    dispatcher.add_handler(LOG_HANDLER)
    dispatcher.add_handler(SET_LOG_HANDLER)
    dispatcher.add_handler(UNSET_LOG_HANDLER)

    dispatcher.add_handler(LOG_AR_HANDLER)
    dispatcher.add_handler(SET_LOG_AR_HANDLER)
    dispatcher.add_handler(UNSET_LOG_AR_HANDLER)

else:
    # run anyway if module not loaded
    def loggable(func):
        return func
