import logging
import os
import sys
import time
from logging import StreamHandler

import telegram as tg
from telegram.ext import Application

# دالة بديلة لـ strtobool (لأن distutils أزيل في Python 3.12)
def strtobool(val: str) -> bool:
    """تحويل سلسلة نصية إلى قيمة منطقية (bool)."""
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError(f"Invalid truth value: {val}")

# قم بتعطيل التسجيل إذا كان في وضع الإنتاج
if os.environ.get("DISABLE_LOGGER"):
    pass
else:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=[StreamHandler(sys.stdout)],
    )

LOGGER = logging.getLogger(__name__)

# إذا كنت ترغب في تعطيل بعض أجزاء التسجيل (مثل طلبات urllib3)
# logging.getLogger("httpx").setLevel(logging.WARNING)

ENV = bool(os.environ.get("ENV", False))

if ENV:
    TOKEN = os.environ.get("TOKEN", None)
    try:
        OWNER_ID = int(os.environ.get("OWNER_ID", None))
    except ValueError:
        raise Exception("Your OWNER_ID env variable is not a valid integer.")

    OWNER_USERNAME = os.environ.get("OWNER_USERNAME", None)
    MESSAGE_DUMP = os.environ.get("MESSAGE_DUMP", None)
    try:
        SUDO_USERS = set(int(x) for x in os.environ.get("SUDO_USERS", "").split())
    except ValueError:
        raise Exception("Your sudo users list does not contain valid integers.")

    try:
        SUPPORT_USERS = set(int(x) for x in os.environ.get("SUPPORT_USERS", "").split())
    except ValueError:
        raise Exception("Your support users list does not contain valid integers.")

    try:
        WHITELIST_USERS = set(int(x) for x in os.environ.get("WHITELIST_USERS", "").split())
    except ValueError:
        raise Exception("Your whitelist users list does not contain valid integers.")

    DONATION_LINK = os.environ.get("DONATION_LINK", None)
    CERT_PATH = os.environ.get("CERT_PATH", None)
    PORT = int(os.environ.get("PORT", 8443))
    URL = os.environ.get("URL", None)

    try:
        BAN_STICKER = os.environ.get("BAN_STICKER", "CAADBQADfQADv7rGI0wxx1ORU7UzAg")
    except:
        BAN_STICKER = "CAADBQADfQADv7rGI0wxx1ORU7UzAg"

    ALLOW_EXCL = os.environ.get("ALLOW_EXCL", False)
    if ALLOW_EXCL is not None:
        ALLOW_EXCL = bool(strtobool(str(ALLOW_EXCL)))
    DEL_CMDS = bool(strtobool(os.environ.get("DEL_CMDS", "False")))

    STRICT_GBAN = bool(strtobool(os.environ.get("STRICT_GBAN", "True")))
    try:
        BMERNU_SCUT_SRELFTI = int(os.environ.get("BMERNU_SCUT_SRELFTI", 5))
    except:
        BMERNU_SCUT_SRELFTI = 5

    TEMP_DOWNLOAD_DIRECTORY = os.environ.get("TEMP_DOWNLOAD_DIRECTORY", "./")
else:
    from tg_bot.config import Development as Config

    TOKEN = Config.API_KEY
    OWNER_ID = Config.OWNER_ID
    OWNER_USERNAME = Config.OWNER_USERNAME

    MESSAGE_DUMP = Config.MESSAGE_DUMP
    SUDO_USERS = Config.SUDO_USERS
    SUPPORT_USERS = Config.SUPPORT_USERS
    WHITELIST_USERS = Config.WHITELIST_USERS
    DONATION_LINK = Config.DONATION_LINK
    CERT_PATH = Config.CERT_PATH
    PORT = Config.PORT
    URL = Config.URL
    BAN_STICKER = Config.BAN_STICKER
    ALLOW_EXCL = Config.ALLOW_EXCL
    DEL_CMDS = Config.DEL_CMDS
    STRICT_GBAN = Config.STRICT_GBAN
    BMERNU_SCUT_SRELFTI = Config.BMERNU_SCUT_SRELFTI
    TEMP_DOWNLOAD_DIRECTORY = Config.TEMP_DOWNLOAD_DIRECTORY

# إنشاء التطبيق (بدلاً من updater القديم)
application = Application.builder().token(TOKEN).build()

# متغيرات عامة للاستخدام في الوحدات
dispatcher = application  # للتوافق مع الكود القديم (بعض الوحدات لا تزال تستخدم dispatcher)
updater = application  # أيضاً للتوافق
bot = application.bot

# التحقق من وجود SUDO_USERS إلخ.
if not SUDO_USERS:
    SUGGESTION = "Owners: " + str(OWNER_ID) if OWNER_ID else "None"
    raise Exception("SUDO_USERS variable is missing! Check your config.env file.\n" + SUGGESTION)

# دمج OWNER_ID مع SUDO_USERS
SUDO_USERS.add(OWNER_ID)

# قوائم الصلاحيات
whitelist = WHITELIST_USERS
support = SUPPORT_USERS
sudo = SUDO_USERS

# زخرفة الأرقام (للتسجيل)
TELE_GRAM_ID_S = list(SUDO_USERS) + list(SUPPORT_USERS) + list(WHITELIST_USERS)

# بعض الإعدادات الإضافية
try:
    from telegram import __version__ as pver
except ImportError:
    pver = "Unknown"

LOGGER.info("Successfully loaded config!")
LOGGER.info(f"Python version: {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}")
LOGGER.info(f"python-telegram-bot version: {pver}")
LOGGER.info(f"Users: sudo - {len(SUDO_USERS)} | support - {len(SUPPORT_USERS)} | whitelist - {len(WHITELIST_USERS)}")
