import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, RegexHandler, MessageHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown, mention_html

from tg_bot import dispatcher
import tg_bot.modules.sql.setlink_sql as sql
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import bot_admin, can_promote, user_admin, can_pin, is_owner
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.helper_funcs.string_handling import markdown_parser
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import ranks_sql
from tg_bot.modules.helper_funcs.chat_status import can_promote_to, can_demote

# ==================== الدوال الأصلية (promote, demote, pin, unpin, invite, link, adminlist) ====================

@run_async
@bot_admin
@can_promote
@user_admin
@loggable
def promote(bot: Bot, update: Update, args: List[str]) -> str:
    chat_id = update.effective_chat.id
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == 'administrator' or user_member.status == 'creator':
        message.reply_text("How am I meant to promote someone that's already an admin?")
        return ""

    if user_id == bot.id:
        message.reply_text("I can't promote myself! Get an admin to do it for me.")
        return ""

    # set same perms as bot - bot can't assign higher perms than itself!
    bot_member = chat.get_member(bot.id)

    bot.promoteChatMember(chat_id, user_id,
                          can_change_info=bot_member.can_change_info,
                          can_post_messages=bot_member.can_post_messages,
                          can_edit_messages=bot_member.can_edit_messages,
                          can_delete_messages=bot_member.can_delete_messages,
                          # can_invite_users=bot_member.can_invite_users,
                          can_restrict_members=bot_member.can_restrict_members,
                          can_pin_messages=bot_member.can_pin_messages,
                          can_promote_members=bot_member.can_promote_members)

    message.reply_text("Successfully promoted!")
    return "<b>{}:</b>" \
           "\n#PROMOTED" \
           "\n<b>Admin:</b> {}" \
           "\n<b>User:</b> {}".format(html.escape(chat.title),
                                      mention_html(user.id, user.first_name),
                                      mention_html(user_member.user.id, user_member.user.first_name))


