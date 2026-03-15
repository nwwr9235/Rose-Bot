import html
from typing import Optional, List

from telegram import Update, Chat, User, Message, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes, CommandHandler, filters
from telegram.helpers import mention_html

from tg_bot import dispatcher, BAN_STICKER, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import (
    bot_admin, user_admin, is_user_ban_protected, can_restrict,
    is_user_admin, is_user_in_chat, is_bot_admin, _TELE_GRAM_ID_S
)
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


@bot_admin
@can_restrict
@user_admin
@loggable
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if user.id not in _TELE_GRAM_ID_S:
        admin_user = await chat.get_member(user.id)
        if not (admin_user.can_restrict_members or admin_user.status == "creator"):
            return ""

    user_id, reason = extract_user_and_text(message, context.args)

    if not user_id:
        await message.reply_text("لم تحدد أي مستخدم للإشارة إليه.")
        return ""

    try:
        member = await chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            await message.reply_text("لا يمكنني العثور على هذا المستخدم")
            return ""
        else:
            raise

    if await is_user_ban_protected(chat, user_id, member):
        await message.reply_text("أتمنى لو كان بإمكاني حظر المشرفين...")
        return ""

    if user_id == context.bot.id:
        await message.reply_text("لن أحظر نفسي، هل أنت مجنون؟")
        return ""

    log = f"<b>{html.escape(chat.title)}:</b>" \
          f"\n#BANNED" \
          f"\n<b>Admin:</b> {mention_html(user.id, user.first_name)}" \
          f"\n<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
    if reason:
        log += f"\n<b>Reason:</b> {reason}"

    try:
        await context.bot.ban_chat_member(chat.id, user_id)
        await context.bot.send_sticker(chat.id, BAN_STICKER)  # ملصق banhammer
        reply = f"{mention_html(member.user.id, member.user.first_name)} تم حظره!"
        await message.reply_text(reply, parse_mode=ParseMode.HTML)
        return log

    except BadRequest as excp:
        if excp.message == "Replied message not found":
            # لا ترد على الرسالة
            reply = f"{mention_html(member.user.id, member.user.first_name)} تم حظره!"
            await context.bot.send_message(chat.id, reply, parse_mode=ParseMode.HTML)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            await message.reply_text("يا للهول، لا أستطيع حظر هذا المستخدم.")

    return ""


