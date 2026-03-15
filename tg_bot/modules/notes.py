import re
import random
import html
from io import BytesIO
from typing import Optional, List, Dict, Any, Tuple

from telegram import Update, Message, Chat, User, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode, MessageLimit
from telegram.error import BadRequest
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ConversationHandler,
)
from telegram.helpers import escape_markdown, mention_html

from tg_bot import dispatcher, MESSAGE_DUMP, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin, connection_status
from tg_bot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from tg_bot.modules.helper_funcs.msg_types import get_note_type
from tg_bot.modules.helper_funcs.string_handling import (
    escape_invalid_curly_brackets,
    markdown_parser,
    button_markdown_parser,
    split_quotes,
)
from tg_bot.modules.sql import notes_sql as sql
from tg_bot.modules.connection import connected

# مراحل المحادثة
KEYWORD, REPLY_CONTENT = range(2)

# الحد الأقصى للردود لكل كلمة
MAX_REPLIES = 10

# نمط استخراج معرف الملف (من الإصدار القديم، للتوافق)
FILE_MATCHER = re.compile(r"^###file_id(!photo)?###:(.*?)(?:\s|$)")

# دوال الإرسال حسب نوع المحتوى
ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: "send_message",
    sql.Types.BUTTON_TEXT.value: "send_message",
    sql.Types.STICKER.value: "send_sticker",
    sql.Types.DOCUMENT.value: "send_document",
    sql.Types.PHOTO.value: "send_photo",
    sql.Types.AUDIO.value: "send_audio",
    sql.Types.VOICE.value: "send_voice",
    sql.Types.VIDEO.value: "send_video",
}


# =================== دوال مساعدة ===================

async def get_user_rank(update: Update, user_id: int) -> str:
    """الحصول على رتبة المستخدم في المجموعة."""
    chat = update.effective_chat
    try:
        member = await chat.get_member(user_id)
        if member.status == "creator":
            return "منشئ"
        elif member.status == "administrator":
            return "مشرف"
        else:
            return "عضو"
    except:
        return "عضو"


def format_note_content(
    content: str,
    target_user: Optional[Dict[str, Any]] = None,
    from_user: Optional[Dict[str, Any]] = None,
    target_user_rank: str = "",
) -> str:
    """استبدال المتغيرات في محتوى الملاحظة."""
    if target_user is None:
        target_user = {}
    if from_user is None:
        from_user = {}

    replacements = {
        "#الاسم": target_user.get("first_name", ""),
        "#يوزره": f"@{target_user.get('username', '')}" if target_user.get('username') else target_user.get("first_name", ""),
        "#اليوزر": f"@{from_user.get('username', '')}" if from_user.get('username') else from_user.get("first_name", ""),
        "#الايدي": str(target_user.get("id", "")),
        "#الرتبه": target_user_rank,
    }

    for var, value in replacements.items():
        content = content.replace(var, value)
    return content


async def send_note_content(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    reply_id: int,
    note_content: Dict,
):
    """إرسال محتوى الملاحظة (نص أو وسائط) مع الأزرار إن وجدت."""
    msg_type = note_content["msgtype"]
    file_id = note_content.get("file")
    text = note_content.get("text", "")
    buttons = note_content.get("buttons", [])
    parse_mode = ParseMode.MARKDOWN if note_content.get("has_markdown", False) else None
    disable_preview = not ("telegra.ph" in text or "youtu.be" in text)

    keyboard = InlineKeyboardMarkup(build_keyboard(buttons)) if buttons else None

    func_name = ENUM_FUNC_MAP.get(msg_type, "send_message")
    send_func = getattr(context.bot, func_name)

    try:
        if msg_type in (sql.Types.TEXT, sql.Types.BUTTON_TEXT):
            await send_func(
                chat_id=chat_id,
                text=text,
                reply_to_message_id=reply_id,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview,
                reply_markup=keyboard,
            )
        else:
            await send_func(
                chat_id=chat_id,
                file_id,
                caption=text,
                reply_to_message_id=reply_id,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview,
                reply_markup=keyboard,
            )
    except BadRequest as e:
        if e.message == "Entity_mention_user_invalid":
            await context.bot.send_message(
                chat_id,
                "يبدو أنك حاولت منشن شخص لم أره من قبل. إذا أردت منشنه، قم بإعادة توجيه إحدى رسائله إليّ.",
            )
        elif FILE_MATCHER.match(text):
            # رد قادم من استيراد غير صحيح
            await context.bot.send_message(
                chat_id,
                "هذه الملاحظة مستوردة بشكل غير صحيح من بوت آخر. سأحذفها.",
            )
            # حذف الملاحظة غير الصالحة (يجب تحديثه لاحقاً)
        else:
            LOGGER.exception("Could not parse note content: %s", text)
            await context.bot.send_message(
                chat_id,
                "حدث خطأ في إرسال الملاحظة. تحقق من التنسيق.",
            )


