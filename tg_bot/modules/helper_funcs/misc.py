from math import ceil
from typing import Dict, List, Optional
from html import escape

from telegram import InlineKeyboardButton, Bot, Update
from telegram.constants import MessageLimit, ParseMode  # الاستيراد الصحيح

from tg_bot import LOGGER, SUDO_USERS, OWNER_ID

class EqInlineKeyboardButton(InlineKeyboardButton):
    def __eq__(self, other):
        return self.text == other.text

    def __lt__(self, other):
        return self.text < other.text

    def __gt__(self, other):
        return self.text > other.text

def split_list_into_chunks(lst: List, chunk_size: int) -> List[List]:
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def paginate_modules(page_n: int, module_dict: Dict, prefix, chat=None) -> List[List[InlineKeyboardButton]]:
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
    keyb = []
    for btn in buttons:
        if btn["same_line"] and keyb:
            keyb[-1].append(InlineKeyboardButton(btn["name"], url=btn["url"]))
        else:
            keyb.append([InlineKeyboardButton(btn["name"], url=btn["url"])])
    return keyb

def revert_buttons(buttons: List) -> str:
    res = ""
    for btn in buttons:
        if btn["same_line"]:
            res += "\n[{}](buttonurl://{}:same)".format(btn["name"], btn["url"])
        else:
            res += "\n[{}](buttonurl://{})".format(btn["name"], btn["url"])
    return res

def is_module_loaded(name: str) -> bool:
    return name in list(LOGGER.manager.loggerDict.keys())

async def send_to_list(bot: Bot, send_to: list, message: str, markdown=False, html=False) -> None:
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
    return None

def escape_mentions_using_eggs(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
