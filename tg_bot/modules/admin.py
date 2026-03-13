import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, MessageHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown, mention_html

from tg_bot import dispatcher
import tg_bot.modules.sql.setlink_sql as sql
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import bot_admin, can_promote, user_admin, can_pin
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.helper_funcs.string_handling import markdown_parser
from tg_bot.modules.log_channel import loggable


@run_async
@bot_admin
@can_promote
@user_admin
@loggable
def promote(bot: Bot, update: Update, args: List[str]) -> str:
    chat_id = update.effective_chat.id
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("لم أتمكن من العثور على هذا المستخدم.")
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == 'administrator' or user_member.status == 'creator':
        message.reply_text("كيف يمكنني رفع شخص هو بالفعل مشرف؟")
        return ""

    if user_id == bot.id:
        message.reply_text("لا يمكنني رفع نفسي! اجعل أحد المشرفين يفعل ذلك.")
        return ""

    bot_member = chat.get_member(bot.id)

    bot.promoteChatMember(chat_id, user_id,
                          can_change_info=bot_member.can_change_info,
                          can_post_messages=bot_member.can_post_messages,
                          can_edit_messages=bot_member.can_edit_messages,
                          can_delete_messages=bot_member.can_delete_messages,
                          can_restrict_members=bot_member.can_restrict_members,
                          can_pin_messages=bot_member.can_pin_messages,
                          can_promote_members=bot_member.can_promote_members)

    message.reply_text("تم الرفع بنجاح!")
    return "<b>{}:</b>" \
           "\n#رفع" \
           "\n<b>المشرف:</b> {}" \
           "\n<b>المستخدم:</b> {}".format(html.escape(chat.title),
                                      mention_html(user.id, user.first_name),
                                      mention_html(user_member.user.id, user_member.user.first_name))


