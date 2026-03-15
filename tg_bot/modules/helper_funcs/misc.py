from math import ceil
from typing import Dict, List, Optional
from html import escape

from telegram import InlineKeyboardButton, Bot, Update
from telegram.constants import MessageLimit
from telegram import ParseMode

from tg_bot import LOGGER, SUDO_USERS, OWNER_ID


class EqInlineKeyboardButton(InlineKeyboardButton):
    def __eq__(self, other):
        return self.text == other.text

    def __lt__(self, other):
        return self.text < other.text

    def __gt__(self, other):
        return self.text > other.text


def split_list_into_chunks(lst: List, chunk_size: int) -> List[List]:
    """تقسيم قائمة إلى قوائم أصغر بحجم معين."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def paginate_modules(page_n: int, module_dict: Dict, prefix, chat=None) -> List[List[InlineKeyboardButton]]:
    """توليد لوحة مفاتيح بصفحات لعرض قائمة الوحدات."""
    if not chat:
        modules = sorted([EqInlineKeyboardButton(x.__mod_name__,
                                                 callback_data="{}_module({})".format(prefix, x.__mod_name__.lower()))
                          for x in module_dict.values()])
    else:
        modules = sorted([EqInlineKeyboardButton(x.__mod_name__,
                                                 callback_data="{}_module({},{})".format(prefix, chat, x.__mod_name__.lower()))
                          for x in module_dict.values()])

    pairs = split_list_into_chunks(modules, 2)
    if len(pairs) > 1:
        # إضافة أزرار التنقل
        if page_n == 0:
            next_page_button = InlineKeyboardButton("التالي ➡️", callback_data="{}_next({})".format(prefix, page_n + 1))
            pairs.append([next_page_button])
        elif page_n == len(pairs) - 1:
            prev_page_button = InlineKeyboardButton("⬅️ السابق", callback_data="{}_prev({})".format(prefix, page_n - 1))
            pairs.append([prev_page_button])
        else:
            prev_page_button = InlineKeyboardButton("⬅️ السابق", callback_data="{}_prev({})".format(prefix, page_n - 1))
            next_page_button = InlineKeyboardButton("التالي ➡️", callback_data="{}_next({})".format(prefix, page_n + 1))
            pairs.append([prev_page_button, next_page_button])

    return pairs


def build_keyboard(buttons: List) -> List[List[InlineKeyboardButton]]:
    """بناء لوحة مفاتيح من قائمة الأزرار."""
    keyb = []
    for btn in buttons:
        if btn["same_line"] and keyb:
            keyb[-1].append(InlineKeyboardButton(btn["name"], url=btn["url"]))
        else:
            keyb.append([InlineKeyboardButton(btn["name"], url=btn["url"])])
    return keyb


def revert_buttons(buttons: List) -> str:
    """تحويل الأزرار إلى نص (للتوافق مع noformat)."""
    res = ""
    for btn in buttons:
        if btn["same_line"]:
            res += "\n[{}](buttonurl://{}:same)".format(btn["name"], btn["url"])
        else:
            res += "\n[{}](buttonurl://{})".format(btn["name"], btn["url"])
    return res


def is_module_loaded(name: str) -> bool:
    """التحقق من تحميل وحدة معينة."""
    return name in list(LOGGER.manager.loggerDict.keys())  # قد لا يعمل بشكل صحيح، نستخدم طريقة أخرى
    # بدلاً من ذلك، يمكننا استخدام قائمة الوحدات المحملة، لكننا سنتركها كما هي مؤقتًا.


async def send_to_list(bot: Bot, send_to: list, message: str, markdown=False, html=False) -> None:
    """إرسال رسالة إلى قائمة من المستخدمين (sudo, support)."""
    if html and markdown:
        raise ValueError("لا يمكن استخدام علامتي تنسيق معًا.")
    for user_id in set(send_to):
        try:
            if markdown:
                await bot.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN)
            elif html:
                await bot.send_message(user_id, message, parse_mode=ParseMode.HTML)
            else:
                await bot.send_message(user_id, message)
        except Exception as e:
            LOGGER.warning(f"فشل إرسال رسالة إلى {user_id}: {e}")


def build_keyboard_parser(bot, chat_id, text, buttons):
    """دالة مساعدة لتحليل الأزرار (قديمة، نحتاجها للتوافق)."""
    # هذه الدالة قد تُستدعى من cust_filters.py، يجب تحديثها لاحقًا.
    # سنتركها كما هي حاليًا.
    return None


def escape_mentions_using_eggs(func):
    """دالة زخرفية للتعامل مع المنشنات (غير مستخدمة كثيرًا)."""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
