import html
from io import BytesIO
from typing import Optional, List

from telegram import Update, User, Chat, Message, InlineKeyboardMarkup, ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.helpers import mention_html

import tg_bot.modules.sql.global_bans_sql as sql
from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, STRICT_GBAN
from tg_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import send_to_list
from tg_bot.modules.sql.users_sql import get_all_chats

GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
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
    "Not in the chat",
    "User not found"
}

UNGBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Method is available for supergroup and channel chats only",
    "Not in the chat",
    "Channel_private",
    "Chat_admin_required",
    "Peer_id_invalid",
    "User not found"
}


async def gban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    args = context.args

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        await message.reply_text("يبدو أنك لم تحدد مستخدمًا.")
        return

    if int(user_id) in SUDO_USERS:
        await message.reply_text("أرى بعيني الصغيرة... حرب مشرفين! لماذا تتقاتلون مع بعضكم؟")
        return

    if int(user_id) in SUPPORT_USERS:
        await message.reply_text("شخص ما يحاول حظر عضو دعم! *يحضر الفشار*")
        return

    if user_id == context.bot.id:
        await message.reply_text("لن أحظر نفسي، هل أنت مجنون؟")
        return

    try:
        user_chat = await context.bot.get_chat(user_id)
    except BadRequest as excp:
        await message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        await message.reply_text("هذا ليس مستخدمًا!")
        return

    if sql.is_user_gbanned(user_id):
        if not reason:
            await message.reply_text("هذا المستخدم محظور بالفعل؛ لم تحدد سببًا لتغييره.")
            return

        old_reason = sql.update_gban_reason(user_id, user_chat.username or user_chat.first_name, reason)
        banner = update.effective_user
        await send_to_list(
            context.bot, SUDO_USERS + SUPPORT_USERS,
            f"<b>تعديل الحظر العام</b>"
            f"\n#GBAN"
            f"\n<b>الحالة:</b> <code>تم التعديل</code>"
            f"\n<b>المشرف:</b> {mention_html(banner.id, banner.first_name)}"
            f"\n<b>المستخدم:</b> {mention_html(user_chat.id, user_chat.first_name or 'محذوف')}"
            f"\n<b>المعرف:</b> <code>{user_chat.id}</code>"
            f"\n<b>السبب السابق:</b> {old_reason}"
            f"\n<b>السبب المعدل:</b> {reason}",
            html=True
        )

        if old_reason:
            await message.reply_text(
                f"هذا المستخدم محظور بالفعل، للسبب التالي:\n"
                f"<code>{html.escape(old_reason)}</code>\n"
                f"لقد قمت بتحديثه بالسبب الجديد!",
                parse_mode=ParseMode.HTML
            )
        else:
            await message.reply_text("هذا المستخدم محظور بالفعل، لكن لم يكن لديه سبب. لقد قمت بتحديثه!")

        return

    starting = f"تم بدء الحظر العام للمستخدم:\nالمستخدم: {mention_html(user_chat.id, user_chat.first_name or 'محذوف')}\nالسبب: {reason}"
    await message.reply_text(starting, parse_mode=ParseMode.HTML)

    banner = update.effective_user
    await send_to_list(
        context.bot, SUDO_USERS + SUPPORT_USERS,
        f"<b>حظر عام</b>"
        f"\n#GBAN"
        f"\n<b>الحالة:</b> <code>قيد التنفيذ</code>"
        f"\n<b>المشرف:</b> {mention_html(banner.id, banner.first_name)}"
        f"\n<b>المستخدم:</b> {mention_html(user_chat.id, user_chat.first_name or 'محذوف')}"
        f"\n<b>المعرف:</b> <code>{user_chat.id}</code>"
        f"\n<b>السبب:</b> {reason or 'بدون سبب'}",
        html=True
    )

    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        if not sql.does_chat_gban(chat_id):
            continue

        try:
            await context.bot.ban_chat_member(chat_id, user_id)
        except BadRequest as excp:
            if excp.message in GBAN_ERRORS:
                pass
            else:
                await message.reply_text(f"تعذر الحظر بسبب: {excp.message}")
                await send_to_list(context.bot, SUDO_USERS + SUPPORT_USERS, f"تعذر الحظر بسبب: {excp.message}")
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass

    await send_to_list(
        context.bot, SUDO_USERS + SUPPORT_USERS,
        f"تم حظر {mention_html(user_chat.id, user_chat.first_name or 'محذوف')} بنجاح!",
        html=True
    )

    gban_complete = f"تم حظر {mention_html(user_chat.id, user_chat.first_name or 'محذوف')} بنجاح :)\nالسبب: {reason}"
    await message.reply_text(gban_complete, parse_mode=ParseMode.HTML)


async def ungban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    args = context.args

    user_id = extract_user(message, args)
    if not user_id:
        await message.reply_text("يبدو أنك لم تحدد مستخدمًا.")
        return

    user_chat = await context.bot.get_chat(user_id)
    if user_chat.type != 'private':
        await message.reply_text("هذا ليس مستخدمًا!")
        return

    if not sql.is_user_gbanned(user_id):
        await message.reply_text("هذا المستخدم غير محظور!")
        return

    banner = update.effective_user

    await message.reply_text(f"سأعطي {user_chat.first_name} فرصة ثانية، على مستوى العالم.")

    await send_to_list(
        context.bot, SUDO_USERS + SUPPORT_USERS,
        f"<b>إلغاء الحظر العام</b>"
        f"\n#UNGBAN"
        f"\n<b>الحالة:</b> <code>تم الإلغاء</code>"
        f"\n<b>المشرف:</b> {mention_html(banner.id, banner.first_name)}"
        f"\n<b>المستخدم:</b> {mention_html(user_chat.id, user_chat.first_name or 'محذوف')}"
        f"\n<b>المعرف:</b> <code>{user_chat.id}</code>",
        html=True
    )

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status == 'kicked':
                await context.bot.unban_chat_member(chat_id, user_id)
        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                await message.reply_text(f"تعذر إلغاء الحظر بسبب: {excp.message}")
                await context.bot.send_message(OWNER_ID, f"تعذر إلغاء الحظر بسبب: {excp.message}")
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)

    await send_to_list(context.bot, SUDO_USERS + SUPPORT_USERS, "تم إلغاء الحظر العام بنجاح!")

    await message.reply_text("تم إلغاء الحظر عن الشخص.")