@run_async
@bot_admin
@can_promote
@user_admin
@loggable
def demote(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("لم أتمكن من العثور على هذا المستخدم.")
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == 'creator':
        message.reply_text("هذا الشخص هو منشئ المجموعة، كيف يمكنني تنزيله؟")
        return ""

    if not user_member.status == 'administrator':
        message.reply_text("لا يمكن تنزيل شخص لم يتم رفعه!")
        return ""

    if user_id == bot.id:
        message.reply_text("لا يمكنني تنزيل نفسي! اجعل أحد المشرفين يفعل ذلك.")
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
        message.reply_text("تم التنزيل بنجاح!")
        return "<b>{}:</b>" \
               "\n#تنزيل" \
               "\n<b>المشرف:</b> {}" \
               "\n<b>المستخدم:</b> {}".format(html.escape(chat.title),
                                          mention_html(user.id, user.first_name),
                                          mention_html(user_member.user.id, user_member.user.first_name))

    except BadRequest:
        message.reply_text("تعذر التنزيل. قد لا أكون مشرفاً، أو أن رتبة المشرف تم تعيينها من قبل مستخدم آخر.")
        return ""


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def pin(bot: Bot, update: Update, args: List[str]) -> str:
    user = update.effective_user
    chat = update.effective_chat

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
               "\n#تثبيت" \
               "\n<b>المشرف:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name))

    return ""


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def unpin(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user

    try:
        bot.unpinChatMessage(chat.id)
    except BadRequest as excp:
        if excp.message == "Chat_not_modified":
            pass
        else:
            raise

    return "<b>{}:</b>" \
           "\n#إلغاء_تثبيت" \
           "\n<b>المشرف:</b> {}".format(html.escape(chat.title),
                                       mention_html(user.id, user.first_name))


@run_async
@bot_admin
@user_admin
def invite(bot: Bot, update: Update):
    chat = update.effective_chat
    message = update.effective_message

    if chat.username:
        update.effective_message.reply_text("@{}".format(chat.username))
    elif chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
        bot_member = chat.get_member(bot.id)
        if bot_member.can_invite_users:
            invitelink = bot.exportChatInviteLink(chat.id)
            linktext = "تم إنشاء رابط جديد لـ *{}*:".format(chat.title)
            link = "`{}`".format(invitelink)
            message.reply_text(linktext, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
            message.reply_text(link, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        else:
            message.reply_text("ليس لدي صلاحية الوصول إلى رابط الدعوة، حاول تغيير صلاحياتي!")
    else:
        message.reply_text("يمكنني فقط إعطاء روابط الدعوة للمجموعات الخارقة والقنوات، آسف!")


@run_async
def link_public(bot: Bot, update: Update):
    chat = update.effective_chat
    message = update.effective_message
    chat_id = update.effective_chat.id
    invitelink = sql.get_link(chat_id)

    if chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
        if invitelink:
            message.reply_text("رابط *{}*:\n`{}`".format(chat.title, invitelink), parse_mode=ParseMode.MARKDOWN)
        else:
            message.reply_text("مشرفو *{}* لم يحددوا رابطاً بعد."
                               " \nيمكن تعيين الرابط باستخدام `/setlink` ثم لصق الرابط بعد الأمر.".format(chat.title), parse_mode=ParseMode.MARKDOWN)
    else:
        message.reply_text("يمكنني فقط حفظ روابط للمجموعات الخارقة والقنوات، آسف!")


@run_async
@user_admin
def set_link(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    msg = update.effective_message
    chat = update.effective_chat
    raw_text = msg.text
    args = raw_text.split(None, 1)

    if len(args) == 2:
        links_text = args[1]

        sql.set_link(chat_id, links_text)
        msg.reply_text("تم تعيين الرابط لـ {}!\nاسترجع الرابط باستخدام #رابط".format(chat.title))


@run_async
@user_admin
def clear_link(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    sql.set_link(chat_id, "")
    update.effective_message.reply_text("تم مسح الرابط بنجاح!")


@run_async
def adminlist(bot: Bot, update: Update):
    administrators = update.effective_chat.get_administrators()
    text = "المشرفون في *{}*:".format(update.effective_chat.title or "هذه الدردشة")
    for admin in administrators:
        user = admin.user
        name = "[{}](tg://user?id={})".format(user.first_name + (user.last_name or ""), user.id)
        if user.username:
            name = escape_markdown("@" + user.username)
        text += "\n - {}".format(name)

    update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def __stats__():
    return "{} دردشة لديها رابط محفوظ.".format(sql.num_chats())


def __chat_settings__(chat_id, user_id):
    return "أنت *مشرف*: `{}`".format(
        dispatcher.bot.get_chat_member(chat_id, user_id).status in ("administrator", "creator"))


# ================== المساعدة ==================
__help__ = """
هل أنت كسول لرفع أو تنزيل شخص للمشرفين؟ هل تريد رؤية معلومات أساسية عن الدردشة؟
كل ما يتعلق بالدردشة مثل قوائم المشرفين أو التثبيت أو الحصول على رابط الدعوة يمكن القيام به بسهولة باستخدام البوت.

- /adminlist: قائمة المشرفين في الدردشة
- /staff: نفس /adminlist
- /link: الحصول على رابط المجموعة لهذه الدردشة.
- #link: نفس /link

*للمشرفين فقط:*
- /pin: تثبيت الرسالة التي تم الرد عليها بصمت - أضف 'loud' أو 'notify' لإعلام المستخدمين.
- /unpin: إلغاء تثبيت الرسالة المثبتة حالياً.
- /invitelink: إنشاء رابط دعوة جديد.
- /setlink <رابط المجموعة هنا>: تعيين رابط المجموعة لهذه الدردشة.
- /clearlink: مسح رابط المجموعة لهذه الدردشة.
- /promote: رفع المستخدم الذي تم الرد عليه
- /demote: تنزيل المستخدم الذي تم الرد عليه

*الأوامر العربية (بدون /):*
رفع مشرف <بالرد>: رفع عضو إلى مشرف
تنزيل مشرف <بالرد>: تنزيل عضو من المشرفين
تثبيت: تثبيت الرسالة التي تم الرد عليها
الغاء تثبيت: إلغاء تثبيت الرسالة المثبتة
رابط: الحصول على رابط المجموعة
مشرفين: قائمة المشرفين
دعوة: إنشاء رابط دعوة جديد
تعيين رابط <الرابط>: تعيين رابط المجموعة
مسح رابط: مسح رابط المجموعة
"""

__mod_name__ = "المشرفون"

PIN_HANDLER = CommandHandler("pin", pin, pass_args=True, filters=Filters.group)
UNPIN_HANDLER = CommandHandler("unpin", unpin, filters=Filters.group)
LINK_HANDLER = DisableAbleCommandHandler("link", link_public)
SET_LINK_HANDLER = CommandHandler("setlink", set_link, filters=Filters.group)
RESET_LINK_HANDLER = CommandHandler("clearlink", clear_link, filters=Filters.group)
HASH_LINK_HANDLER = MessageHandler(Filters.regex(r'^#رابط$'), link_public)
INVITE_HANDLER = CommandHandler("invitelink", invite, filters=Filters.group)
PROMOTE_HANDLER = CommandHandler("promote", promote, pass_args=True, filters=Filters.group)
DEMOTE_HANDLER = CommandHandler("demote", demote, pass_args=True, filters=Filters.group)
ADMINLIST_HANDLER = DisableAbleCommandHandler(["adminlist", "staff"], adminlist, filters=Filters.group)

# معالجات الأوامر العربية
PROMOTE_AR_HANDLER = MessageHandler(Filters.regex(r'^رفع مشرف$') & Filters.reply, promote, pass_args=True)
DEMOTE_AR_HANDLER = MessageHandler(Filters.regex(r'^تنزيل مشرف$') & Filters.reply, demote, pass_args=True)
PIN_AR_HANDLER = MessageHandler(Filters.regex(r'^تثبيت$') & Filters.reply, pin, pass_args=True)
UNPIN_AR_HANDLER = MessageHandler(Filters.regex(r'^الغاء تثبيت$'), unpin)
LINK_AR_HANDLER = MessageHandler(Filters.regex(r'^رابط$'), link_public)
ADMINLIST_AR_HANDLER = MessageHandler(Filters.regex(r'^مشرفين$'), adminlist)
INVITE_AR_HANDLER = MessageHandler(Filters.regex(r'^دعوة$'), invite)
SETLINK_AR_HANDLER = MessageHandler(Filters.regex(r'^تعيين رابط (.+)$'), set_link)
CLEARLINK_AR_HANDLER = MessageHandler(Filters.regex(r'^مسح رابط$'), clear_link)

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

dispatcher.add_handler(PROMOTE_AR_HANDLER)
dispatcher.add_handler(DEMOTE_AR_HANDLER)
dispatcher.add_handler(PIN_AR_HANDLER)
dispatcher.add_handler(UNPIN_AR_HANDLER)
dispatcher.add_handler(LINK_AR_HANDLER)
dispatcher.add_handler(ADMINLIST_AR_HANDLER)
dispatcher.add_handler(INVITE_AR_HANDLER)
dispatcher.add_handler(SETLINK_AR_HANDLER)
dispatcher.add_handler(CLEARLINK_AR_HANDLER)
