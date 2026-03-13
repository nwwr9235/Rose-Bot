import html
import re
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters, run_async

import tg_bot.modules.sql.blacklist_sql as sql
from tg_bot import dispatcher, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin, user_not_admin
from tg_bot.modules.helper_funcs.extraction import extract_text
from tg_bot.modules.helper_funcs.misc import split_message

BLACKLIST_GROUP = 11

BASE_BLACKLIST_STRING = "الكلمات <b>المحظورة</b> الحالية:\n"


@run_async
def blacklist(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message
    chat = update.effective_chat

    all_blacklisted = sql.get_chat_blacklist(chat.id)

    filter_list = BASE_BLACKLIST_STRING

    if len(args) > 0 and args[0].lower() == 'copy':
        for trigger in all_blacklisted:
            filter_list += "<code>{}</code>\n".format(html.escape(trigger))
    else:
        for trigger in all_blacklisted:
            filter_list += " - <code>{}</code>\n".format(html.escape(trigger))

    split_text = split_message(filter_list)
    for text in split_text:
        if text == BASE_BLACKLIST_STRING:
            msg.reply_text("لا توجد كلمات محظورة هنا!")
            return
        msg.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
@user_admin
def add_blacklist(bot: Bot, update: Update):
    msg = update.effective_message
    chat = update.effective_chat
    words = msg.text.split(None, 1)
    if len(words) > 1:
        text = words[1]
        to_blacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
        for trigger in to_blacklist:
            sql.add_to_blacklist(chat.id, trigger.lower())

        if len(to_blacklist) == 1:
            msg.reply_text("تمت إضافة <code>{}</code> إلى قائمة الحظر!".format(html.escape(to_blacklist[0])),
                           parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(
                "تمت إضافة <code>{}</code> كلمة إلى قائمة الحظر.".format(len(to_blacklist)), parse_mode=ParseMode.HTML)

    else:
        msg.reply_text("أخبرني بالكلمات التي تريد إضافتها إلى قائمة الحظر.")


@run_async
@user_admin
def unblacklist(bot: Bot, update: Update):
    msg = update.effective_message
    chat = update.effective_chat
    words = msg.text.split(None, 1)
    if len(words) > 1:
        text = words[1]
        to_unblacklist = list(set(trigger.strip() for trigger in text.split("\n") if trigger.strip()))
        successful = 0
        for trigger in to_unblacklist:
            success = sql.rm_from_blacklist(chat.id, trigger.lower())
            if success:
                successful += 1

        if len(to_unblacklist) == 1:
            if successful:
                msg.reply_text("تمت إزالة <code>{}</code> من قائمة الحظر!".format(html.escape(to_unblacklist[0])),
                               parse_mode=ParseMode.HTML)
            else:
                msg.reply_text("هذه الكلمة ليست في قائمة الحظر...!")

        elif successful == len(to_unblacklist):
            msg.reply_text(
                "تمت إزالة <code>{}</code> كلمة من قائمة الحظر.".format(successful), parse_mode=ParseMode.HTML)

        elif not successful:
            msg.reply_text(
                "لم يتم إزالة أي من هذه الكلمات لأنها غير موجودة في القائمة.", parse_mode=ParseMode.HTML)

        else:
            msg.reply_text(
                "تمت إزالة <code>{}</code> كلمة من قائمة الحظر. {} كلمة غير موجودة ولم تتم إزالتها.".format(successful, len(to_unblacklist) - successful),
                parse_mode=ParseMode.HTML)
    else:
        msg.reply_text("أخبرني بالكلمات التي تريد إزالتها من قائمة الحظر.")


@run_async
@user_not_admin
def del_blacklist(bot: Bot, update: Update):
    chat = update.effective_chat
    message = update.effective_message
    to_match = extract_text(message)
    if not to_match:
        return

    chat_filters = sql.get_chat_blacklist(chat.id)
    for trigger in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(trigger) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("خطأ أثناء حذف رسالة القائمة السوداء.")
            break


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    blacklisted = sql.num_blacklist_chat_filters(chat_id)
    return "هناك {} كلمة محظورة.".format(blacklisted)


def __stats__():
    return "{} كلمة محظورة، عبر {} دردشة.".format(sql.num_blacklist_filters(),
                                                            sql.num_blacklist_filter_chats())


# ================== المساعدة ==================
__mod_name__ = "قائمة الحظر"

__help__ = """
تستخدم قوائم الحظر لمنع ذكر كلمات معينة في المجموعة. كلما تم ذكر الكلمة، سيتم حذف الرسالة فوراً. من الجيد أحياناً دمج هذا مع عوامل التصفية التحذيرية!

*ملاحظة:* قوائم الحظر لا تؤثر على مشرفي المجموعة.

- /blacklist: عرض الكلمات المحظورة الحالية.

*للمشرفين فقط:*
- /addblacklist <كلمات>: إضافة كلمات إلى قائمة الحظر. كل سطر يعتبر كلمة واحدة، لذا يمكنك استخدام أسطر مختلفة لإضافة عدة كلمات.
- /unblacklist <كلمات>: إزالة كلمات من قائمة الحظر. نفس منطق الأسطر الجديدة ينطبق هنا، لذا يمكنك إزالة عدة كلمات دفعة واحدة.
- /rmblacklist <كلمات>: نفس ما سبق.

*الأوامر العربية (بدون /):*
قائمة الحظر: عرض الكلمات المحظورة
إضافة حظر <كلمات>: إضافة كلمات إلى القائمة
إزالة حظر <كلمات>: إزالة كلمات من القائمة
"""

BLACKLIST_HANDLER = DisableAbleCommandHandler("blacklist", blacklist, filters=Filters.group, pass_args=True,
                                              admin_ok=True)
ADD_BLACKLIST_HANDLER = CommandHandler("addblacklist", add_blacklist, filters=Filters.group)
UNBLACKLIST_HANDLER = CommandHandler(["unblacklist", "rmblacklist"], unblacklist, filters=Filters.group)
BLACKLIST_DEL_HANDLER = MessageHandler(
    (Filters.text | Filters.command | Filters.sticker | Filters.photo) & Filters.group, del_blacklist)

# معالجات الأوامر العربية
BLACKLIST_AR_HANDLER = CommandHandler("قائمة الحظر", blacklist, filters=Filters.group, pass_args=True)
ADD_BLACKLIST_AR_HANDLER = CommandHandler("إضافة حظر", add_blacklist, filters=Filters.group)
UNBLACKLIST_AR_HANDLER = CommandHandler(["إزالة حظر", "حذف حظر"], unblacklist, filters=Filters.group)

dispatcher.add_handler(BLACKLIST_HANDLER)
dispatcher.add_handler(ADD_BLACKLIST_HANDLER)
dispatcher.add_handler(UNBLACKLIST_HANDLER)
dispatcher.add_handler(BLACKLIST_DEL_HANDLER, group=BLACKLIST_GROUP)

dispatcher.add_handler(BLACKLIST_AR_HANDLER)
dispatcher.add_handler(ADD_BLACKLIST_AR_HANDLER)
dispatcher.add_handler(UNBLACKLIST_AR_HANDLER)
