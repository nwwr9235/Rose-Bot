import html
from typing import Optional, List

import requests
from telegram import Message, Chat, Update, Bot, MessageEntity
from telegram.error import BadRequest
from telegram import ParseMode
from telegram.ext import CommandHandler, run_async, Filters, MessageHandler
from telegram.utils.helpers import mention_markdown, mention_html, escape_markdown

import tg_bot.modules.sql.welcome_sql as sql
from tg_bot import dispatcher, LOGGER
from tg_bot.modules.helper_funcs.chat_status import user_admin, can_delete
from tg_bot.modules.log_channel import loggable


@run_async
@user_admin
@loggable
def rem_cmds(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user

    if not args:
        del_pref = sql.get_cmd_pref(chat.id)
        if del_pref:
            update.effective_message.reply_text("يجب أن أحذف رسائل `@bluetextbot` الآن.")
        else:
            update.effective_message.reply_text("أنا لا أحذف رسائل `@bluetextbot` حالياً!")
        return ""

    if args[0].lower() in ("on", "yes"):
        sql.set_cmd_joined(str(chat.id), True)
        update.effective_message.reply_text("سأحاول حذف رسائل `@bluetextbot`!")
        return "<b>{}:</b>" \
               "\n#مكافحة_الأمر" \
               "\n<b>المشرف:</b> {}" \
               "\nقام بتشغيل AntiCommandBot إلى <code>ON</code>.".format(html.escape(chat.title),
                                                                         mention_html(user.id, user.first_name))
    elif args[0].lower() in ("off", "no"):
        sql.set_cmd_joined(str(chat.id), False)
        update.effective_message.reply_text("لن أحذف رسائل `@bluetextbot`.")
        return "<b>{}:</b>" \
               "\n#مكافحة_الأمر" \
               "\n<b>المشرف:</b> {}" \
               "\nقام بإيقاف AntiCommandBot إلى <code>OFF</code>.".format(html.escape(chat.title),
                                                                          mention_html(user.id, user.first_name))
    else:
        update.effective_message.reply_text("أنا أفهم 'on/yes' أو 'off/no' فقط!")
        return ""


@run_async
def rem_slash_commands(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    msg = update.effective_message
    del_pref = sql.get_cmd_pref(chat.id)

    if del_pref:
        try:
            msg.delete()
        except BadRequest as excp:
            LOGGER.info(excp)


# ================== المساعدة ==================
__help__ = """
أقوم بحذف الرسائل التي تبدأ بـ / في المجموعات والمجموعات الخارقة.
- /rmcmd <on/off>: عندما يحاول شخص إرسال رسالة @BlueTextBot، سأحاول حذفها!

*الأمر العربي (بدون /):*
منع الأوامر <on/off>: تفعيل/تعطيل حذف الأوامر.
"""

__mod_name__ = "مكافحة الأوامر"

DEL_REM_COMMANDS = CommandHandler("rmcmd", rem_cmds, pass_args=True, filters=Filters.group)
REM_SLASH_COMMANDS = MessageHandler(Filters.command & Filters.group, rem_slash_commands)

# معالجات الأوامر العربية
ANTICMD_ON_AR = CommandHandler("منع الأوامر on", lambda b,u: rem_cmds(b,u,args=["on"]), filters=Filters.group)
ANTICMD_OFF_AR = CommandHandler("منع الأوامر off", lambda b,u: rem_cmds(b,u,args=["off"]), filters=Filters.group)
ANTICMD_STATUS_AR = CommandHandler("منع الأوامر", lambda b,u: rem_cmds(b,u,args=[]), filters=Filters.group)

dispatcher.add_handler(DEL_REM_COMMANDS)
dispatcher.add_handler(REM_SLASH_COMMANDS)

dispatcher.add_handler(ANTICMD_ON_AR)
dispatcher.add_handler(ANTICMD_OFF_AR)
dispatcher.add_handler(ANTICMD_STATUS_AR)