# =================== نظام إضافة الردود المتعددة ===================

@user_admin
async def add_note_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء محادثة إضافة رد مميز."""
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    # التحقق من الاتصال بمجموعة عن بُعد
    conn = await connected(update, context, chat, user.id, need_admin=True)
    if conn:
        context.user_data["note_chat_id"] = conn
        chat_name = (await context.bot.get_chat(conn)).title
        context.user_data["note_chat_name"] = chat_name
    else:
        context.user_data["note_chat_id"] = chat.id
        context.user_data["note_chat_name"] = chat.title

    await msg.reply_text(
        "• حسناً، الآن أرسل كلمة الرد المميز:"
    )
    return KEYWORD


async def get_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال الكلمة المفتاحية والانتقال إلى إرسال المحتوى."""
    keyword = update.effective_message.text.strip()
    chat_id = context.user_data["note_chat_id"]

    # التحقق من وجود الكلمة مسبقاً
    existing_note = sql.get_note(chat_id, keyword)
    if existing_note:
        # إذا كانت موجودة، نستخدم قائمة الردود الموجودة
        replies = existing_note.get("replies", [])
        context.user_data["note_replies"] = replies
    else:
        # كلمة جديدة، ننشئ قائمة فارغة
        context.user_data["note_replies"] = []

    context.user_data["note_keyword"] = keyword

    # إرسال رسالة التوجيه
    help_text = (
        "• حسناً يمكنك إضافة\n"
        "( نص، صورة، فيديو، متحركة، بصمة، أغنية، ملف )\n"
        "ويمكنك إضافة الرد بتلك الطريقة:\n"
        "▹ #الاسم - اسم العضو.\n"
        "▹ #يوزره - يوزر الرد.\n"
        "▹ #اليوزر - يوزر مرسل الرسالة.\n"
        "▹ #الايدي - ايدي الحلو.\n"
        "▹ #الرتبه - رتبة الحلو.\n"
        f"الردود الحالية: {len(context.user_data['note_replies'])}/{MAX_REPLIES}\n"
        "أرسل محتوى الرد الآن، أو أرسل `تم` للإنهاء."
    )
    await update.effective_message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    return REPLY_CONTENT


