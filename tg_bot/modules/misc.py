import html
import json
import random
from datetime import datetime
from typing import Optional, List

import requests
from telegram import Message, Chat, Update, Bot, MessageEntity
from telegram import ParseMode
from telegram.ext import CommandHandler, run_async, Filters, MessageHandler
from telegram.utils.helpers import escape_markdown, mention_html

from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS, BAN_STICKER
from tg_bot.__main__ import GDPR
from tg_bot.__main__ import STATS, USER_INFO
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.helper_funcs.filters import CustomFilters

# ==================== الثوابت الأصلية ====================
RUN_STRINGS = (
    "Where do you think you're going?",
    # ... باقي النصوص
)

SLAP_TEMPLATES = (
    "{user1} {hits} {user2} with a {item}.",
    # ... باقي القوالب
)

ITEMS = (
    "cast iron skillet",
    # ... باقي العناصر
)

THROW = ("throws", "flings", "chucks", "hurls")
HIT = ("hits", "whacks", "slaps", "smacks", "bashes")

GMAPS_LOC = "https://maps.googleapis.com/maps/api/geocode/json"
GMAPS_TIME = "https://maps.googleapis.com/maps/api/timezone/json"

# ==================== الدوال الأصلية ====================
# (يجب أن تكون جميع الدوال الأصلية موجودة: runs, slap, get_bot_ip, get_id, info, get_time, echo, gdpr, markdown_help, stats, stickerid, getsticker)
# سأضع هنا عناوين فقط للاختصار، لكن يجب نسخ المحتوى الكامل من ملفك الأصلي

@run_async
def runs(bot: Bot, update: Update):
    update.effective_message.reply_text(random.choice(RUN_STRINGS))

@run_async
def slap(bot: Bot, update: Update, args: List[str]):
    # ... الكود الأصلي
    pass

@run_async
def get_bot_ip(bot: Bot, update: Update):
    # ... الكود الأصلي
    pass

@run_async
def get_id(bot: Bot, update: Update, args: List[str]):
    # ... الكود الأصلي
    pass

@run_async
def info(bot: Bot, update: Update, args: List[str]):
    # ... الكود الأصلي
    pass

@run_async
def get_time(bot: Bot, update: Update, args: List[str]):
    # ... الكود الأصلي
    pass

@run_async
def echo(bot: Bot, update: Update):
    # ... الكود الأصلي
    pass

@run_async
def gdpr(bot: Bot, update: Update):
    # ... الكود الأصلي
    pass

@run_async
def markdown_help(bot: Bot, update: Update):
    # ... الكود الأصلي
    pass

@run_async
def stats(bot: Bot, update: Update):
    # ... الكود الأصلي
    pass

@run_async
def stickerid(bot: Bot, update: Update):
    # ... الكود الأصلي
    pass

@run_async
def getsticker(bot: Bot, update: Update):
    # ... الكود الأصلي
    pass

# ==================== الدالة الجديدة ====================
@run_async
def info_shortcut(bot: Bot, update: Update):
    """اختصار لعرض معلومات المستخدم عند كتابة حرف 'ا' فقط."""
    info(bot, update, [])

# ==================== تعريفات المعالجات (HANDLER DEFINITIONS) ====================
# هذه يجب أن تبقى كما هي (غير مُعلَّقة)
ID_HANDLER = DisableAbleCommandHandler("id", get_id, pass_args=True)
INFO_HANDLER = DisableAbleCommandHandler("info", info, pass_args=True)
IP_HANDLER = CommandHandler("ip", get_bot_ip, filters=Filters.chat(OWNER_ID))
TIME_HANDLER = CommandHandler("time", get_time, pass_args=True)
RUNS_HANDLER = DisableAbleCommandHandler("runs", runs)
SLAP_HANDLER = DisableAbleCommandHandler("slap", slap, pass_args=True)
ECHO_HANDLER = CommandHandler("echo", echo, filters=Filters.user(OWNER_ID))
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help, filters=Filters.private)
STATS_HANDLER = CommandHandler("stats", stats, filters=CustomFilters.sudo_filter)
GDPR_HANDLER = CommandHandler("gdpr", gdpr, filters=Filters.private)
STICKERID_HANDLER = DisableAbleCommandHandler("stickerid", stickerid)
GETSTICKER_HANDLER = DisableAbleCommandHandler("getsticker", getsticker)

# ==================== تسجيل المعالجات ====================
# الأوامر التي نريد إبقاءها نشطة:
dispatcher.add_handler(ID_HANDLER)      # /id
dispatcher.add_handler(INFO_HANDLER)    # /info

# الأوامر التي نريد تعطيلها (معلَّقة):
# dispatcher.add_handler(IP_HANDLER)
# dispatcher.add_handler(TIME_HANDLER)
# dispatcher.add_handler(RUNS_HANDLER)
# dispatcher.add_handler(SLAP_HANDLER)
# dispatcher.add_handler(ECHO_HANDLER)
# dispatcher.add_handler(MD_HELP_HANDLER)
# dispatcher.add_handler(STATS_HANDLER)
# dispatcher.add_handler(GDPR_HANDLER)
# dispatcher.add_handler(STICKERID_HANDLER)
# dispatcher.add_handler(GETSTICKER_HANDLER)

# الأمر العربي الجديد:
INFO_SHORTCUT_HANDLER = MessageHandler(
    Filters.regex(r'^\s*[اأ]\s*$'),
    info_shortcut
)
dispatcher.add_handler(INFO_SHORTCUT_HANDLER)
