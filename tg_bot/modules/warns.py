import html
import re
from typing import Optional, List

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, User, CallbackQuery
from telegram import Message, Chat, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async, DispatcherHandlerStop, MessageHandler, Filters, CallbackQueryHandler
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, BAN_STICKER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import is_user_admin, bot_admin, user_admin_no_reply, user_admin, \
    can_restrict
from tg_bot.modules.helper_funcs.extraction import extract_text, extract_user_and_text, extract_user
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import split_message
from tg_bot.modules.helper_funcs.string_handling import split_quotes
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import warns_sql as sql

WARN_HANDLER_GROUP = 9
CURRENT_WARNING_FILTER_STRING = "<b>فلاتر التحذير الحالية في هذه الدردشة:</b>\n"


# ليست async
def warn(user: User, chat: Chat, reason: str, message: Message, warner: User = None) -> str:
    if is_user_admin(chat, user.id):
        message.reply_text("لا يمكن تحذير المشرفين!")
        return ""

    if warner:
        warner_tag = mention_html(warner.id, warner.first_name)
    else:
        warner_tag = "فلتر تحذير تلقائي."

    limit, soft_warn = sql.get_warn_setting(chat.id)
    num_warns, reasons = sql.warn_user(user.id, chat.id, reason)
    if num_warns >= limit:
        sql.reset_warns(user.id, chat.id)
        if soft_warn:  # طرد
            chat.unban_member(user.id)
            reply = "{} تحذيرات، {} تم طرده!".format(limit, mention_html(user.id, user.first_name))

        else:  # حظر
            chat.kick_member(user.id)
            reply = "{} تحذيرات، {} تم حظره!".format(limit, mention_html(user.id, user.first_name))

        for warn_reason in reasons:
            reply += "\n - {}".format(html.escape(warn_reason))

        message.bot.send_sticker(chat.id, BAN_STICKER)  # ملصق مطرقة الحظر
        keyboard = []
        log_reason = "<b>{}:</b>" \
                     "\n#تحذير_حظر" \
                     "\n<b>المشرف:</b> {}" \
                     "\n<b>المستخدم:</b> {}" \
                     "\n<b>السبب:</b> {}"\
                     "\n<b>العدد:</b> <code>{}/{}</code>".format(html.escape(chat.title),
                                                                  warner_tag,
                                                                  mention_html(user.id, user.first_name), 
                                                                  reason, num_warns, limit)

    else:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("إزالة التحذير", callback_data="rm_warn({})".format(user.id))]])

        reply = "{} لديه {}/{} تحذيرات... انتبه!".format(mention_html(user.id, user.first_name), num_warns,
                                                             limit)
        if reason:
            reply += "\nسبب آخر تحذير:\n{}".format(html.escape(reason))

        log_reason = "<b>{}:</b>" \
                     "\n#تحذير" \
                     "\n<b>المشرف:</b> {}" \
                     "\n<b>المستخدم:</b> {}" \
                     "\n<b>السبب:</b> {}"\
                     "\n<b>العدد:</b> <code>{}/{}</code>".format(html.escape(chat.title),
                                                                  warner_tag,
                                                                  mention_html(user.id, user.first_name), 
                                                                  reason, num_warns, limit)

    try:
        message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except BadRequest as excp:
        if excp.message == "Replied message not found":
            # لا ترد
            message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML, quote=False)
        else:
            raise
    return log_reason