@bot_admin
@can_restrict
@user_admin
@loggable
async def temp_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if user.id not in _TELE_GRAM_ID_S:
        admin_user = await chat.get_member(user.id)
        if not (admin_user.can_restrict_members or admin_user.status == "creator"):
            return ""

    user_id, reason = extract_user_and_text(message, context.args)

    if not user_id:
        await message.reply_text("لم تحدد أي مستخدم للإشارة إليه.")
        return ""

    try:
        member = await chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            await message.reply_text("لا يمكنني العثور على هذا المستخدم")
            return ""
        else:
            raise

    if await is_user_ban_protected(chat, user_id, member):
        await message.reply_text("أتمنى لو كان بإمكاني حظر المشرفين...")
        return ""

    if user_id == context.bot.id:
        await message.reply_text("لن أحظر نفسي، هل أنت مجنون؟")
        return ""

    if not reason:
        await message.reply_text("لم تحدد مدة الحظر!")
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

    log = f"<b>{html.escape(chat.title)}:</b>" \
          f"\n#TEMP BANNED" \
          f"\n<b>Admin:</b> {mention_html(user.id, user.first_name)}" \
          f"\n<b>User:</b> {mention_html(member.user.id, member.user.first_name)}" \
          f"\n<b>Time:</b> {time_val}"
    if reason:
        log += f"\n<b>Reason:</b> {reason}"

    try:
        await context.bot.ban_chat_member(chat.id, user_id, until_date=bantime)
        await context.bot.send_sticker(chat.id, BAN_STICKER)
        await message.reply_text(f"تم الحظر! المستخدم محظور لمدة {time_val}.")
        return log

    except BadRequest as excp:
        if excp.message == "Replied message not found":
            await message.reply_text(f"تم الحظر! المستخدم محظور لمدة {time_val}.", quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            await message.reply_text("يا للهول، لا أستطيع حظر هذا المستخدم.")

    return ""


@bot_admin
@can_restrict
@user_admin
@loggable
async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if user.id not in _TELE_GRAM_ID_S:
        admin_user = await chat.get_member(user.id)
        if not (admin_user.can_restrict_members or admin_user.status == "creator"):
            return ""

    user_id, reason = extract_user_and_text(message, context.args)

    if not user_id:
        return ""

    try:
        member = await chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            await message.reply_text("لا يمكنني العثور على هذا المستخدم")
            return ""
        else:
            raise

    if await is_user_ban_protected(chat, user_id):
        await message.reply_text("أتمنى لو كان بإمكاني طرد المشرفين...")
        return ""

    if user_id == context.bot.id:
        await message.reply_text("لن أفعل ذلك")
        return ""

    res = await context.bot.unban_chat_member(chat.id, user_id)  # unban = طرد في هذه الحالة
    if res:
        await context.bot.send_sticker(chat.id, BAN_STICKER)
        await message.reply_text("تم الطرد!")
        log = f"<b>{html.escape(chat.title)}:</b>" \
              f"\n#KICKED" \
              f"\n<b>Admin:</b> {mention_html(user.id, user.first_name)}" \
              f"\n<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
        if reason:
            log += f"\n<b>Reason:</b> {reason}"
        return log
    else:
        await message.reply_text("يا للهول، لا أستطيع طرد هذا المستخدم.")

    return ""


@bot_admin
@can_restrict
async def kickme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_message.from_user.id
    if await is_user_admin(update.effective_chat, user_id):
        await update.effective_message.reply_text("أتمنى لو كان بإمكاني... لكنك مشرف.")
        return

    res = await context.bot.unban_chat_member(update.effective_chat.id, user_id)  # unban = طرد
    if res:
        await update.effective_message.reply_text("تم الطرد.")
    else:
        await update.effective_message.reply_text("هاه؟ لا أستطيع :/")


@bot_admin
@can_restrict
@user_admin
@loggable
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id, reason = extract_user_and_text(message, context.args)

    if not user_id:
        return ""

    try:
        member = await chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            await message.reply_text("لا يمكنني العثور على هذا المستخدم")
            return ""
        else:
            raise

    if user_id == context.bot.id:
        await message.reply_text("كيف سألغي حظر نفسي إذا لم أكن هنا...؟")
        return ""

    if await is_user_in_chat(chat, user_id):
        await message.reply_text("لماذا تحاول إلغاء حظر شخص موجود بالفعل في المجموعة؟")
        return ""

    await context.bot.unban_chat_member(chat.id, user_id)
    await message.reply_text("نعم، يمكن لهذا المستخدم الانضمام!")

    log = f"<b>{html.escape(chat.title)}:</b>" \
          f"\n#UNBANNED" \
          f"\n<b>Admin:</b> {mention_html(user.id, user.first_name)}" \
          f"\n<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
    if reason:
        log += f"\n<b>Reason:</b> {reason}"

    return log


@bot_admin
async def rban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if not context.args:
        await message.reply_text("يبدو أنك لم تحدد مجموعة/مستخدم.")
        return

    user_id, chat_id = extract_user_and_text(message, context.args)

    if not user_id:
        await message.reply_text("يبدو أنك لم تحدد مستخدم.")
        return
    elif not chat_id:
        await message.reply_text("يبدو أنك لم تحدد مجموعة.")
        return

    try:
        chat = await context.bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "Chat not found":
            await message.reply_text("لم يتم العثور على المجموعة! تأكد من إدخال معرف مجموعة صالح وأنني عضو في تلك المجموعة.")
            return
        else:
            raise

    if chat.type == 'private':
        await message.reply_text("آسف، هذه محادثة خاصة!")
        return

    if not await is_bot_admin(chat, context.bot.id) or not (await chat.get_member(context.bot.id)).can_restrict_members:
        await message.reply_text("لا أستطيع تقييد الأعضاء هناك! تأكد من أني مشرف ولدي صلاحية حظر المستخدمين.")
        return

    try:
        member = await chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            await message.reply_text("لا يمكنني العثور على هذا المستخدم")
            return
        else:
            raise

    if await is_user_ban_protected(chat, user_id, member):
        await message.reply_text("أتمنى لو كان بإمكاني حظر المشرفين...")
        return

    if user_id == context.bot.id:
        await message.reply_text("لن أحظر نفسي، هل أنت مجنون؟")
        return

    try:
        await context.bot.ban_chat_member(chat.id, user_id)
        await message.reply_text("تم الحظر!")
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            await message.reply_text('تم الحظر!', quote=False)
        elif excp.message in RBAN_ERRORS:
            await message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            await message.reply_text("يا للهول، لا أستطيع حظر هذا المستخدم.")


@bot_admin
async def runban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if not context.args:
        await message.reply_text("يبدو أنك لم تحدد مجموعة/مستخدم.")
        return

    user_id, chat_id = extract_user_and_text(message, context.args)

    if not user_id:
        await message.reply_text("يبدو أنك لم تحدد مستخدم.")
        return
    elif not chat_id:
        await message.reply_text("يبدو أنك لم تحدد مجموعة.")
        return

    try:
        chat = await context.bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "Chat not found":
            await message.reply_text("لم يتم العثور على المجموعة! تأكد من إدخال معرف مجموعة صالح وأنني عضو في تلك المجموعة.")
            return
        else:
            raise

    if chat.type == 'private':
        await message.reply_text("آسف، هذه محادثة خاصة!")
        return

    if not await is_bot_admin(chat, context.bot.id) or not (await chat.get_member(context.bot.id)).can_restrict_members:
        await message.reply_text("لا أستطيع إلغاء تقييد الأعضاء هناك! تأكد من أني مشرف ولدي صلاحية إلغاء حظر المستخدمين.")
        return

    try:
        member = await chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            await message.reply_text("لا يمكنني العثور على هذا المستخدم هناك")
            return
        else:
            raise

    if await is_user_in_chat(chat, user_id):
        await message.reply_text("لماذا تحاول إلغاء حظر شخص موجود بالفعل في تلك المجموعة؟")
        return

    if user_id == context.bot.id:
        await message.reply_text("لن ألغي حظر نفسي، أنا مشرف هناك!")
        return

    try:
        await context.bot.unban_chat_member(chat.id, user_id)
        await message.reply_text("نعم، يمكن لهذا المستخدم الانضمام إلى تلك المجموعة!")
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            await message.reply_text('تم إلغاء الحظر!', quote=False)
        elif excp.message in RUNBAN_ERRORS:
            await message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR unbanning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            await message.reply_text("يا للهول، لا أستطيع إلغاء حظر هذا المستخدم.")


__help__ = """
- /kickme: يطرد المستخدم الذي أرسل الأمر

*للمشرفين فقط:*
- /ban <المستخدم>: حظر مستخدم (عبر المنشن أو الرد)
- /tban <المستخدم> x(م/س/ي): حظر مستخدم لمدة محددة. م = دقائق، س = ساعات، ي = أيام
- /unban <المستخدم>: إلغاء حظر مستخدم
- /kick <المستخدم>: طرد مستخدم
"""

__mod_name__ = "الحظر"

BAN_HANDLER = CommandHandler("ban", ban, filters=filters.ChatType.GROUPS)
TEMPBAN_HANDLER = CommandHandler(["tban", "tempban"], temp_ban, filters=filters.ChatType.GROUPS)
KICK_HANDLER = CommandHandler("kick", kick, filters=filters.ChatType.GROUPS)
UNBAN_HANDLER = CommandHandler("unban", unban, filters=filters.ChatType.GROUPS)
KICKME_HANDLER = DisableAbleCommandHandler("kickme", kickme, filters=filters.ChatType.GROUPS)
RBAN_HANDLER = CommandHandler("rban", rban, filters=CustomFilters.sudo_filter)
RUNBAN_HANDLER = CommandHandler("runban", runban, filters=CustomFilters.sudo_filter)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(KICK_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(KICKME_HANDLER)
dispatcher.add_handler(RBAN_HANDLER)
dispatcher.add_handler(RUNBAN_HANDLER)
