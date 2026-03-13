import re
from io import BytesIO
from typing import Optional, List

from telegram import MAX_MESSAGE_LENGTH, ParseMode, InlineKeyboardMarkup
from telegram import Message, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, RegexHandler, MessageHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown

import tg_bot.modules.sql.notes_sql as sql
from tg_bot import dispatcher, MESSAGE_DUMP, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from tg_bot.modules.helper_funcs.msg_types import get_note_type
from tg_bot.modules.connection import connected

FILE_MATCHER = re.compile(r"^###file_id(!photo)?###:(.*?)(?:\s|$)")

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video
}


# لا تستخدم async
def get(bot, update, notename, show_none=True, no_format=False):
    chat_id = update.effective_chat.id
    chat = update.effective_chat
    user = update.effective_user
    conn = connected(bot, update, chat, user.id, need_admin=False)
    if not conn == False:
        chat_id = conn
        send_id = user.id
    else:
        chat_id = update.effective_chat.id
        send_id = chat_id

    note = sql.get_note(chat_id, notename)
    message = update.effective_message

    if note:
        if message.reply_to_message:
            reply_id = message.reply_to_message.message_id
        else:
            reply_id = message.message_id

        if note.is_reply:
            if MESSAGE_DUMP:
                try:
                    bot.forward_message(chat_id=update.effective_chat.id, from_chat_id=MESSAGE_DUMP, message_id=note.value)
                except BadRequest as excp:
                    if excp.message == "Message to forward not found":
                        message.reply_text("يبدو أن هذه الرسالة قد فقدت - سأزيلها من قائمة ملاحظاتك.")
                        sql.rm_note(chat_id, notename)
                    else:
                        raise
            else:
                try:
                    bot.forward_message(chat_id=update.effective_chat.id, from_chat_id=chat_id, message_id=note.value)
                except BadRequest as excp:
                    if excp.message == "Message to forward not found":
                        message.reply_text("يبدو أن المرسل الأصلي لهذه الملاحظة قد حذف رسالته - آسف! اطلب من مشرف البوت البدء في استخدام تفريغ الرسائل لتجنب هذا. سأزيل هذه الملاحظة من ملاحظاتك المحفوظة.")
                        sql.rm_note(chat_id, notename)
                    else:
                        raise
        else:
            text = note.value
            keyb = []
            parseMode = ParseMode.MARKDOWN
            buttons = sql.get_buttons(chat_id, notename)
            should_preview_disabled = True
            if no_format:
                parseMode = None
                text += revert_buttons(buttons)
            else:
                keyb = build_keyboard(buttons)
                if "telegra.ph" in text or "youtu.be" in text:
                    should_preview_disabled = False

            keyboard = InlineKeyboardMarkup(keyb)

            try:
                if note.msgtype in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):

                    bot.send_message(chat_id, text, reply_to_message_id=reply_id,
                                     parse_mode=parseMode, disable_web_page_preview=should_preview_disabled,
                                     reply_markup=keyboard)
                else:
                    ENUM_FUNC_MAP[note.msgtype](chat_id, note.file, caption=text, reply_to_message_id=reply_id,
                                                parse_mode=parseMode, disable_web_page_preview=should_preview_disabled,
                                                reply_markup=keyboard)

            except BadRequest as excp:
                if excp.message == "Entity_mention_user_invalid":
                    message.reply_text("يبدو أنك حاولت ذكر شخص لم أره من قبل. إذا كنت تريد حقاً ذكره، قم بإعادة توجيه إحدى رسائله إلي، وسأتمكن من منشنهم!")
                elif FILE_MATCHER.match(note.value):
                    message.reply_text("تم استيراد هذه الملاحظة بشكل غير صحيح من بوت آخر - لا يمكنني استخدامها. إذا كنت بحاجة إليها حقاً، ستحتاج إلى حفظها مرة أخرى. في هذه الأثناء، سأزيلها من قائمة ملاحظاتك.")
                    sql.rm_note(chat_id, notename)
                else:
                    message.reply_text("تعذر إرسال هذه الملاحظة، لأن تنسيقها غير صحيح. اسأل في @keralabots إذا كنت لا تستطيع معرفة السبب!")
                    LOGGER.exception("تعذر تحليل الرسالة #%s في الدردشة %s", notename, str(chat_id))
                    LOGGER.warning("الرسالة كانت: %s", str(note.value))
        return
    elif show_none:
        message.reply_text("هذه الملاحظة غير موجودة")