async def gbanlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    banned_users = sql.get_gban_list()

    if not banned_users:
        await update.effective_message.reply_text("لا يوجد مستخدمون محظورون عمومًا! أنت ألطف مما توقعت...")
        return

    banfile = 'هؤلاء الأشخاص محظورون:\n'
    for user in banned_users:
        banfile += f"[x] {user['name']} - {user['user_id']}\n"
        if user['reason']:
            banfile += f"السبب: {user['reason']}\n"

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        await update.effective_message.reply_document(
            document=output,
            filename="gbanlist.txt",
            caption="هذه قائمة المستخدمين المحظورين عمومًا حاليًا."
        )


async def check_and_ban(update: Update, user_id: int, should_message: bool = True):
    chat = update.effective_chat
    if sql.is_user_gbanned(user_id):
        await context.bot.ban_chat_member(chat.id, user_id)
        if should_message:
            await update.effective_message.reply_text("هذا شخص سيئ، لا يجب أن يكون هنا!")


async def enforce_gban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # لا نستخدم @restrict handler لتجنب الإزعاج - فقط تجاهل إذا لم نتمكن من الحظر
    chat = update.effective_chat
    bot_member = await chat.get_member(context.bot.id)
    if sql.does_chat_gban(chat.id) and bot_member.can_restrict_members:
        user = update.effective_user
        msg = update.effective_message

        if user and not await is_user_admin(chat, user.id):
            await check_and_ban(update, user.id, should_message=False)

        if msg.new_chat_members:
            new_members = msg.new_chat_members
            for mem in new_members:
                await check_and_ban(update, mem.id, should_message=False)

        if msg.reply_to_message:
            user = msg.reply_to_message.from_user
            if user and not await is_user_admin(chat, user.id):
                await check_and_ban(update, user.id, should_message=False)


@user_admin
async def gbanstat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gbans(update.effective_chat.id)
            await update.effective_message.reply_text(
                "لقد فعّلت الحظر العام في هذه المجموعة. سيساعد هذا في حمايتك من المرسلين العشوائيين والشخصيات غير المرغوب فيها."
            )
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            await update.effective_message.reply_text(
                "لقد عطّلت الحظر العام في هذه المجموعة. لن يؤثر الحظر العام على مستخدميك بعد الآن. لكنك ستكون أقل حماية من المتصيدين والمرسلين العشوائيين."
            )
    else:
        await update.effective_message.reply_text(
            f"أعطني بعض الوسائط لاختيار الإعداد! on/off, yes/no!\n\n"
            f"الإعداد الحالي: {sql.does_chat_gban(update.effective_chat.id)}\n"
            f"عند True، أي حظر عام يحدث سيحدث أيضًا في مجموعتك. "
            f"عند False، لن يحدث، مما يجعلك عرضة للمرسلين العشوائيين."
        )


def __stats__():
    return f"{sql.num_gbanned_users()} مستخدم محظور عمومًا."


def __user_info__(user_id: int) -> str:
    is_gbanned = sql.is_user_gbanned(user_id)
    text = "محظور عمومًا: <b>{}</b>"
    if is_gbanned:
        text = text.format("نعم")
        user = sql.get_gbanned_user(user_id)
        if user and user.reason:
            text += f"\nالسبب: {html.escape(user.reason)}"
    else:
        text = text.format("لا")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


async def __chat_settings__(chat_id: int, user_id: int) -> str:
    return f"هذه المجموعة تفرض *الحظر العام*: `{sql.does_chat_gban(chat_id)}`."


__help__ = """
*للمشرفين فقط:*
- /gbanstat <on/off/yes/no>: تعطيل تأثير الحظر العام على مجموعتك، أو عرض الإعدادات الحالية.

الحظر العام هو أداة يستخدمها مالكو البوت لحظر المرسلين العشوائيين عبر جميع المجموعات. يساعد في حمايتك ومجموعاتك عن طريق إزالة مزعجي الإرسال بسرعة. يمكن تعطيله لمجموعتك باستخدام /gbanstat.
"""

__mod_name__ = "الحظر العام"

GBAN_HANDLER = CommandHandler("gban", gban, filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
UNGBAN_HANDLER = CommandHandler("ungban", ungban, filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GBAN_LIST_HANDLER = CommandHandler("gbanlist", gbanlist, filters=CustomFilters.sudo_filter | CustomFilters.support_filter)

GBAN_STATUS_HANDLER = CommandHandler("gbanstat", gbanstat, filters=filters.ChatType.GROUPS)

GBAN_ENFORCER_HANDLER = MessageHandler(filters.ALL & filters.ChatType.GROUPS, enforce_gban)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST_HANDLER)
dispatcher.add_handler(GBAN_STATUS_HANDLER)

if STRICT_GBAN:
    dispatcher.add_handler(GBAN_ENFORCER_HANDLER, GBAN_ENFORCE_GROUP)
