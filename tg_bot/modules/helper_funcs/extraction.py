from typing import List, Optional

from telegram import Message, MessageEntity
from telegram.error import BadRequest

from tg_bot import LOGGER
from tg_bot.modules.users import get_user_id


def id_from_reply(message):
    """استخراج معرف المستخدم من الرسالة التي تم الرد عليها."""
    prev_message = message.reply_to_message
    if not prev_message:
        return None, None
    user_id = prev_message.from_user.id
    res = message.text.split(None, 1)
    if len(res) < 2:
        return user_id, ""
    return user_id, res[1]


def extract_user(message: Message, args: List[str]) -> Optional[int]:
    """استخراج معرف المستخدم فقط من الرسالة."""
    return extract_user_and_text(message, args)[0]


def extract_user_and_text(message: Message, args: List[str]) -> (Optional[int], Optional[str]):
    """استخراج معرف المستخدم والنص من الرسالة (بعد الأمر)."""
    prev_message = message.reply_to_message
    split_text = message.text.split(None, 1)

    if len(split_text) < 2:
        return id_from_reply(message)  # الخيار الوحيد الممكن

    text_to_parse = split_text[1]

    text = ""

    entities = list(message.parse_entities([MessageEntity.TEXT_MENTION]))
    if len(entities) > 0:
        ent = entities[0]
    else:
        ent = None

    # إذا كان موقع الكيان يتطابق مع نهاية الأمر
    if entities and ent and ent.offset == len(message.text) - len(text_to_parse):
        ent = entities[0]
        user_id = ent.user.id
        text = message.text[ent.offset + ent.length:]

    elif len(args) >= 1 and args[0][0] == '@':
        user = args[0]
        user_id = get_user_id(user)
        if not user_id:
            message.reply_text("ليس لدي هذا المستخدم في قاعدة بياناتي. يمكنك التفاعل معه إذا قمت بالرد على رسالته، أو إعادة توجيه إحدى رسائله.")
            return None, None
        else:
            user_id = user_id
            res = message.text.split(None, 2)
            if len(res) >= 3:
                text = res[2]

    elif len(args) >= 1 and args[0].isdigit():
        user_id = int(args[0])
        res = message.text.split(None, 2)
        if len(res) >= 3:
            text = res[2]

    elif prev_message:
        user_id, text = id_from_reply(message)

    else:
        return None, None

    try:
        message.bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message in ("User_id_invalid", "Chat not found"):
            message.reply_text("لم أجد هذا الشخص في أي مكان... "
                               "أرسل لي شيئاً منه (حتى رسالة) ... "
                               "وبعدها لنبدأ العمل بسرعة...")
        else:
            LOGGER.exception("استثناء %s على المستخدم %s", excp.message, user_id)
        return None, None

    return user_id, text


def extract_text(message) -> str:
    """استخراج النص من الرسالة (نص رئيسي أو تعليق أو إيموجي ملصق)."""
    return message.text or message.caption or (message.sticker.emoji if message.sticker else None)