@run_async
@bot_admin
@can_promote
@user_admin
@loggable
def demote(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("You don't seem to be referring to a user.")
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == 'creator':
        message.reply_text("This person CREATED the chat, how would I demote them?")
        return ""

    if not user_member.status == 'administrator':
        message.reply_text("Can't demote what wasn't promoted!")
        return ""

    if user_id == bot.id:
        message.reply_text("I can't demote myself! Get an admin to do it for me.")
        return ""

    try:
        bot.promoteChatMember(int(chat.id), int(user_id),
                              can_change_info=False,
                              can_post_messages=False,
                              can_edit_messages=False,
                              can_delete_messages=False,
                              can_invite_users=False,
                              can_restrict_members=False,
                              can_pin_messages=False,
                              can_promote_members=False)
        message.reply_text("Successfully demoted!")
        return "<b>{}:</b>" \
               "\n#DEMOTED" \
               "\n<b>Admin:</b> {}" \
               "\n<b>User:</b> {}".format(html.escape(chat.title),
                                          mention_html(user.id, user.first_name),
                                          mention_html(user_member.user.id, user_member.user.first_name))

    except BadRequest:
        message.reply_text("Could not demote. I might not be admin, or the admin status was appointed by another "
                           "user, so I can't act upon them!")
        return ""


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def pin(bot: Bot, update: Update, args: List[str]) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]

    is_group = chat.type != "private" and chat.type != "channel"

    prev_message = update.effective_message.reply_to_message

    is_silent = True
    if len(args) >= 1:
        is_silent = not (args[0].lower() == 'notify' or args[0].lower() == 'loud' or args[0].lower() == 'violent')

    if prev_message and is_group:
        try:
            bot.pinChatMessage(chat.id, prev_message.message_id, disable_notification=is_silent)
        except BadRequest as excp:
            if excp.message == "Chat_not_modified":
                pass
            else:
                raise
        return "<b>{}:</b>" \
               "\n#PINNED" \
               "\n<b>Admin:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name))

    return ""


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def unpin(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user  # type: Optional[User]

    try:
        bot.unpinChatMessage(chat.id)
    except BadRequest as excp:
        if excp.message == "Chat_not_modified":
            pass
        else:
            raise

    return "<b>{}:</b>" \
           "\n#UNPINNED" \
           "\n<b>Admin:</b> {}".format(html.escape(chat.title),
                                       mention_html(user.id, user.first_name))

@run_async
@bot_admin
@user_admin
def invite(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message #type: Optional[Messages]
    
    if chat.username:
        update.effective_message.reply_text("@{}".format(chat.username))
    elif chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
        bot_member = chat.get_member(bot.id)
        if bot_member.can_invite_users:
            invitelink = bot.exportChatInviteLink(chat.id)
            linktext = "Successfully generated new link for *{}:*".format(chat.title)
            link = "`{}`".format(invitelink)
            message.reply_text(linktext, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
            message.reply_text(link, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        else:
            message.reply_text("I don't have access to the invite link, try changing my permissions!")
    else:
        message.reply_text("I can only give you invite links for supergroups and channels, sorry!")

@run_async
def link_public(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message #type: Optional[Messages]
    chat_id = update.effective_chat.id
    invitelink = sql.get_link(chat_id)
    
    if chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
        if invitelink:
            message.reply_text("Link of *{}*:\n`{}`".format(chat.title, invitelink), parse_mode=ParseMode.MARKDOWN)
        else:
            message.reply_text("The admins of *{}* haven't set link."
                               " \nLink can be set by following: `/setlink` and get link of chat "
                               "using /invitelink, paste the link after `/setlink` append.".format(chat.title), parse_mode=ParseMode.MARKDOWN)
    else:
        message.reply_text("I can only can save links for supergroups and channels, sorry!")

@run_async
@user_admin
def set_link(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    raw_text = msg.text
    args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
    
    if len(args) == 2:
        links_text = args[1]

        sql.set_link(chat_id, links_text)
        msg.reply_text("The link has been set for {}!\nRetrieve link by #link".format((chat.title)))


@run_async
@user_admin
def clear_link(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    sql.set_link(chat_id, "")
    update.effective_message.reply_text("Successfully cleared link!")


@run_async
def adminlist(bot: Bot, update: Update):
    administrators = update.effective_chat.get_administrators()
    text = "Admins in *{}*:".format(update.effective_chat.title or "this chat")
    for admin in administrators:
        user = admin.user
        name = "[{}](tg://user?id={})".format(user.first_name + (user.last_name or ""), user.id)
        if user.username:
            name = escape_markdown("@" + user.username)
        text += "\n - {}".format(name)

    update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

def __stats__():
    return "{} chats have links set.".format(sql.num_chats())

def __chat_settings__(chat_id, user_id):
    return "You are *admin*: `{}`".format(
        dispatcher.bot.get_chat_member(chat_id, user_id).status in ("administrator", "creator"))


# ==================== الدوال العربية الجديدة للرتب ====================

@run_async
def arabic_promote(bot: Bot, update: Update):
    """معالج رفع: رفع @user رتبة"""
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    text = msg.text.strip()
    parts = text.split()
    if len(parts) < 3:
        msg.reply_text("استخدم: رفع @username الرتبة\nالرتب: مالك اساسي, مالك, منشئ, مدير, اداري, مميز")
        return

    username = parts[1]
    rank_ar = parts[2]
    # تحويل الرتبة العربية إلى إنجليزية
    rank_map = {
        'مالك اساسي': 'ownerplus',
        'مالك': 'owner',
        'منشئ': 'creator',
        'مدير': 'manager',
        'اداري': 'admin',
        'مميز': 'vip'
    }
    new_rank = rank_map.get(rank_ar)
    if not new_rank:
        msg.reply_text("رتبة غير معروفة. الرتب: مالك اساسي, مالك, منشئ, مدير, اداري, مميز")
        return

    # استخراج user_id من username
    target_user_id = extract_user(msg, [username])
    if not target_user_id:
        msg.reply_text("لم أتمكن من العثور على المستخدم.")
        return

    # التحقق من الصلاحية
    if not can_promote_to(chat.id, user.id, target_user_id, new_rank):
        msg.reply_text("ليس لديك صلاحية لرفع هذا المستخدم إلى هذه الرتبة.")
        return

    # تعيين الرتبة
    ranks_sql.set_rank(chat.id, target_user_id, new_rank)
    target_name = bot.get_chat(target_user_id).first_name
    msg.reply_text(f"تم رفع {target_name} إلى رتبة {rank_ar}.")


@run_async
def arabic_demote(bot: Bot, update: Update):
    """معالج تنزيل: تنزيل @user"""
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    text = msg.text.strip()
    parts = text.split()
    if len(parts) < 2:
        msg.reply_text("استخدم: تنزيل @username")
        return

    username = parts[1]
    target_user_id = extract_user(msg, [username])
    if not target_user_id:
        msg.reply_text("لم أتمكن من العثور على المستخدم.")
        return

    if not can_demote(chat.id, user.id, target_user_id):
        msg.reply_text("ليس لديك صلاحية لتنزيل هذا المستخدم.")
        return

    ranks_sql.remove_rank(chat.id, target_user_id)
    target_name = bot.get_chat(target_user_id).first_name
    msg.reply_text(f"تم تنزيل {target_name} (حذف الرتبة).")


@run_async
def arabic_show_rank(bot: Bot, update: Update):
    """عرض رتبة المستخدم: رتبتي أو رتبة @user"""
    msg = update.effective_message
    chat = update.effective_chat
    text = msg.text.strip()
    parts = text.split()
    if len(parts) >= 2 and parts[1].startswith('@'):
        username = parts[1]
        target_user_id = extract_user(msg, [username])
    else:
        target_user_id = msg.from_user.id

    if not target_user_id:
        msg.reply_text("لم أتمكن من العثور على المستخدم.")
        return

    rank = ranks_sql.get_rank(chat.id, target_user_id)
    target_name = bot.get_chat(target_user_id).first_name
    rank_map_rev = {
        'ownerplus': 'مالك اساسي',
        'owner': 'مالك',
        'creator': 'منشئ',
        'manager': 'مدير',
        'admin': 'اداري',
        'vip': 'مميز'
    }
    rank_ar = rank_map_rev.get(rank, 'بدون رتبة')
    msg.reply_text(f"رتبة {target_name}: {rank_ar}")


# ==================== تعريفات المعالجات (Handlers) ====================

PIN_HANDLER = CommandHandler("pin", pin, pass_args=True, filters=Filters.group)
UNPIN_HANDLER = CommandHandler("unpin", unpin, filters=Filters.group)
LINK_HANDLER = DisableAbleCommandHandler("link", link_public)
SET_LINK_HANDLER = CommandHandler("setlink", set_link, filters=Filters.group)
RESET_LINK_HANDLER = CommandHandler("clearlink", clear_link, filters=Filters.group)
HASH_LINK_HANDLER = RegexHandler("#link", link_public)
INVITE_HANDLER = CommandHandler("invitelink", invite, filters=Filters.group)
PROMOTE_HANDLER = CommandHandler("promote", promote, pass_args=True, filters=Filters.group)
DEMOTE_HANDLER = CommandHandler("demote", demote, pass_args=True, filters=Filters.group)
ADMINLIST_HANDLER = DisableAbleCommandHandler(["adminlist", "staff"], adminlist, filters=Filters.group)

# معالجات الأوامر العربية
ARABIC_PROMOTE_HANDLER = MessageHandler(
    Filters.regex(r'^\s*رفع\s+@\w+\s+(مالك اساسي|مالك|منشئ|مدير|اداري|مميز)\s*$'),
    arabic_promote,
    filters=Filters.group
)
ARABIC_DEMOTE_HANDLER = MessageHandler(
    Filters.regex(r'^\s*تنزيل\s+@\w+\s*$'),
    arabic_demote,
    filters=Filters.group
)
ARABIC_SHOW_RANK_HANDLER = MessageHandler(
    Filters.regex(r'^\s*(رتبتي|رتبة\s+@\w+)\s*$'),
    arabic_show_rank,
    filters=Filters.group
)

dispatcher.add_handler(PIN_HANDLER)
dispatcher.add_handler(UNPIN_HANDLER)
dispatcher.add_handler(INVITE_HANDLER)
dispatcher.add_handler(LINK_HANDLER)
dispatcher.add_handler(SET_LINK_HANDLER)
dispatcher.add_handler(RESET_LINK_HANDLER)
dispatcher.add_handler(HASH_LINK_HANDLER)
dispatcher.add_handler(PROMOTE_HANDLER)
dispatcher.add_handler(DEMOTE_HANDLER)
dispatcher.add_handler(ADMINLIST_HANDLER)

# تسجيل المعالجات العربية الجديدة
dispatcher.add_handler(ARABIC_PROMOTE_HANDLER)
dispatcher.add_handler(ARABIC_DEMOTE_HANDLER)
dispatcher.add_handler(ARABIC_SHOW_RANK_HANDLER)

__help__ = """
Lazy to promote or demote someone for admins? Want to see basic information about chat? \
All stuff about chatroom such as admin lists, pinning or grabbing an invite link can be \
done easily using the bot.

 - /adminlist: list of admins and members in the chat
 - /staff: same as /adminlist
 - /link: get the group link for this chat.
 - #link: same as /link

*Admin only:*
 - /pin: silently pins the message replied to - add 'loud' or 'notify' to give notifies to users.
 - /unpin: unpins the currently pinned message.
 - /invitelink: generates new invite link.
 - /setlink <your group link here>: set the group link for this chat.
 - /clearlink: clear the group link for this chat.
 - /promote: promotes the user replied to
 - /demote: demotes the user replied to
 
 An example of set a link:
`/setlink https://t.me/joinchat/HwiIk1RADK5gRMr9FBdOrwtae`

An example of promoting someone to admins:
`/promote @username`; this promotes a user to admins.
"""

__mod_name__ = "Admin"
