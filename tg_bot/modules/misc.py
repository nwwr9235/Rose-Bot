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

# ... (ضع هنا جميع الثوابت والدوال الموجودة أصلاً في ملفك: RUN_STRINGS, SLAP_TEMPLATES, ITEMS, THROW, HIT, GMAPS_LOC, GMAPS_TIME، والدوال runs, slap, get_bot_ip, get_id, info, get_time, echo, gdpr, markdown_help, stats, stickerid, getsticker)
# لا تحذف أي شيء من المحتوى الأصلي، فقط أضف ما يلي في نهاية الملف:

# ======================== NEW SHORTCUT FUNCTION =========================
@run_async
def info_shortcut(bot: Bot, update: Update):
    """
    اختصار لعرض معلومات المستخدم عند كتابة حرف 'ا' فقط.
    يستدعي دالة info مع args فارغة.
    """
    info(bot, update, [])
# ========================================================================

# ------------------------ REGISTER HANDLERS -----------------------------

# الأوامر التي نبقيها (غير مُعلّقة):
dispatcher.add_handler(ID_HANDLER)          # /id سيظل يعمل
dispatcher.add_handler(INFO_HANDLER)         # /info سيظل يعمل (يمكنك إزالته إذا أردت)

# الأوامر التي نوقفها (مُعلّقة):
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

# الأمر العربي الجديد: حرف "ا" أو "أ" فقط (مع مسافات قبل أو بعد)
INFO_SHORTCUT_HANDLER = MessageHandler(
    Filters.regex(r'^\s*[اأ]\s*$'),   # يلتقط "ا" أو "أ" محاطة بمسافات اختيارية
    info_shortcut
)
dispatcher.add_handler(INFO_SHORTCUT_HANDLER)
