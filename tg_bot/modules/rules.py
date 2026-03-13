from typing import Optional

from telegram import Message, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown

import tg_bot.modules.sql.rules_sql as sql
from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.helper_funcs.string_handling import markdown_parser


@run_async
def get_rules(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    send_rules(update, chat_id)


# ليست async - ليست من معالج
def send_rules(update, chat_id, from_pm=False):
    bot = dispatcher.bot
    user = update.effective_user
    try:
        chat = bot.get_chat(chat_id)
    except BadRequest as excp:
        if excp.message == "Chat not found" and from_pm:
            bot.send_message(user.id, "اختصار القواعد لهذه الدردشة لم يتم تعيينه بشكل صحيح! اطلب من المشرفين إصلاح هذا.")
            return
        else:
            raise

    rules = sql.get_rules(chat_id)
    text = "قواعد *{}* هي:\n\n{}".format(escape_markdown(chat.title), rules)

    if from_pm and rules:
        bot.send_message(user.id, text, parse_mode=ParseMode.MARKDOWN)
    elif from_pm:
        bot.send_message(user.id, "مشرفو المجموعة لم يضعوا أي قواعد لهذه الدردشة بعد. هذا لا يعني أنها خالية من القوانين...!")
    elif rules:
        update.effective_message.reply_text("تواصل معي في الخاص للحصول على قواعد هذه المجموعة.",
                                            reply_markup=InlineKeyboardMarkup(
                                                [[InlineKeyboardButton(text="القواعد",
                                                                       url="t.me/{}?start={}".format(bot.username,
                                                                                                     chat_id))]]))
    else:
        update.effective_message.reply_text("مشرفو المجموعة لم يضعوا أي قواعد لهذه الدردشة بعد. "
                                            "هذا لا يعني أنها خالية من القوانين...!")


@run_async
@user_admin
def set_rules(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    msg = update.effective_message
    raw_text = msg.text
    args = raw_text.split(None, 1)  # استخدم maxsplit في بايثون لفصل الأمر والوسائط
    if len(args) == 2:
        txt = args[1]
        offset = len(txt) - len(raw_text)  # تعيين الإزاحة الصحيحة بالنسبة للأمر
        markdown_rules = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)

        sql.set_rules(chat_id, markdown_rules)
        update.effective_message.reply_text("تم تعيين قواعد هذه المجموعة بنجاح.")


@run_async
@user_admin
def clear_rules(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    sql.set_rules(chat_id, "")
    update.effective_message.reply_text("تم مسح القواعد بنجاح!")


def __stats__():
    return "{} دردشة لديها قواعد محددة.".format(sql.num_chats())


def __import_data__(chat_id, data):
    # تعيين قواعد الدردشة
    rules = data.get('info', {}).get('rules', "")
    sql.set_rules(chat_id, rules)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "هذه الدردشة لديها قواعد محددة: `{}`".format(bool(sql.get_rules(chat_id)))


# ================== المساعدة ==================
__help__ = """
- /rules: الحصول على قواعد هذه الدردشة.

*للمشرفين فقط:*
- /setrules <قواعدك هنا>: تعيين قواعد هذه الدردشة.
- /clearrules: مسح قواعد هذه الدردشة.

*الأوامر العربية (بدون /):*
القواعد: عرض قواعد المجموعة
تعيين قواعد <النص>: تعيين قواعد المجموعة
مسح قواعد: مسح قواعد المجموعة
"""

__mod_name__ = "القواعد"

GET_RULES_HANDLER = CommandHandler("rules", get_rules, filters=Filters.group)
SET_RULES_HANDLER = CommandHandler("setrules", set_rules, filters=Filters.group)
RESET_RULES_HANDLER = CommandHandler("clearrules", clear_rules, filters=Filters.group)

# معالجات الأوامر العربية
GET_RULES_AR_HANDLER = CommandHandler("القواعد", get_rules, filters=Filters.group)
SET_RULES_AR_HANDLER = CommandHandler("تعيين قواعد", set_rules, filters=Filters.group)
CLEAR_RULES_AR_HANDLER = CommandHandler("مسح قواعد", clear_rules, filters=Filters.group)

dispatcher.add_handler(GET_RULES_HANDLER)
dispatcher.add_handler(SET_RULES_HANDLER)
dispatcher.add_handler(RESET_RULES_HANDLER)

dispatcher.add_handler(GET_RULES_AR_HANDLER)
dispatcher.add_handler(SET_RULES_AR_HANDLER)
dispatcher.add_handler(CLEAR_RULES_AR_HANDLER)