@run_async
@user_admin_no_reply
@bot_admin
@loggable
def button(bot: Bot, update: Update) -> str:
    query = update.callback_query
    user = update.effective_user
    match = re.match(r"rm_warn\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat = update.effective_chat
        res = sql.remove_warn(user_id, chat.id)
        if res:
            update.effective_message.edit_text(
                "تمت إزالة التحذير بواسطة {}.".format(mention_html(user.id, user.first_name)),
                parse_mode=ParseMode.HTML)
            user_member = chat.get_member(user_id)
            return "<b>{}:</b>" \
                   "\n#إزالة_تحذير" \
                   "\n<b>المشرف:</b> {}" \
                   "\n<b>المستخدم:</b> {}".format(html.escape(chat.title),
                                              mention_html(user.id, user.first_name),
                                              mention_html(user_member.user.id, user_member.user.first_name))
        else:
            update.effective_message.edit_text(
                "المستخدم ليس لديه تحذيرات.".format(mention_html(user.id, user.first_name)),
                parse_mode=ParseMode.HTML)

    return ""


@run_async
@user_admin
@can_restrict
@loggable
def warn_user(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    chat = update.effective_chat
    warner = update.effective_user

    user_id, reason = extract_user_and_text(message, args)

    if user_id:
        if message.reply_to_message and message.reply_to_message.from_user.id == user_id:
            return warn(message.reply_to_message.from_user, chat, reason, message.reply_to_message, warner)
        else:
            return warn(chat.get_member(user_id).user, chat, reason, message, warner)
    else:
        message.reply_text("لم يتم تحديد مستخدم!")
    return ""


@run_async
@user_admin
@bot_admin
@loggable
def reset_warns(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    user_id = extract_user(message, args)

    if user_id:
        sql.reset_warns(user_id, chat.id)
        message.reply_text("تم إعادة تعيين التحذيرات!")
        warned = chat.get_member(user_id).user
        return "<b>{}:</b>" \
               "\n#إعادة_تعيين_تحذيرات" \
               "\n<b>المشرف:</b> {}" \
               "\n<b>المستخدم:</b> {}".format(html.escape(chat.title),
                                          mention_html(user.id, user.first_name),
                                          mention_html(warned.id, warned.first_name))
    else:
        message.reply_text("لم يتم تحديد مستخدم!")
    return ""


@run_async
def warns(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    chat = update.effective_chat
    user_id = extract_user(message, args) or update.effective_user.id
    result = sql.get_warns(user_id, chat.id)

    if result and result[0] != 0:
        num_warns, reasons = result
        limit, soft_warn = sql.get_warn_setting(chat.id)

        if reasons:
            text = "هذا المستخدم لديه {}/{} تحذيراً، للأسباب التالية:".format(num_warns, limit)
            for reason in reasons:
                text += "\n - {}".format(reason)

            msgs = split_message(text)
            for msg in msgs:
                update.effective_message.reply_text(msg)
        else:
            update.effective_message.reply_text(
                "المستخدم لديه {}/{} تحذيراً، ولكن لا توجد أسباب لأي منها.".format(num_warns, limit))
    else:
        update.effective_message.reply_text("هذا المستخدم ليس لديه أي تحذيرات!")


# معالج إيقاف dispatcher - لا تستخدم async
@user_admin
def add_warn_filter(bot: Bot, update: Update):
    chat = update.effective_chat
    msg = update.effective_message

    args = msg.text.split(None, 1)

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) >= 2:
        keyword = extracted[0].lower()
        content = extracted[1]

    else:
        return

    for handler in dispatcher.handlers.get(WARN_HANDLER_GROUP, []):
        if handler.filters == (keyword, chat.id):
            dispatcher.remove_handler(handler, WARN_HANDLER_GROUP)

    sql.add_warn_filter(chat.id, keyword, content)

    update.effective_message.reply_text("تمت إضافة معالج تحذير لـ '{}'!".format(keyword))
    raise DispatcherHandlerStop


@user_admin
def remove_warn_filter(bot: Bot, update: Update):
    chat = update.effective_chat
    msg = update.effective_message

    args = msg.text.split(None, 1)

    if len(args) < 2:
        return

    extracted = split_quotes(args[1])

    if len(extracted) < 1:
        return

    to_remove = extracted[0]

    chat_filters = sql.get_chat_warn_triggers(chat.id)

    if not chat_filters:
        msg.reply_text("لا توجد فلاتر تحذير نشطة هنا!")
        return

    for filt in chat_filters:
        if filt == to_remove:
            sql.remove_warn_filter(chat.id, to_remove)
            msg.reply_text("حسناً، سأتوقف عن تحذير الأشخاص بسبب ذلك.")
            raise DispatcherHandlerStop

    msg.reply_text("هذا ليس فلتر تحذير حالي - استخدم /warnlist لعرض جميع فلاتر التحذير النشطة.")


@run_async
def list_warn_filters(bot: Bot, update: Update):
    chat = update.effective_chat
    all_handlers = sql.get_chat_warn_triggers(chat.id)

    if not all_handlers:
        update.effective_message.reply_text("لا توجد فلاتر تحذير نشطة هنا!")
        return

    filter_list = CURRENT_WARNING_FILTER_STRING
    for keyword in all_handlers:
        entry = " - {}\n".format(html.escape(keyword))
        if len(entry) + len(filter_list) > telegram.MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)
            filter_list = entry
        else:
            filter_list += entry

    if not filter_list == CURRENT_WARNING_FILTER_STRING:
        update.effective_message.reply_text(filter_list, parse_mode=ParseMode.HTML)


@run_async
@loggable
def reply_filter(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    message = update.effective_message

    chat_warn_filters = sql.get_chat_warn_triggers(chat.id)
    to_match = extract_text(message)
    if not to_match:
        return ""

    for keyword in chat_warn_filters:
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            user = update.effective_user
            warn_filter = sql.get_warn_filter(chat.id, keyword)
            return warn(user, chat, warn_filter.reply, message)
    return ""


@run_async
@user_admin
@loggable
def set_warn_limit(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if args:
        if args[0].isdigit():
            if int(args[0]) < 3:
                msg.reply_text("الحد الأدنى للتحذيرات هو 3!")
            else:
                sql.set_warn_limit(chat.id, int(args[0]))
                msg.reply_text("تم تحديث حد التحذير إلى {}".format(args[0]))
                return "<b>{}:</b>" \
                       "\n#تعيين_حد_تحذير" \
                       "\n<b>المشرف:</b> {}" \
                       "\nتم تعيين حد التحذير إلى <code>{}</code>".format(html.escape(chat.title),
                                                                        mention_html(user.id, user.first_name), args[0])
        else:
            msg.reply_text("أعطني رقماً كوسيط!")
    else:
        limit, soft_warn = sql.get_warn_setting(chat.id)

        msg.reply_text("حد التحذير الحالي هو {}".format(limit))
    return ""


@run_async
@user_admin
def set_warn_strength(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if args:
        if args[0].lower() in ("on", "yes"):
            sql.set_warn_strength(chat.id, False)
            msg.reply_text("سيؤدي تجاوز عدد التحذيرات الآن إلى حظر المستخدم!")
            return "<b>{}:</b>\n" \
                   "<b>المشرف:</b> {}\n" \
                   "قام بتشغيل التحذيرات القوية. سيتم حظر المستخدمين.".format(html.escape(chat.title),
                                                                            mention_html(user.id, user.first_name))

        elif args[0].lower() in ("off", "no"):
            sql.set_warn_strength(chat.id, True)
            msg.reply_text("سيؤدي تجاوز عدد التحذيرات الآن إلى طرد المستخدم! يمكن للمستخدم الانضمام مرة أخرى بعد ذلك.")
            return "<b>{}:</b>\n" \
                   "<b>المشرف:</b> {}\n" \
                   "قام بإيقاف التحذيرات القوية. سيتم طرد المستخدمين فقط.".format(html.escape(chat.title),
                                                                                  mention_html(user.id,
                                                                                               user.first_name))

        else:
            msg.reply_text("أنا أفهم فقط on/yes/no/off!")
    else:
        limit, soft_warn = sql.get_warn_setting(chat.id)
        if soft_warn:
            msg.reply_text("التحذيرات حالياً مضبوطة على *طرد* المستخدمين عند تجاوز الحد.",
                           parse_mode=ParseMode.MARKDOWN)
        else:
            msg.reply_text("التحذيرات حالياً مضبوطة على *حظر* المستخدمين عند تجاوز الحد.",
                           parse_mode=ParseMode.MARKDOWN)
    return ""


def __stats__():
    return "{} تحذير إجمالي، عبر {} دردشة.\n" \
           "{} فلتر تحذير، عبر {} دردشة.".format(sql.num_warns(), sql.num_warn_chats(),
                                                      sql.num_warn_filters(), sql.num_warn_filter_chats())


def __import_data__(chat_id, data):
    for user_id, count in data.get('warns', {}).items():
        for x in range(int(count)):
            sql.warn_user(user_id, chat_id)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    num_warn_filters = sql.num_warn_chat_filters(chat_id)
    limit, soft_warn = sql.get_warn_setting(chat_id)
    return "هذه الدردشة لديها `{}` فلتر تحذير. تحتاج إلى `{}` تحذير " \
           "قبل أن يتم *{}* المستخدم.".format(num_warn_filters, limit, "طرده" if soft_warn else "حظره")


# ================== المساعدة ==================
__help__ = """
- /warns <المستخدم>: الحصول على عدد وأسباب تحذيرات المستخدم.
- /warnlist: قائمة بجميع فلاتر التحذير الحالية.

*للمشرفين فقط:*
- /warn <المستخدم>: تحذير مستخدم. بعد 3 تحذيرات، سيتم حظر المستخدم من المجموعة. يمكن استخدامه أيضاً كرد.
- /resetwarn <المستخدم>: إعادة تعيين التحذيرات لمستخدم. يمكن استخدامه أيضاً كرد.
- /addwarn <كلمة مفتاحية> <رسالة الرد>: تعيين فلتر تحذير على كلمة مفتاحية معينة. إذا أردت أن تكون كلمتك المفتاحية جملة، ضعها بين اقتباسات، مثل: `/addwarn "غاضب جداً" هذا مستخدم غاضب`.
- /nowarn <كلمة مفتاحية>: إيقاف فلتر تحذير.
- /warnlimit <رقم>: تعيين حد التحذير.
- /strongwarn <on/yes/off/no>: إذا تم ضبطه على on، فإن تجاوز حد التحذير سيؤدي إلى حظر. وإلا، سيتم الطرد فقط.

*الأوامر العربية (بدون /):*
تحذير <بالرد>: تحذير المستخدم الذي تم الرد عليه
تحذيراتي: عرض تحذيراتي
تحذيرات <بالرد>: عرض تحذيرات المستخدم الذي تم الرد عليه
إعادة تحذيرات <بالرد>: إعادة تعيين تحذيرات المستخدم
إضافة فلتر تحذير <كلمة> <السبب>: إضافة فلتر تحذير لكلمة معينة
إزالة فلتر تحذير <كلمة>: إزالة فلتر تحذير
فلاتر تحذير: عرض فلاتر التحذير الحالية
حد تحذير <رقم>: تعيين حد التحذير
تحذير قوي <on/off>: تفعيل/تعطيل التحذير القوي (حظر بدلاً من طرد)
"""

__mod_name__ = "التحذيرات"

WARN_HANDLER = CommandHandler("warn", warn_user, pass_args=True, filters=Filters.group)
RESET_WARN_HANDLER = CommandHandler(["resetwarn", "resetwarns"], reset_warns, pass_args=True, filters=Filters.group)
CALLBACK_QUERY_HANDLER = CallbackQueryHandler(button, pattern=r"rm_warn")
MYWARNS_HANDLER = DisableAbleCommandHandler("warns", warns, pass_args=True, filters=Filters.group)
ADD_WARN_HANDLER = CommandHandler("addwarn", add_warn_filter, filters=Filters.group)
RM_WARN_HANDLER = CommandHandler(["nowarn", "stopwarn"], remove_warn_filter, filters=Filters.group)
LIST_WARN_HANDLER = DisableAbleCommandHandler(["warnlist", "warnfilters"], list_warn_filters, filters=Filters.group, admin_ok=True)
WARN_FILTER_HANDLER = MessageHandler(CustomFilters.has_text & Filters.group, reply_filter)
WARN_LIMIT_HANDLER = CommandHandler("warnlimit", set_warn_limit, pass_args=True, filters=Filters.group)
WARN_STRENGTH_HANDLER = CommandHandler("strongwarn", set_warn_strength, pass_args=True, filters=Filters.group)

# معالجات الأوامر العربية
WARN_AR_HANDLER = MessageHandler(Filters.regex(r'^تحذير$') & Filters.reply, warn_user, pass_args=True)
MYWARNS_AR_HANDLER = MessageHandler(Filters.regex(r'^تحذيراتي$'), lambda b,u: warns(b,u,args=[]))
WARNS_AR_HANDLER = MessageHandler(Filters.regex(r'^تحذيرات$') & Filters.reply, lambda b,u: warns(b,u,args=[str(u.message.reply_to_message.from_user.id)]))
RESET_WARN_AR_HANDLER = MessageHandler(Filters.regex(r'^إعادة تحذيرات$') & Filters.reply, lambda b,u: reset_warns(b,u,args=[str(u.message.reply_to_message.from_user.id)]))
ADD_WARN_FILTER_AR_HANDLER = MessageHandler(Filters.regex(r'^إضافة فلتر تحذير (.+?) (.+)$'), add_warn_filter)
RM_WARN_FILTER_AR_HANDLER = MessageHandler(Filters.regex(r'^إزالة فلتر تحذير (.+)$'), remove_warn_filter)
LIST_WARN_FILTERS_AR_HANDLER = MessageHandler(Filters.regex(r'^فلاتر تحذير$'), list_warn_filters)
WARN_LIMIT_AR_HANDLER = MessageHandler(Filters.regex(r'^حد تحذير (\d+)$'), set_warn_limit, pass_args=True)
WARN_STRENGTH_AR_HANDLER = MessageHandler(Filters.regex(r'^تحذير قوي (on|off)$'), set_warn_strength, pass_args=True)

dispatcher.add_handler(WARN_HANDLER)
dispatcher.add_handler(CALLBACK_QUERY_HANDLER)
dispatcher.add_handler(RESET_WARN_HANDLER)
dispatcher.add_handler(MYWARNS_HANDLER)
dispatcher.add_handler(ADD_WARN_HANDLER)
dispatcher.add_handler(RM_WARN_HANDLER)
dispatcher.add_handler(LIST_WARN_HANDLER)
dispatcher.add_handler(WARN_LIMIT_HANDLER)
dispatcher.add_handler(WARN_STRENGTH_HANDLER)
dispatcher.add_handler(WARN_FILTER_HANDLER, WARN_HANDLER_GROUP)

dispatcher.add_handler(WARN_AR_HANDLER)
dispatcher.add_handler(MYWARNS_AR_HANDLER)
dispatcher.add_handler(WARNS_AR_HANDLER)
dispatcher.add_handler(RESET_WARN_AR_HANDLER)
dispatcher.add_handler(ADD_WARN_FILTER_AR_HANDLER)
dispatcher.add_handler(RM_WARN_FILTER_AR_HANDLER)
dispatcher.add_handler(LIST_WARN_FILTERS_AR_HANDLER)
dispatcher.add_handler(WARN_LIMIT_AR_HANDLER)
dispatcher.add_handler(WARN_STRENGTH_AR_HANDLER)
