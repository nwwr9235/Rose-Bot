import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import run_async, CommandHandler, Filters, MessageHandler
from telegram.utils.helpers import mention_html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, User, CallbackQuery

from tg_bot import dispatcher, BAN_STICKER, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_ban_protected, can_restrict, \
    is_user_admin, is_user_in_chat, is_bot_admin, _TELE_GRAM_ID_S
from tg_bot.modules.helper_funcs.extraction import extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.helper_funcs.filters import CustomFilters

RBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Peer_id_invalid",
    "Group chat was deactivated",
    "Need to be inviter of a user to kick it from a basic group",
    "Chat_admin_required",
    "Only the creator of a basic group can kick group administrators",
    "Channel_private",
    "Not in the chat"
}

RUNBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Peer_id_invalid",
    "Group chat was deactivated",
    "Need to be inviter of a user to kick it from a basic group",
    "Chat_admin_required",
    "Only the creator of a basic group can kick group administrators",
    "Channel_private",
    "Not in the chat"
}


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if user.id not in _TELE_GRAM_ID_S:
        admin_user = chat.get_member(user.id)
        if not (admin_user.can_restrict_members or admin_user.status == "creator"):
            return

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("لم أتمكن من العثور على هذا المستخدم.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("لا يمكنني العثور على هذا المستخدم")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("لا يمكنني حظر المشرفين!")
        return ""

    if user_id == bot.id:
        message.reply_text("لن أحظر نفسي، هل أنت مجنون؟")
        return ""

    log = "<b>{}:</b>" \
          "\n#محظور" \
          "\n<b>المشرف:</b> {}" \
          "\n<b>المستخدم:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name))
    if reason:
        log += "\n<b>السبب:</b> {}".format(reason)

    try:
        chat.kick_member(user_id)
        bot.send_sticker(chat.id, BAN_STICKER)
        keyboard = []
        reply = "تم حظر {}!".format(mention_html(member.user.id, member.user.first_name))
        message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        return log

    except BadRequest as excp:
        if excp.message == "Replied message not found":
            chat_id = update.effective_chat.id
            message = update.effective_message
            reply = "تم حظر {}!".format(mention_html(member.user.id, member.user.first_name))
            bot.send_message(chat_id, reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("خطأ في حظر المستخدم %s في الدردشة %s (%s) بسبب %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("لا يمكنني حظر هذا المستخدم.")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if user.id not in _TELE_GRAM_ID_S:
        admin_user = chat.get_member(user.id)
        if not (admin_user.can_restrict_members or admin_user.status == "creator"):
            return

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("لم أتمكن من العثور على هذا المستخدم.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("لا يمكنني العثور على هذا المستخدم")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("لا يمكنني حظر المشرفين!")
        return ""

    if user_id == bot.id:
        message.reply_text("لن أحظر نفسي، هل أنت مجنون؟")
        return ""

    if not reason:
        message.reply_text("لم تحدد مدة الحظر لهذا المستخدم!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    bantime = extract_time(message, time_val)

    if not bantime:
        return ""

    log = "<b>{}:</b>" \
          "\n#حظر_مؤقت" \
          "\n<b>المشرف:</b> {}" \
          "\n<b>المستخدم:</b> {}" \
          "\n<b>المدة:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name), time_val)
    if reason:
        log += "\n<b>السبب:</b> {}".format(reason)

    try:
        chat.kick_member(user_id, until_date=bantime)
        bot.send_sticker(chat.id, BAN_STICKER)
        message.reply_text("تم الحظر! المستخدم محظور لمدة {}.".format(time_val))
        return log

    except BadRequest as excp:
        if excp.message == "Replied message not found":
            message.reply_text("تم الحظر! المستخدم محظور لمدة {}.".format(time_val), quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("خطأ في حظر المستخدم %s في الدردشة %s (%s) بسبب %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("لا يمكنني حظر هذا المستخدم.")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def kick(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if user.id not in _TELE_GRAM_ID_S:
        admin_user = chat.get_member(user.id)
        if not (admin_user.can_restrict_members or admin_user.status == "creator"):
            return

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("لا يمكنني العثور على هذا المستخدم")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id):
        message.reply_text("لا يمكنني طرد المشرفين!")
        return ""

    if user_id == bot.id:
        message.reply_text("لن أفعل ذلك!")
        return ""

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        bot.send_sticker(chat.id, BAN_STICKER)
        message.reply_text("تم الطرد!")
        log = "<b>{}:</b>" \
              "\n#مطرود" \
              "\n<b>المشرف:</b> {}" \
              "\n<b>المستخدم:</b> {}".format(html.escape(chat.title),
                                         mention_html(user.id, user.first_name),
                                         mention_html(member.user.id, member.user.first_name))
        if reason:
            log += "\n<b>السبب:</b> {}".format(reason)

        return log

    else:
        message.reply_text("لا يمكنني طرد هذا المستخدم.")

    return ""


@run_async
@bot_admin
@can_restrict
def kickme(bot: Bot, update: Update):
    user_id = update.effective_message.from_user.id
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("كنت أتمنى ذلك... لكنك مشرف.")
        return

    res = update.effective_chat.unban_member(user_id)  # unban on current user = kick
    if res:
        update.effective_message.reply_text("تم الطرد.")
    else:
        update.effective_message.reply_text("لا يمكنني ذلك.")


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def unban(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("لا يمكنني العثور على هذا المستخدم")
            return ""
        else:
            raise

    if user_id == bot.id:
        message.reply_text("كيف يمكنني إلغاء حظر نفسي إذا لم أكن هنا؟")
        return ""

    if is_user_in_chat(chat, user_id):
        message.reply_text("لماذا تحاول إلغاء حظر شخص موجود بالفعل في الدردشة؟")
        return ""

    chat.unban_member(user_id)
    message.reply_text("تم إلغاء الحظر! يمكن لهذا المستخدم الانضمام الآن.")

    log = "<b>{}:</b>" \
          "\n#إلغاء_حظر" \
          "\n<b>المشرف:</b> {}" \
          "\n<b>المستخدم:</b> {}".format(html.escape(chat.title),
                                     mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name))
    if reason:
        log += "\n<b>السبب:</b> {}".format(reason)

    return log


@run_async
@bot_admin
def rban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    if not args:
        message.reply_text("لم تحدد مستخدماً أو دردشة.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("لم تحدد مستخدماً.")
        return
    elif not chat_id:
        message.reply_text("لم تحدد دردشة.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "Chat not found":
            message.reply_text("الدردشة غير موجودة! تأكد من إدخال معرف دردشة صحيح وأنني عضو فيها.")
            return
        else:
            raise

    if chat.type == 'private':
        message.reply_text("هذه دردشة خاصة!")
        return

    if not is_bot_admin(chat, bot.id) or not chat.get_member(bot.id).can_restrict_members:
        message.reply_text("لا يمكنني تقييد الأشخاص هناك! تأكد من أنني مشرف ويمكنني حظر المستخدمين.")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("لا يمكنني العثور على هذا المستخدم")
            return
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("لا يمكنني حظر المشرفين!")
        return

    if user_id == bot.id:
        message.reply_text("لن أحظر نفسي، هل أنت مجنون؟")
        return

    try:
        chat.kick_member(user_id)
        message.reply_text("تم الحظر!")
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            message.reply_text('تم الحظر!', quote=False)
        elif excp.message in RBAN_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("خطأ في حظر المستخدم %s في الدردشة %s (%s) بسبب %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("لا يمكنني حظر هذا المستخدم.")


@run_async
@bot_admin
def runban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    if not args:
        message.reply_text("لم تحدد مستخدماً أو دردشة.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("لم تحدد مستخدماً.")
        return
    elif not chat_id:
        message.reply_text("لم تحدد دردشة.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "Chat not found":
            message.reply_text("الدردشة غير موجودة! تأكد من إدخال معرف دردشة صحيح وأنني عضو فيها.")
            return
        else:
            raise

    if chat.type == 'private':
        message.reply_text("هذه دردشة خاصة!")
        return

    if not is_bot_admin(chat, bot.id) or not chat.get_member(bot.id).can_restrict_members:
        message.reply_text("لا يمكنني إلغاء تقييد الأشخاص هناك! تأكد من أنني مشرف ويمكنني إلغاء حظر المستخدمين.")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("لا يمكنني العثور على هذا المستخدم هناك")
            return
        else:
            raise

    if is_user_in_chat(chat, user_id):
        message.reply_text("لماذا تحاول إلغاء حظر شخص موجود بالفعل في تلك الدردشة؟")
        return

    if user_id == bot.id:
        message.reply_text("لن ألغي حظر نفسي، أنا مشرف هناك!")
        return

    try:
        chat.unban_member(user_id)
        message.reply_text("يمكن لهذا المستخدم الانضمام إلى تلك الدردشة!")
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            message.reply_text('تم إلغاء الحظر!', quote=False)
        elif excp.message in RUNBAN_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("خطأ في إلغاء حظر المستخدم %s في الدردشة %s (%s) بسبب %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("لا يمكنني إلغاء حظر هذا المستخدم.")


# ================== المساعدة ==================
__help__ = """
- /kickme: طرد المستخدم الذي أرسل الأمر

*للمشرفين فقط:*
- /ban <المستخدم>: حظر مستخدم (بالمعرف أو بالرد)
- /tban <المستخدم> x(م/س/ي): حظر مستخدم لمدة محددة. م = دقائق، س = ساعات، ي = أيام.
- /unban <المستخدم>: إلغاء حظر مستخدم (بالمعرف أو بالرد)
- /kick <المستخدم>: طرد مستخدم (بالمعرف أو بالرد)

*الأوامر العربية (بدون /):*
حظر <بالرد>: حظر المستخدم الذي تم الرد عليه
حظر مؤقت <المدة> <بالرد>: حظر المستخدم لمدة محددة
طرد <بالرد>: طرد المستخدم الذي تم الرد عليه
الغاء حظر <بالرد>: إلغاء حظر المستخدم الذي تم الرد عليه
اطردني: طرد نفسك من المجموعة
"""

__mod_name__ = "الحظر"

BAN_HANDLER = CommandHandler("ban", ban, pass_args=True, filters=Filters.group)
TEMPBAN_HANDLER = CommandHandler(["tban", "tempban"], temp_ban, pass_args=True, filters=Filters.group)
KICK_HANDLER = CommandHandler("kick", kick, pass_args=True, filters=Filters.group)
UNBAN_HANDLER = CommandHandler("unban", unban, pass_args=True, filters=Filters.group)
KICKME_HANDLER = DisableAbleCommandHandler("kickme", kickme, filters=Filters.group)
RBAN_HANDLER = CommandHandler("rban", rban, pass_args=True, filters=CustomFilters.sudo_filter)
RUNBAN_HANDLER = CommandHandler("runban", runban, pass_args=True, filters=CustomFilters.sudo_filter)

# معالجات الأوامر العربية (تم إزالة pass_args=True)
BAN_AR_HANDLER = MessageHandler(Filters.regex(r'^حظر$') & Filters.reply, ban)
TEMPBAN_AR_HANDLER = MessageHandler(Filters.regex(r'^حظر مؤقت (.+)$') & Filters.reply, temp_ban)
KICK_AR_HANDLER = MessageHandler(Filters.regex(r'^طرد$') & Filters.reply, kick)
UNBAN_AR_HANDLER = MessageHandler(Filters.regex(r'^الغاء حظر$') & Filters.reply, unban)
KICKME_AR_HANDLER = MessageHandler(Filters.regex(r'^اطردني$'), kickme)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(KICK_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(KICKME_HANDLER)
dispatcher.add_handler(RBAN_HANDLER)
dispatcher.add_handler(RUNBAN_HANDLER)

dispatcher.add_handler(BAN_AR_HANDLER)
dispatcher.add_handler(TEMPBAN_AR_HANDLER)
dispatcher.add_handler(KICK_AR_HANDLER)
dispatcher.add_handler(UNBAN_AR_HANDLER)
dispatcher.add_handler(KICKME_AR_HANDLER)