async def receive_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال محتوى الرد وإضافته إلى القائمة المؤقتة."""
    msg = update.effective_message
    chat_id = context.user_data["note_chat_id"]
    keyword = context.user_data["note_keyword"]

    # إذا كان المستخدم يريد إنهاء الإضافة
    if msg.text and msg.text.strip() == "تم":
        return await finish_adding(update, context)

    # تحليل المحتوى باستخدام get_note_type (متزامن)
    # ملاحظة: get_note_type تعمل مع الرسالة وتعيد (note_name, text, data_type, content, buttons)
    # نحتاج إلى استخراج البيانات المناسبة
    note_name, text, data_type, content, buttons = get_note_type(msg)

    if data_type is None:
        await msg.reply_text("لم ترسل محتوى صحيحاً! أرسل نصاً أو وسائط.")
        return REPLY_CONTENT

    # بناء كائن الرد
    reply_data = {
        "msgtype": data_type,
        "text": text,
        "file": content,
        "buttons": buttons,
        "has_markdown": True,  # نفترض أن جميع الردود الجديدة تدعم الماركداون
    }

    # إضافة إلى القائمة المؤقتة
    replies = context.user_data["note_replies"]
    replies.append(reply_data)

    # التحقق من العدد الأقصى
    remaining = MAX_REPLIES - len(replies)
    if remaining <= 0:
        # اكتمل العدد، ننهي ونحفظ
        return await finish_adding(update, context)

    await msg.reply_text(
        f"تم إضافة الرد، تبقى {remaining}.\n"
        "أرسل رداً آخر أو أرسل `تم` للإنهاء.",
        parse_mode=ParseMode.MARKDOWN,
    )
    return REPLY_CONTENT


async def finish_adding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ جميع الردود في قاعدة البيانات."""
    chat_id = context.user_data["note_chat_id"]
    keyword = context.user_data["note_keyword"]
    replies = context.user_data["note_replies"]

    if not replies:
        await update.effective_message.reply_text("لم تضف أي رد. تم الإلغاء.")
        return ConversationHandler.END

    # حفظ في قاعدة البيانات (سنتصل بوظيفة جديدة في notes_sql)
    try:
        sql.add_note_replies(chat_id, keyword, replies)
        await update.effective_message.reply_text(
            f"تم حفظ {len(replies)} ردود للكلمة '{keyword}'."
        )
    except Exception as e:
        LOGGER.exception("Error saving note replies")
        await update.effective_message.reply_text("حدث خطأ أثناء الحفظ.")

    # تنظيف البيانات المؤقتة
    context.user_data.pop("note_chat_id", None)
    context.user_data.pop("note_chat_name", None)
    context.user_data.pop("note_keyword", None)
    context.user_data.pop("note_replies", None)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء المحادثة."""
    await update.effective_message.reply_text("تم إلغاء الإضافة.")
    context.user_data.pop("note_chat_id", None)
    context.user_data.pop("note_chat_name", None)
    context.user_data.pop("note_keyword", None)
    context.user_data.pop("note_replies", None)
    return ConversationHandler.END


# =================== دوال استدعاء الملاحظات ===================

async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE, notename: str, show_none: bool = True, no_format: bool = False):
    """استدعاء ملاحظة (اختيار رد عشوائي وتنسيقه)."""
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    # تحديد معرف المجموعة (قد يكون متصلاً)
    conn = await connected(update, context, chat, user.id, need_admin=False)
    if conn:
        chat_id = conn
        send_id = user.id
    else:
        chat_id = chat.id
        send_id = chat_id

    note_data = sql.get_note(chat_id, notename)
    if not note_data:
        if show_none:
            await message.reply_text("هذه الملاحظة غير موجودة.")
        return

    # استخراج قائمة الردود
    replies = note_data.get("replies", [])
    if not replies:
        await message.reply_text("لا توجد ردود لهذه الملاحظة.")
        return

    # اختيار رد عشوائي
    selected = random.choice(replies)

    # تحضير المتغيرات للتنسيق
    target_user = None
    from_user = None
    target_user_rank = ""

    # إذا كانت الرسالة رداً على شخص ما، نأخذ ذلك الشخص كهدف
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        target_user = {
            "id": target.id,
            "first_name": target.first_name,
            "username": target.username,
        }
        target_user_rank = await get_user_rank(update, target.id)
    else:
        # خلاف ذلك، الهدف هو المرسل نفسه (أو ربما لا نضع هدفاً)
        pass

    from_user = {
        "id": user.id,
        "first_name": user.first_name,
        "username": user.username,
    }

    # تنسيق النص إذا كان موجوداً
    text = selected.get("text", "")
    if text:
        text = format_note_content(text, target_user, from_user, target_user_rank)

    # تحديد معرف الرد
    reply_id = message.reply_to_message.message_id if message.reply_to_message else message.message_id

    # إرسال المحتوى
    await send_note_content(context, chat_id, reply_id, {**selected, "text": text})


async def cmd_get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /get."""
    args = context.args
    if len(args) >= 2 and args[1].lower() == "noformat":
        await get_note(update, context, args[0], show_none=True, no_format=True)
    elif len(args) >= 1:
        await get_note(update, context, args[0], show_none=True)
    else:
        await update.effective_message.reply_text("استخدم: /get <اسم الملاحظة>")


async def hash_get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج استدعاء الملاحظة بـ #."""
    message = update.effective_message
    fst_word = message.text.split()[0]
    no_hash = fst_word[1:]
    await get_note(update, context, no_hash, show_none=False)


@user_admin
async def save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ ملاحظة جديدة (الطريقة القديمة - ولكن نعدلها لاستخدام النظام الجديد)."""
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    conn = await connected(update, context, chat, user.id)
    if conn:
        chat_id = conn
        chat_name = (await context.bot.get_chat(conn)).title
    else:
        chat_id = chat.id
        chat_name = chat.title if chat.type != "private" else "الملاحظات المحلية"

    note_name, text, data_type, content, buttons = get_note_type(msg)

    if data_type is None:
        await msg.reply_text("لم ترسل محتوى صحيحاً!")
        return

    if len(text.strip()) == 0:
        text = note_name

    # إنشاء قائمة ردود تحتوي على هذا الرد الواحد
    reply_data = {
        "msgtype": data_type,
        "text": text,
        "file": content,
        "buttons": buttons,
        "has_markdown": True,
    }
    replies = [reply_data]

    sql.add_note_replies(chat_id, note_name, replies)

    await msg.reply_text(
        f"تم إضافة {note_name} في *{chat_name}*.\n"
        f"استخدم /get {note_name} أو #{note_name}",
        parse_mode=ParseMode.MARKDOWN,
    )

    if msg.reply_to_message and msg.reply_to_message.from_user.is_bot:
        await msg.reply_text(
            "يبدو أنك تحاول حفظ رسالة من بوت. البوتات لا تستطيع إعادة توجيه رسائل البوتات، "
            "لذا قد لا يتم حفظ المحتوى بشكل كامل."
        )


@user_admin
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مسح ملاحظة."""
    chat = update.effective_chat
    user = update.effective_user
    args = context.args

    conn = await connected(update, context, chat, user.id)
    if conn:
        chat_id = conn
        chat_name = (await context.bot.get_chat(conn)).title
    else:
        chat_id = chat.id
        chat_name = chat.title if chat.type != "private" else "الملاحظات المحلية"

    if len(args) >= 1:
        notename = args[0]
        if sql.rm_note(chat_id, notename):
            await update.effective_message.reply_text("تم مسح الملاحظة بنجاح.")
        else:
            await update.effective_message.reply_text("لا توجد ملاحظة بهذا الاسم.")
    else:
        await update.effective_message.reply_text("استخدم: /clear <اسم الملاحظة>")


