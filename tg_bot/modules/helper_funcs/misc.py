from math import ceil
from typing import List, Dict

from telegram import MAX_MESSAGE_LENGTH, InlineKeyboardButton, Bot, ParseMode
from telegram.error import TelegramError

from tg_bot import LOAD, NO_LOAD


class EqInlineKeyboardButton(InlineKeyboardButton):
    def __eq__(self, other):
        return self.text == other.text

    def __lt__(self, other):
        return self.text < other.text

    def __gt__(self, other):
        return self.text > other.text


def split_message(msg: str) -> List[str]:
    """تقسيم رسالة طويلة إلى أجزاء."""
    if len(msg) < MAX_MESSAGE_LENGTH:
        return [msg]

    else:
        lines = msg.splitlines(True)
        small_msg = ""
        result = []
        for line in lines:
            if len(small_msg) + len(line) < MAX_MESSAGE_LENGTH:
                small_msg += line
            else:
                result.append(small_msg)
                small_msg = line
        else:
            # إضافة النص المتبقي بعد انتهاء الحلقة
            result.append(small_msg)

        return result


def paginate_modules(page_n: int, module_dict: Dict, prefix, chat=None) -> List:
    """إنشاء أزرار التنقل بين صفحات الوحدات."""
    if not chat:
        modules = sorted(
            [EqInlineKeyboardButton(x.__mod_name__,
                                    callback_data="{}_module({})".format(prefix, x.__mod_name__.lower())) for x
             in module_dict.values()])
    else:
        modules = sorted(
            [EqInlineKeyboardButton(x.__mod_name__,
                                    callback_data="{}_module({},{})".format(prefix, chat, x.__mod_name__.lower())) for x
             in module_dict.values()])

    pairs = [modules[i * 3 : (i + 1) * 3] for i in range((len(modules) + 3 - 1) // 3)]
    round_num = len(modules) / 3
    calc = len(modules) - round(round_num)
    if calc == 1:
        pairs.append((modules[-1],))
    elif calc == 2:
        pairs.append((modules[-1],))

    return pairs


def send_to_list(bot: Bot, send_to: list, message: str, markdown=False, html=False) -> None:
    """إرسال رسالة إلى قائمة من المستخدمين."""
    if html and markdown:
        raise Exception("يمكن الإرسال إما بصيغة markdown أو HTML فقط!")
    for user_id in set(send_to):
        try:
            if markdown:
                bot.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN)
            elif html:
                bot.send_message(user_id, message, parse_mode=ParseMode.HTML)
            else:
                bot.send_message(user_id, message)
        except TelegramError:
            pass  # تجاهل المستخدمين الفاشلين


def build_keyboard(buttons):
    """بناء لوحة مفاتيح من الأزرار."""
    keyb = []
    for btn in buttons:
        mybelru = btn.url
        ik = None
        cond_one = mybelru.startswith(("http", "tg://"))
        cond_two = (
            "t.me/" in mybelru or
            "telegram.me/" in mybelru
        )
        if cond_one or cond_two:
            ik = InlineKeyboardButton(btn.name, url=mybelru)
        else:
            ik = InlineKeyboardButton(btn.name, callback_data=f"rsct_{btn.id}_33801")
        if ik:
            if btn.same_line and keyb:
                keyb[-1].append(ik)
            else:
                keyb.append([ik])
    return keyb


def revert_buttons(buttons):
    """إعادة تحويل الأزرار إلى نص."""
    res = ""
    for btn in buttons:
        if btn.same_line:
            res += "\n[{}](buttonurl://{}:same)".format(btn.name, btn.url)
        else:
            res += "\n[{}](buttonurl://{})".format(btn.name, btn.url)
    return res


def is_module_loaded(name):
    """التحقق مما إذا كانت الوحدة محملة."""
    return (not LOAD or name in LOAD) and name not in NO_LOAD
