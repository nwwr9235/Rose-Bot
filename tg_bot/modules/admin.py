import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, RegexHandler, MessageHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown, mention_html

from tg_bot import dispatcher
import tg_bot.modules.sql.setlink_sql as sql
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import bot_admin, can_promote, user_admin, can_pin
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.helper_funcs.string_handling import markdown_parser
from tg_bot.modules.log_channel import loggable

# ------------------- دوال مساعدة للأوامر العربية -------------------
def extract_args_from_text(text: str, keyword: str) -> List[str]:
    """استخراج المعاملات بعد الكلمة المفتاحية"""
    if text.startswith(keyword):
        rest = text[len(keyword):].strip()
        return rest.split() if rest else []
    return []

# =================== الأوامر العربية الجديدة ===================

# رفع مشرف
@run_async
@bot_admin
@can_promote
@user_admin
@loggable
def promote_arabic(bot: Bot, update: Update) -> str:
    message = update.effective_message
    text = message.text
    args = extract_args_from_text(text, "رفع")
    # استدعاء الدالة الأصلية مع args
    return promote(bot, update, args)

# تنزيل مشرف
@run_async
@bot_admin
@can_promote
@user_admin
@loggable
def demote_arabic(bot: Bot, update: Update) -> str:
    message = update.effective_message
    text = message.text
    args = extract_args_from_text(text, "تنزيل")
    return demote(bot, update, args)

# تثبيت رسالة
@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def pin_arabic(bot: Bot, update: Update) -> str:
    message = update.effective_message
    text = message.text
    args = extract_args_from_text(text, "تثبيت")
    return pin(bot, update, args)

# فك التثبيت
@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def unpin_arabic(bot: Bot, update: Update) -> str:
    return unpin(bot, update)

# دعوة (إنشاء رابط دعوة)
@run_async
@bot_admin
@user_admin
def invite_arabic(bot: Bot, update: Update):
    message = update.effective_message
    text = message.text
    args = extract_args_from_text(text, "دعوة")
    return invite(bot, update)

# رابط عام (عرض الرابط المحفوظ)
@run_async
def link_public_arabic(bot: Bot, update: Update):
    message = update.effective_message
    text = message.text
    args = extract_args_from_text(text, "رابط عام")
    return link_public(bot, update)

# تعيين رابط
@run_async
@user_admin
def set_link_arabic(bot: Bot, update: Update):
    message = update.effective_message
    text = message.text
    args = extract_args_from_text(text, "تعيين الرابط")
    return set_link(bot, update)

# مسح الرابط
@run_async
@user_admin
def clear_link_arabic(bot: Bot, update: Update):
    message = update.effective_message
    text = message.text
    args = extract_args_from_text(text, "مسح الرابط")
    return clear_link(bot, update)

# قائمة الإشراف (عرض المشرفين)
@run_async
def adminlist_arabic(bot: Bot, update: Update):
    message = update.effective_message
    text = message.text
    args = extract_args_from_text(text, "قائمة الإشراف")
    return adminlist(bot, update)

# =================== الدوال الأصلية (معدلة الرسائل) ===================

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
        message.reply_text("لم تحدد أي مستخدم للإشارة إليه.")
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == 'administrator' or user_member.status == 'creator':
        message.reply_text("كيف يمكنني رفع شخص هو بالفعل مشرف؟")
        return ""

    if user_id == bot.id:
        message.reply_text("لا أستطيع رفع نفسي! اطلب من أحد المشرفين فعل ذلك.")
        return ""

    # تعيين نفس صلاحيات البوت - لا يمكن للبوت منح صلاحيات أعلى من صلاحياته
    bot_member = chat.get_member(bot.id)

    bot.promoteChatMember(chat_id, user_id,
                          can_change_info=bot_member.can_change_info,
                          can_post_messages=bot_member.can_post_messages,
                          can_edit_messages=bot_member.can_edit_messages,
                          can_delete_messages=bot_member.can_delete_messages,
                          can_restrict_members=bot_member.can_restrict_members,
                          can_pin_messages=bot_member.can_pin_messages,
                          can_promote_members=bot_member.can_promote_members)

    message.reply_text("تم الترقية بنجاح!")
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
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("لم تحدد أي مستخدم للإشارة إليه.")
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == 'creator':
        message.reply_text("هذا الشخص هو منشئ المجموعة، كيف يمكنني تنزيله؟")
        return ""

    if not user_member.status == 'administrator':
        message.reply_text("لا يمكن تنزيل من لم يتم رفعه!")
        return ""

    if user_id == bot.id:
        message.reply_text("لا أستطيع تنزيل نفسي! اطلب من أحد المشرفين فعل ذلك.")
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
        message.reply_text("لم أتمكن من التنزيل. قد لا أكون مشرفًا، أو أن صلاحية الإشراف مُنحت من قبل مستخدم آخر، لذا لا يمكنني التصرف تجاههم!")
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
    user = update.effective_user  # type: Optional[User]

    try:
        bot.unpinChatMessage(chat.id)
    except BadRequest as excp:
        if excp.message == "Chat_not_modified":
            pass
        else:
            raise

    return "<b>{}:</b>" \
           "\n#فك_تثبيت" \
           "\n<b>المشرف:</b> {}".format(html.escape(chat.title),
                                       mention_html(user.id, user.first_name))


