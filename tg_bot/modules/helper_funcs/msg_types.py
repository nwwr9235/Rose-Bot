from enum import IntEnum, unique

from telegram import Message

from tg_bot.modules.helper_funcs.string_handling import button_markdown_parser


@unique
class Types(IntEnum):
    """أنواع المحتوى للملاحظات والرسائل الترحيبية."""
    TEXT = 0
    BUTTON_TEXT = 1
    STICKER = 2
    DOCUMENT = 3
    PHOTO = 4
    AUDIO = 5
    VOICE = 6
    VIDEO = 7


def get_note_type(msg: Message):
    """
    تحديد نوع الملاحظة (نص، صورة، ملصق، إلخ) واستخراج محتواها.

    :param msg: رسالة التليجرام
    :return: (اسم_الملاحظة, النص, نوع_البيانات, المحتوى, الأزرار)
    """
    data_type = None
    content = None
    text = ""
    raw_text = msg.text or msg.caption
    args = raw_text.split(None, 2)  # استخدام maxsplit لفصل الأمر واسم الملاحظة
    note_name = args[1]

    buttons = []
    # تحديد محتويات الفلتر - نص، صورة، ملصق، إلخ
    if len(args) >= 3:
        offset = len(args[2]) - len(raw_text)  # ضبط الإزاحة الصحيحة نسبةً للأمر + اسم الملاحظة
        text, buttons = button_markdown_parser(args[2], entities=msg.parse_entities() or msg.parse_caption_entities(),
                                               offset=offset)
        if buttons:
            data_type = Types.BUTTON_TEXT
        else:
            data_type = Types.TEXT

    elif msg.reply_to_message:
        entities = msg.reply_to_message.parse_entities()
        msgtext = msg.reply_to_message.text or msg.reply_to_message.caption
        if len(args) >= 2 and msg.reply_to_message.text:  # ليس تعليقاً، بل نص
            text, buttons = button_markdown_parser(msgtext,
                                                   entities=entities)
            if buttons:
                data_type = Types.BUTTON_TEXT
            else:
                data_type = Types.TEXT

        elif msg.reply_to_message.sticker:
            content = msg.reply_to_message.sticker.file_id
            data_type = Types.STICKER

        elif msg.reply_to_message.document:
            content = msg.reply_to_message.document.file_id
            text, buttons = button_markdown_parser(msgtext, entities=entities)
            data_type = Types.DOCUMENT

        elif msg.reply_to_message.photo:
            content = msg.reply_to_message.photo[-1].file_id  # آخر عنصر = أفضل جودة
            text, buttons = button_markdown_parser(msgtext, entities=entities)
            data_type = Types.PHOTO

        elif msg.reply_to_message.audio:
            content = msg.reply_to_message.audio.file_id
            text, buttons = button_markdown_parser(msgtext, entities=entities)
            data_type = Types.AUDIO

        elif msg.reply_to_message.voice:
            content = msg.reply_to_message.voice.file_id
            text, buttons = button_markdown_parser(msgtext, entities=entities)
            data_type = Types.VOICE

        elif msg.reply_to_message.video:
            content = msg.reply_to_message.video.file_id
            text, buttons = button_markdown_parser(msgtext, entities=entities)
            data_type = Types.VIDEO

    return note_name, text, data_type, content, buttons


def get_welcome_type(msg: Message):
    """
    تحديد نوع رسالة الترحيب (نص، صورة، إلخ).

    :param msg: رسالة التليجرام
    :return: (النص, نوع_البيانات, المحتوى, الأزرار)
    """
    data_type = None
    content = None
    text = ""

    args = msg.text.split(None, 1)  # استخدام maxsplit لفصل الأمر والوسائط

    buttons = []
    if len(args) >= 2:
        offset = len(args[1]) - len(msg.text)  # ضبط الإزاحة الصحيحة نسبةً للأمر
        text, buttons = button_markdown_parser(args[1], entities=msg.parse_entities(), offset=offset)
        if buttons:
            data_type = Types.BUTTON_TEXT
        else:
            data_type = Types.TEXT

    elif msg.reply_to_message and msg.reply_to_message.sticker:
        content = msg.reply_to_message.sticker.file_id
        text = msg.reply_to_message.caption
        data_type = Types.STICKER

    elif msg.reply_to_message and msg.reply_to_message.document:
        content = msg.reply_to_message.document.file_id
        text = msg.reply_to_message.caption
        data_type = Types.DOCUMENT

    elif msg.reply_to_message and msg.reply_to_message.photo:
        content = msg.reply_to_message.photo[-1].file_id
        text = msg.reply_to_message.caption
        data_type = Types.PHOTO

    elif msg.reply_to_message and msg.reply_to_message.audio:
        content = msg.reply_to_message.audio.file_id
        text = msg.reply_to_message.caption
        data_type = Types.AUDIO

    elif msg.reply_to_message and msg.reply_to_message.voice:
        content = msg.reply_to_message.voice.file_id
        text = msg.reply_to_message.caption
        data_type = Types.VOICE

    elif msg.reply_to_message and msg.reply_to_message.video:
        content = msg.reply_to_message.video.file_id
        text = msg.reply_to_message.caption
        data_type = Types.VIDEO

    return text, data_type, content, buttons