@run_async
def cmd_get(bot: Bot, update: Update, args: List[str]):
    if len(args) >= 2 and args[1].lower() == "noformat":
        get(bot, update, args[0], show_none=True, no_format=True)
    elif len(args) >= 1:
        get(bot, update, args[0], show_none=True)
    else:
        update.effective_message.reply_text("الاستخدام: /get <اسم_الملاحظة>")


@run_async
def hash_get(bot: Bot, update: Update):
    message = update.effective_message.text
    fst_word = message.split()[0]
    no_hash = fst_word[1:]
    get(bot, update, no_hash, show_none=False)


@run_async
@user_admin
def save(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user
    conn = connected(bot, update, chat, user.id)
    if not conn == False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = "الملاحظات المحلية"
        else:
            chat_name = chat.title

    msg = update.effective_message

    note_name, text, data_type, content, buttons = get_note_type(msg)

    if data_type is None:
        msg.reply_text("يا صاح، لا توجد ملاحظة")
        return

    if len(text.strip()) == 0:
        text = note_name

    sql.add_note_to_db(chat_id, note_name, text, data_type, buttons=buttons, file=content)

    msg.reply_text(
        "تمت إضافة {} في *{}*.\nيمكنك الحصول عليها بـ /get {}، أو #{}".format(note_name, chat_name, note_name, note_name), parse_mode=ParseMode.MARKDOWN)

    if msg.reply_to_message and msg.reply_to_message.from_user.is_bot:
        if text:
            msg.reply_text("يبدو أنك تحاول حفظ رسالة من بوت. لسوء الحظ، لا يمكن للبوتات إعادة توجيه رسائل البوتات، لذا لا يمكنني حفظ الرسالة بالضبط. سأحفظ كل النص الذي يمكنني، ولكن إذا كنت تريد المزيد، فسيتعين عليك إعادة توجيه الرسالة بنفسك، ثم حفظها.")
        else:
            msg.reply_text("البوتات مقيدة نوعاً ما بواسطة تليجرام، مما يجعل من الصعب على البوتات التفاعل مع البوتات الأخرى، لذا لا يمكنني حفظ هذه الرسالة كما أفعل عادةً - هل تمانع في إعادة توجيهها ثم حفظ تلك الرسالة الجديدة؟ شكراً!")
        return


@run_async
@user_admin
def clear(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    user = update.effective_user
    conn = connected(bot, update, chat, user.id)
    if not conn == False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = "الملاحظات المحلية"
        else:
            chat_name = chat.title

    if len(args) >= 1:
        notename = args[0]

        if sql.rm_note(chat_id, notename):
            update.effective_message.reply_text("تمت إزالة الملاحظة بنجاح.")
        else:
            update.effective_message.reply_text("هذه ليست ملاحظة في قاعدة البيانات!")


@run_async
def list_notes(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    chat = update.effective_chat
    user = update.effective_user
    conn = connected(bot, update, chat, user.id, need_admin=False)
    if not conn == False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
        msg = "*الملاحظات في {}:*\n".format(chat_name)
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = ""
            msg = "*الملاحظات المحلية:*\n"
        else:
            chat_name = chat.title
            msg = "*الملاحظات في {}:*\n".format(chat_name)

    note_list = sql.get_all_chat_notes(chat_id)

    for note in note_list:
        note_name = escape_markdown(" - {}\n".format(note.name))
        if len(msg) + len(note_name) > MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            msg = ""
        msg += note_name

    if msg == "*الملاحظات في الدردشة:*\n":
        update.effective_message.reply_text("لا توجد ملاحظات في هذه الدردشة!")

    elif len(msg) != 0:
        update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


def __import_data__(chat_id, data):
    failures = []
    for notename, notedata in data.get('extra', {}).items():
        match = FILE_MATCHER.match(notedata)

        if match:
            failures.append(notename)
            notedata = notedata[match.end():].strip()
            if notedata:
                sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)
        else:
            sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)

    if failures:
        with BytesIO(str.encode("\n".join(failures))) as output:
            output.name = "failed_imports.txt"
            dispatcher.bot.send_document(chat_id, document=output, filename="failed_imports.txt",
                                         caption="فشلت استيراد هذه الملفات/الصور بسبب مصدرها من بوت آخر. هذا قيد من واجهة برمجة تطبيقات تليجرام، ولا يمكن تجنبه. نأسف للإزعاج!")


def __stats__():
    return "{} ملاحظة، عبر {} دردشة.".format(sql.num_notes(), sql.num_chats())


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    notes = sql.get_all_chat_notes(chat_id)
    return "هناك `{}` ملاحظة في هذه الدردشة.".format(len(notes))


# ================== المساعدة ==================
__help__ = """
- /get <اسم_الملاحظة>: الحصول على الملاحظة بهذا الاسم
- #<اسم_الملاحظة>: نفس /get
- /notes أو /saved: قائمة بجميع الملاحظات المحفوظة في هذه الدردشة

إذا أردت استرجاع محتويات ملاحظة بدون أي تنسيق، استخدم `/get <اسم_الملاحظة> noformat`. يمكن أن يكون هذا مفيداً عند تحديث ملاحظة حالية.

*للمشرفين فقط:*
- /save <اسم_الملاحظة> <بيانات_الملاحظة>: يحفظ بيانات_الملاحظة كملاحظة باسم اسم_الملاحظة
يمكن إضافة زر إلى ملاحظة باستخدام صيغة رابط ماركداون القياسية - يجب أن يسبق الرابط قسم `buttonurl:`، كما يلي: `[رابط ما](buttonurl:example.com)`. تحقق من /markdownhelp لمزيد من المعلومات.
- /save <اسم_الملاحظة>: حفظ الرسالة التي تم الرد عليها كملاحظة باسم اسم_الملاحظة
- /clear <اسم_الملاحظة>: مسح الملاحظة بهذا الاسم

*الأوامر العربية (بدون /):*
ملاحظة <الاسم>: الحصول على ملاحظة
ملاحظات: عرض قائمة الملاحظات
حفظ ملاحظة <الاسم> <النص>: حفظ ملاحظة جديدة
حذف ملاحظة <الاسم>: حذف ملاحظة
"""

__mod_name__ = "الملاحظات"

GET_HANDLER = CommandHandler("get", cmd_get, pass_args=True)
HASH_GET_HANDLER = RegexHandler(r"^#[^\s]+", hash_get)

SAVE_HANDLER = CommandHandler("save", save)
DELETE_HANDLER = CommandHandler("clear", clear, pass_args=True)

LIST_HANDLER = DisableAbleCommandHandler(["notes", "saved"], list_notes, admin_ok=True)

# معالجات الأوامر العربية
GET_AR_HANDLER = CommandHandler("ملاحظة", cmd_get, pass_args=True)
LIST_AR_HANDLER = CommandHandler("ملاحظات", list_notes)
SAVE_AR_HANDLER = CommandHandler("حفظ ملاحظة", save)
DELETE_AR_HANDLER = CommandHandler("حذف ملاحظة", clear, pass_args=True)

dispatcher.add_handler(GET_HANDLER)
dispatcher.add_handler(SAVE_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(HASH_GET_HANDLER)

dispatcher.add_handler(GET_AR_HANDLER)
dispatcher.add_handler(LIST_AR_HANDLER)
dispatcher.add_handler(SAVE_AR_HANDLER)
dispatcher.add_handler(DELETE_AR_HANDLER)