@run_async
@bot_admin
@user_admin
def invite(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    
    if chat.username:
        update.effective_message.reply_text("@{}".format(chat.username))
    elif chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
        bot_member = chat.get_member(bot.id)
        if bot_member.can_invite_users:
            invitelink = bot.exportChatInviteLink(chat.id)
            linktext = "تم إنشاء رابط جديد لـ *{}:*".format(chat.title)
            link = "`{}`".format(invitelink)
            message.reply_text(linktext, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
            message.reply_text(link, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        else:
            message.reply_text("ليس لدي صلاحية الوصول إلى رابط الدعوة، حاول تغيير صلاحياتي!")
    else:
        message.reply_text("يمكنني إعطاء روابط الدعوة فقط للمجموعات الفائقة والقنوات، آسف!")


@run_async
def link_public(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    chat_id = update.effective_chat.id
    invitelink = sql.get_link(chat_id)
    
    if chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
        if invitelink:
            message.reply_text("رابط *{}*:\n`{}`".format(chat.title, invitelink), parse_mode=ParseMode.MARKDOWN)
        else:
            message.reply_text("مشرفو *{}* لم يحددوا رابطًا بعد."
                               " \nيمكن تعيين الرابط عبر: `/setlink` ثم الحصول على رابط المجموعة "
                               "باستخدام /invitelink، والصق الرابط بعد الأمر `/setlink`.".format(chat.title), parse_mode=ParseMode.MARKDOWN)
    else:
        message.reply_text("يمكنني حفظ الروابط فقط للمجموعات الفائقة والقنوات، آسف!")


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
        msg.reply_text("تم تعيين الرابط لـ {}!\nاسترجع الرابط باستخدام #link".format(chat.title))
    else:
        msg.reply_text("الرجاء إرسال الرابط مع الأمر، مثال: /setlink https://t.me/joinchat/...")


@run_async
@user_admin
def clear_link(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    sql.set_link(chat_id, "")
    update.effective_message.reply_text("تم مسح الرابط بنجاح!")


@run_async
def adminlist(bot: Bot, update: Update):
    administrators = update.effective_chat.get_administrators()
    text = "المشرفون في *{}*:".format(update.effective_chat.title or "هذه المجموعة")
    for admin in administrators:
        user = admin.user
        name = "[{}](tg://user?id={})".format(user.first_name + (user.last_name or ""), user.id)
        if user.username:
            name = escape_markdown("@" + user.username)
        text += "\n - {}".format(name)

    update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def __stats__():
    return "{} مجموعة لديها روابط محفوظة.".format(sql.num_chats())


def __chat_settings__(chat_id, user_id):
    return "أنت *مشرف*: `{}`".format(
        dispatcher.bot.get_chat_member(chat_id, user_id).status in ("administrator", "creator"))


# =================== نص المساعدة العربي ===================
__help__ = """
مرحبًا بك في أوامر الإشراف:

- /adminlist أو /staff: عرض قائمة المشرفين في المجموعة.
- /link: الحصول على رابط المجموعة (إذا تم حفظه مسبقًا).
- #link: نفس الأمر السابق.

*أوامر خاصة بالمشرفين:*
- /pin: تثبيت الرسالة التي تم الرد عليها. يمكن إضافة 'notify' أو 'loud' لإرسال إشعار للأعضاء.
- /unpin: فك تثبيت الرسالة المثبتة حالياً.
- /invitelink: إنشاء رابط دعوة جديد للمجموعة.
- /setlink <الرابط>: حفظ رابط المجموعة (للاستخدام مع /link).
- /clearlink: مسح الرابط المحفوظ للمجموعة.
- /promote: رفع العضو الذي تم الرد عليه إلى مشرف.
- /demote: تنزيل العضو الذي تم الرد عليه من الإشراف.

**الأوامر العربية (يمكنك كتابتها مباشرة بدون شرطة):**
- `رفع` (بالرد على مستخدم) ← رفعه مشرفًا.
- `تنزيل` (بالرد على مستخدم) ← تنزيله من الإشراف.
- `تثبيت` (بالرد على رسالة) ← تثبيت الرسالة.
- `فك التثبيت` ← إلغاء تثبيت الرسالة المثبتة.
- `دعوة` ← إنشاء رابط دعوة.
- `رابط عام` ← عرض رابط المجموعة المحفوظ.
- `تعيين الرابط <الرابط>` ← حفظ رابط المجموعة.
- `مسح الرابط` ← حذف الرابط المحفوظ.
- `قائمة الإشراف` ← عرض المشرفين.

مثال لتعيين رابط:
`/setlink https://t.me/joinchat/...`
أو بالعربية: `تعيين الرابط https://t.me/joinchat/...`

مثال لرفع مشرف:
`/promote @username`
أو بالرد على المستخدم وكتابة: `رفع`
"""

__mod_name__ = "الإشراف"

# =================== تسجيل المعالجات ===================
# المعالجات الأصلية
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

# المعالجات العربية الجديدة
PROMOTE_ARABIC_HANDLER = MessageHandler(Filters.regex(r'^(رفع)\s*(.*)') & Filters.group, promote_arabic)
DEMOTE_ARABIC_HANDLER = MessageHandler(Filters.regex(r'^(تنزيل)\s*(.*)') & Filters.group, demote_arabic)
PIN_ARABIC_HANDLER = MessageHandler(Filters.regex(r'^(تثبيت)\s*(.*)') & Filters.group, pin_arabic)
UNPIN_ARABIC_HANDLER = MessageHandler(Filters.regex(r'^(فك التثبيت)$') & Filters.group, unpin_arabic)
INVITE_ARABIC_HANDLER = MessageHandler(Filters.regex(r'^(دعوة)$') & Filters.group, invite_arabic)
LINK_PUBLIC_ARABIC_HANDLER = MessageHandler(Filters.regex(r'^(رابط عام)$') & Filters.group, link_public_arabic)
SET_LINK_ARABIC_HANDLER = MessageHandler(Filters.regex(r'^(تعيين الرابط)\s+(.+)') & Filters.group, set_link_arabic)
CLEAR_LINK_ARABIC_HANDLER = MessageHandler(Filters.regex(r'^(مسح الرابط)$') & Filters.group, clear_link_arabic)
ADMINLIST_ARABIC_HANDLER = MessageHandler(Filters.regex(r'^(قائمة الإشراف)$') & Filters.group, adminlist_arabic)

# إضافة جميع المعالجات إلى dispatcher
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

# إضافة المعالجات العربية
dispatcher.add_handler(PROMOTE_ARABIC_HANDLER)
dispatcher.add_handler(DEMOTE_ARABIC_HANDLER)
dispatcher.add_handler(PIN_ARABIC_HANDLER)
dispatcher.add_handler(UNPIN_ARABIC_HANDLER)
dispatcher.add_handler(INVITE_ARABIC_HANDLER)
dispatcher.add_handler(LINK_PUBLIC_ARABIC_HANDLER)
dispatcher.add_handler(SET_LINK_ARABIC_HANDLER)
dispatcher.add_handler(CLEAR_LINK_ARABIC_HANDLER)
dispatcher.add_handler(ADMINLIST_ARABIC_HANDLER)
