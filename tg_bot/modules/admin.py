import html
from typing import Optional, List

from telegram import Update, Bot, Chat, Message, User
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes
from telegram.helpers import mention_html

from tg_bot import dispatcher  # سيتم إزالة dispatcher لاحقاً، لكننا نحتاجه مؤقتاً للتوافق مع بقية الكود
import tg_bot.modules.sql.setlink_sql as sql
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import bot_admin, can_promote, user_admin, can_pin, connection_status
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.log_channel import loggable

# ------------------- دالة مساعدة للأوامر العربية -------------------
def extract_args_from_text(text: str, keyword: str) -> List[str]:
    """استخراج المعاملات بعد الكلمة المفتاحية"""
    if text.startswith(keyword):
        rest = text[len(keyword):].strip()
        return rest.split() if rest else []
    return []

# =================== الأوامر العربية الجديدة (غير متزامنة) ===================

@bot_admin
@can_promote
@user_admin
@loggable
async def promote_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    message = update.effective_message
    text = message.text
    args = extract_args_from_text(text, "رفع")
    # استدعاء الدالة الأصلية مع args
    return await promote(update, context)


@bot_admin
@can_promote
@user_admin
@loggable
async def demote_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    message = update.effective_message
    text = message.text
    args = extract_args_from_text(text, "تنزيل")
    return await demote(update, context)


@bot_admin
@can_pin
@user_admin
@loggable
async def pin_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    message = update.effective_message
    text = message.text
    args = extract_args_from_text(text, "تثبيت")
    return await pin(update, context)


@bot_admin
@can_pin
@user_admin
@loggable
async def unpin_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    return await unpin(update, context)


@bot_admin
@user_admin
async def invite_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    text = message.text
    args = extract_args_from_text(text, "دعوة")
    return await invite(update, context)


async def link_public_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    text = message.text
    args = extract_args_from_text(text, "رابط عام")
    return await link_public(update, context)


@user_admin
async def set_link_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    text = message.text
    args = extract_args_from_text(text, "تعيين الرابط")
    return await set_link(update, context)


@user_admin
async def clear_link_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    text = message.text
    args = extract_args_from_text(text, "مسح الرابط")
    return await clear_link(update, context)


async def adminlist_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    text = message.text
    args = extract_args_from_text(text, "قائمة الإشراف")
    return await adminlist(update, context)

# =================== الدوال الأصلية (محدثة) ===================

@bot_admin
@can_promote
@user_admin
@loggable
async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat_id = update.effective_chat.id
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    user_id = extract_user(message, context.args)
    if not user_id:
        await message.reply_text("لم تحدد أي مستخدم للإشارة إليه.")
        return ""

    user_member = await chat.get_member(user_id)
    if user_member.status in ('administrator', 'creator'):
        await message.reply_text("كيف يمكنني رفع شخص هو بالفعل مشرف؟")
        return ""

    if user_id == context.bot.id:
        await message.reply_text("لا أستطيع رفع نفسي! اطلب من أحد المشرفين فعل ذلك.")
        return ""

    # تعيين نفس صلاحيات البوت - لا يمكن للبوت منح صلاحيات أعلى من صلاحياته
    bot_member = await chat.get_member(context.bot.id)

    await context.bot.promote_chat_member(
        chat_id, user_id,
        can_change_info=bot_member.can_change_info,
        can_post_messages=bot_member.can_post_messages,
        can_edit_messages=bot_member.can_edit_messages,
        can_delete_messages=bot_member.can_delete_messages,
        can_restrict_members=bot_member.can_restrict_members,
        can_pin_messages=bot_member.can_pin_messages,
        can_promote_members=bot_member.can_promote_members
    )

    await message.reply_text("تم الترقية بنجاح!")
    return "<b>{}:</b>" \
           "\n#رفع" \
           "\n<b>المشرف:</b> {}" \
           "\n<b>المستخدم:</b> {}".format(
               html.escape(chat.title),
               mention_html(user.id, user.first_name),
               mention_html(user_member.user.id, user_member.user.first_name)
           )