async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الملاحظات."""
    chat = update.effective_chat
    user = update.effective_user

    conn = await connected(update, context, chat, user.id, need_admin=False)
    if conn:
        chat_id = conn
        chat_name = (await context.bot.get_chat(conn)).title
    else:
        chat_id = chat.id
        chat_name = chat.title if chat.type != "private" else "الملاحظات المحلية"

    notes_list = sql.get_all_chat_notes(chat_id)
    if not notes_list:
        await update.effective_message.reply_text("لا توجد ملاحظات في هذه المحادثة.")
        return

    msg = f"*الملاحظات في {chat_name}:*\n"
    for note in notes_list:
        note_line = f" - {escape_markdown(note.name)}\n"
        if len(msg) + len(note_line) > MessageLimit.MAX_TEXT_LENGTH:
            await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            msg = ""
        msg += note_line

    if msg:
        await update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


def __import_data__(chat_id, data):
    """استيراد بيانات من بوت آخر (للتوافق)."""
    failures = []
    for notename, notedata in data.get('extra', {}).items():
        match = FILE_MATCHER.match(notedata)
        if match:
            failures.append(notename)
            notedata = notedata[match.end():].strip()
            if notedata:
                # حفظ كرد واحد
                replies = [{"msgtype": sql.Types.TEXT, "text": notedata, "buttons": [], "has_markdown": False}]
                sql.add_note_replies(chat_id, notename[1:], replies)
        else:
            replies = [{"msgtype": sql.Types.TEXT, "text": notedata, "buttons": [], "has_markdown": False}]
            sql.add_note_replies(chat_id, notename[1:], replies)

    if failures:
        with BytesIO(str.encode("\n".join(failures))) as output:
            output.name = "failed_imports.txt"
            dispatcher.bot.send_document(
                chat_id,
                document=output,
                filename="failed_imports.txt",
                caption="هذه الملفات/الصور فشل استيرادها بسبب قيود تيليجرام.",
            )


def __stats__():
    return f"{sql.num_notes()} ملاحظة في {sql.num_chats()} مجموعة."


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


async def __chat_settings__(chat_id: int, user_id: int) -> str:
    notes = sql.get_all_chat_notes(chat_id)
    return f"يوجد `{len(notes)}` ملاحظات في هذه المجموعة."


__help__ = """
- /get <اسم الملاحظة>: الحصول على الملاحظة.
- #<اسم الملاحظة>: نفس الأمر.
- /notes أو /saved: عرض جميع الملاحظات المحفوظة.

إذا أردت استرجاع محتوى الملاحظة بدون تنسيق، استخدم `/get <اسم الملاحظة> noformat`.

*للمشرفين فقط:*
- /save <اسم الملاحظة> <المحتوى>: حفظ ملاحظة جديدة.
- /save <اسم الملاحظة> (بالرد على رسالة): حفظ الرسالة كملاحظة.
- /clear <اسم الملاحظة>: مسح الملاحظة.
- `اضف رد مميز` (أمر عربي): إضافة ردود متعددة لكلمة معينة.
"""

__mod_name__ = "الملاحظات"

# معالج المحادثة للإضافة المتعددة
ADD_NOTE_CONV = ConversationHandler(
    entry_points=[CommandHandler("اضف رد مميز", add_note_start)],
    states={
        KEYWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_keyword)],
        REPLY_CONTENT: [MessageHandler(filters.ALL & ~filters.COMMAND, receive_reply)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# المعالجات الأخرى
GET_HANDLER = CommandHandler("get", cmd_get)
HASH_GET_HANDLER = MessageHandler(filters.Regex(r"^#\S+"), hash_get)
SAVE_HANDLER = CommandHandler("save", save)
DELETE_HANDLER = CommandHandler("clear", clear)
LIST_HANDLER = DisableAbleCommandHandler(["notes", "saved"], list_notes, admin_ok=True)

dispatcher.add_handler(ADD_NOTE_CONV)
dispatcher.add_handler(GET_HANDLER)
dispatcher.add_handler(SAVE_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(HASH_GET_HANDLER)