@bot_admin
@can_promote
@user_admin
@loggable
async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user

    user_id = extract_user(message, context.args)
    if not user_id:
        await message.reply_text("لم تحدد أي مستخدم للإشارة إليه.")
        return ""

    user_member = await chat.get_member(user_id)
    if user_member.status == 'creator':
        await message.reply_text("هذا الشخص هو منشئ المجموعة، كيف يمكنني تنزيله؟")
        return ""

    if user_member.status != 'administrator':
        await message.reply_text("لا يمكن تنزيل من لم يتم رفعه!")
        return ""

    if user_id == context.bot.id:
        await message.reply_text("لا أستطيع تنزيل نفسي! اطلب من أحد المشرفين فعل ذلك.")
        return ""

    try:
        await context.bot.promote_chat_member(
            int(chat.id), int(user_id),
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False
        )
        await message.reply_text("تم التنزيل بنجاح!")
        return "<b>{}:</b>" \
               "\n#تنزيل" \
               "\n<b>المشرف:</b> {}" \
               "\n<b>المستخدم:</b> {}".format(
                   html.escape(chat.title),
                   mention_html(user.id, user.first_name),
                   mention_html(user_member.user.id, user_member.user.first_name)
               )
    except BadRequest:
        await message.reply_text("لم أتمكن من التنزيل. قد لا أكون مشرفًا، أو أن صلاحية الإشراف مُنحت من قبل مستخدم آخر، لذا لا يمكنني التصرف تجاههم!")
        return ""


@bot_admin
@can_pin
@user_admin
@loggable
async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user = update.effective_user
    chat = update.effective_chat

    is_group = chat.type != "private" and chat.type != "channel"

    prev_message = update.effective_message.reply_to_message

    is_silent = True
    if context.args:
        is_silent = not (context.args[0].lower() == 'notify' or context.args[0].lower() == 'loud' or context.args[0].lower() == 'violent')

    if prev_message and is_group:
        try:
            await context.bot.pin_chat_message(chat.id, prev_message.message_id, disable_notification=is_silent)
        except BadRequest as excp:
            if excp.message != "Chat_not_modified":
                raise
        return "<b>{}:</b>" \
               "\n#تثبيت" \
               "\n<b>المشرف:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name))

    return ""


@bot_admin
@can_pin
@user_admin
@loggable
async def unpin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat = update.effective_chat
    user = update.effective_user

    try:
        await context.bot.unpin_chat_message(chat.id)
    except BadRequest as excp:
        if excp.message != "Chat_not_modified":
            raise

    return "<b>{}:</b>" \
           "\n#فك_تثبيت" \
           "\n<b>المشرف:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name))


@bot_admin
@user_admin
async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
    
    if chat.username:
        await message.reply_text(f"@{chat.username}")
    elif chat.type in (chat.SUPERGROUP, chat.CHANNEL):
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.can_invite_users:
            invitelink = await context.bot.export_chat_invite_link(chat.id)
            linktext = f"تم إنشاء رابط جديد لـ *{chat.title}:*"
            link = f"`{invitelink}`"
            await message.reply_text(linktext, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
            await message.reply_text(link, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        else:
            await message.reply_text("ليس لدي صلاحية الوصول إلى رابط الدعوة، حاول تغيير صلاحياتي!")
    else:
        await message.reply_text("يمكنني إعطاء روابط الدعوة فقط للمجموعات الفائقة والقنوات، آسف!")


async def link_public(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
    chat_id = update.effective_chat.id
    invitelink = sql.get_link(chat_id)
    
    if chat.type in (chat.SUPERGROUP, chat.CHANNEL):
        if invitelink:
            await message.reply_text(f"رابط *{chat.title}:*\n`{invitelink}`", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text(
                f"مشرفو *{chat.title}* لم يحددوا رابطًا بعد.\n"
                "يمكن تعيين الرابط عبر: `/setlink` ثم الحصول على رابط المجموعة باستخدام /invitelink، والصق الرابط بعد الأمر `/setlink`.",
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await message.reply_text("يمكنني حفظ الروابط فقط للمجموعات الفائقة والقنوات، آسف!")


@user_admin
async def set_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = update.effective_message
    chat = update.effective_chat
    raw_text = msg.text
    args = raw_text.split(None, 1)
    
    if len(args) == 2:
        links_text = args[1]
        sql.set_link(chat_id, links_text)
        await msg.reply_text(f"تم تعيين الرابط لـ {chat.title}!\nاسترجع الرابط باستخدام #link")
    else:
        await msg.reply_text("الرجاء إرسال الرابط مع الأمر، مثال: /setlink https://t.me/joinchat/...")


@user_admin
async def clear_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sql.set_link(chat_id, "")
    await update.effective_message.reply_text("تم مسح الرابط بنجاح!")


async def adminlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    administrators = await update.effective_chat.get_administrators()
    text = f"المشرفون في *{update.effective_chat.title or 'هذه المجموعة'}*:"
    for admin in administrators:
        user = admin.user
        name = f"[{user.first_name}{' ' + user.last_name if user.last_name else ''}](tg://user?id={user.id})"
        if user.username:
            name = "@" + user.username
        text += f"\n - {name}"

    await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def __stats__():
    return f"{} مجموعة لديها روابط محفوظة.".format(sql.num_chats())


async def __chat_settings__(chat_id: int, user_id: int) -> str:
    # هذه الدالة تُستدعى من settings_button في __main__.py مع await
    status = (await dispatcher.bot.get_chat_member(chat_id, user_id)).status
    return f"أنت *مشرف*: `{status in ('administrator', 'creator')}`"


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

# =================== تسجيل المعالجات (ملاحظة: لم نعد نستخدم dispatcher مباشرةً، ولكن هذا الجزء سيُعدّل لاحقاً) ===================
from tg_bot import dispatcher

# المعالجات الأصلية
PIN_HANDLER = CommandHandler("pin", pin, filters=filters.ChatType.GROUPS)
UNPIN_HANDLER = CommandHandler("unpin", unpin, filters=filters.ChatType.GROUPS)
LINK_HANDLER = DisableAbleCommandHandler("link", link_public, filters=filters.ChatType.GROUPS)
SET_LINK_HANDLER = CommandHandler("setlink", set_link, filters=filters.ChatType.GROUPS)
RESET_LINK_HANDLER = CommandHandler("clearlink", clear_link, filters=filters.ChatType.GROUPS)
HASH_LINK_HANDLER = MessageHandler(filters.Regex(r"^#link$") & filters.ChatType.GROUPS, link_public)
INVITE_HANDLER = CommandHandler("invitelink", invite, filters=filters.ChatType.GROUPS)
PROMOTE_HANDLER = CommandHandler("promote", promote, filters=filters.ChatType.GROUPS)
DEMOTE_HANDLER = CommandHandler("demote", demote, filters=filters.ChatType.GROUPS)
ADMINLIST_HANDLER = DisableAbleCommandHandler(["adminlist", "staff"], adminlist, filters=filters.ChatType.GROUPS)

# المعالجات العربية الجديدة
PROMOTE_ARABIC_HANDLER = MessageHandler(filters.Regex(r"^(رفع)\s*(.*)") & filters.ChatType.GROUPS, promote_arabic)
DEMOTE_ARABIC_HANDLER = MessageHandler(filters.Regex(r"^(تنزيل)\s*(.*)") & filters.ChatType.GROUPS, demote_arabic)
PIN_ARABIC_HANDLER = MessageHandler(filters.Regex(r"^(تثبيت)\s*(.*)") & filters.ChatType.GROUPS, pin_arabic)
UNPIN_ARABIC_HANDLER = MessageHandler(filters.Regex(r"^(فك التثبيت)$") & filters.ChatType.GROUPS, unpin_arabic)
INVITE_ARABIC_HANDLER = MessageHandler(filters.Regex(r"^(دعوة)$") & filters.ChatType.GROUPS, invite_arabic)
LINK_PUBLIC_ARABIC_HANDLER = MessageHandler(filters.Regex(r"^(رابط عام)$") & filters.ChatType.GROUPS, link_public_arabic)
SET_LINK_ARABIC_HANDLER = MessageHandler(filters.Regex(r"^(تعيين الرابط)\s+(.+)") & filters.ChatType.GROUPS, set_link_arabic)
CLEAR_LINK_ARABIC_HANDLER = MessageHandler(filters.Regex(r"^(مسح الرابط)$") & filters.ChatType.GROUPS, clear_link_arabic)
ADMINLIST_ARABIC_HANDLER = MessageHandler(filters.Regex(r"^(قائمة الإشراف)$") & filters.ChatType.GROUPS, adminlist_arabic)

# إضافة جميع المعالجات إلى dispatcher (ملاحظة: في الإصدار الجديد، يجب استخدام application.add_handler بدلاً من dispatcher)
# لكننا سنبقيها هكذا مؤقتاً حتى نقوم بتحديث آلية التحميل في __main__.py لاحقاً.
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

dispatcher.add_handler(PROMOTE_ARABIC_HANDLER)
dispatcher.add_handler(DEMOTE_ARABIC_HANDLER)
dispatcher.add_handler(PIN_ARABIC_HANDLER)
dispatcher.add_handler(UNPIN_ARABIC_HANDLER)
dispatcher.add_handler(INVITE_ARABIC_HANDLER)
dispatcher.add_handler(LINK_PUBLIC_ARABIC_HANDLER)
dispatcher.add_handler(SET_LINK_ARABIC_HANDLER)
dispatcher.add_handler(CLEAR_LINK_ARABIC_HANDLER)
dispatcher.add_handler(ADMINLIST_ARABIC_HANDLER)
