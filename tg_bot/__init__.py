import logging
import os
import sys
from logging import StreamHandler

import telegram as tg
from telegram.ext import Application

# دالة بديلة لـ strtobool (لأن distutils أزيل في Python 3.12)
def strtobool(val: str) -> bool:
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError(f"Invalid truth value: {val}")

# تهيئة التسجيل
if not os.environ.get("DISABLE_LOGGER"):
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=[StreamHandler(sys.stdout)],
    )

LOGGER = logging.getLogger(__name__)

ENV = bool(os.environ.get("ENV", False))

# قيم افتراضية
TOKEN = None
OWNER_ID = 0
OWNER_USERNAME = ""
MESSAGE_DUMP = None
SUDO_USERS = set()
SUPPORT_USERS = set()
WHITELIST_USERS = set()
DONATION_LINK = None
CERT_PATH = None
PORT = 8443
URL = None
WEBHOOK = False
BAN_STICKER = "CAADBQADfQADv7rGI0wxx1ORU7UzAg"
ALLOW_EXCL = False
DEL_CMDS = False
STRICT_GBAN = True
BMERNU_SCUT_SRELFTI = 5
TEMP_DOWNLOAD_DIRECTORY = "./"
LOAD = []
NO_LOAD = []

if ENV:
    TOKEN = os.environ.get("TOKEN")
    if not TOKEN:
        LOGGER.error("TOKEN environment variable not set!")
        sys.exit(1)

    try:
        OWNER_ID = int(os.environ.get("OWNER_ID", 0))
    except ValueError:
        LOGGER.error("OWNER_ID must be an integer!")
        sys.exit(1)

    OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "")
    MESSAGE_DUMP = os.environ.get("MESSAGE_DUMP")

    try:
        SUDO_USERS = set(int(x) for x in os.environ.get("SUDO_USERS", "").split() if x)
    except ValueError:
        LOGGER.error("SUDO_USERS contains non-integer values!")
        sys.exit(1)

    try:
        SUPPORT_USERS = set(int(x) for x in os.environ.get("SUPPORT_USERS", "").split() if x)
    except ValueError:
        LOGGER.error("SUPPORT_USERS contains non-integer values!")
        sys.exit(1)

    try:
        WHITELIST_USERS = set(int(x) for x in os.environ.get("WHITELIST_USERS", "").split() if x)
    except ValueError:
        LOGGER.error("WHITELIST_USERS contains non-integer values!")
        sys.exit(1)

    DONATION_LINK = os.environ.get("DONATION_LINK")
    CERT_PATH = os.environ.get("CERT_PATH")
    PORT = int(os.environ.get("PORT", 8443))
    URL = os.environ.get("URL")

    WEBHOOK = strtobool(os.environ.get("WEBHOOK", "False"))
    BAN_STICKER = os.environ.get("BAN_STICKER", "CAADBQADfQADv7rGI0wxx1ORU7UzAg")
    ALLOW_EXCL = strtobool(os.environ.get("ALLOW_EXCL", "False"))
    DEL_CMDS = strtobool(os.environ.get("DEL_CMDS", "False"))
    STRICT_GBAN = strtobool(os.environ.get("STRICT_GBAN", "True"))

    try:
        BMERNU_SCUT_SRELFTI = int(os.environ.get("BMERNU_SCUT_SRELFTI", 5))
    except ValueError:
        BMERNU_SCUT_SRELFTI = 5

    TEMP_DOWNLOAD_DIRECTORY = os.environ.get("TEMP_DOWNLOAD_DIRECTORY", "./")
    LOAD = os.environ.get("LOAD", "").split()
    NO_LOAD = os.environ.get("NO_LOAD", "").split()
else:
    try:
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
        WEBHOOK = getattr(Config, 'WEBHOOK', False)
        BAN_STICKER = Config.BAN_STICKER
        ALLOW_EXCL = Config.ALLOW_EXCL
        DEL_CMDS = Config.DEL_CMDS
        STRICT_GBAN = Config.STRICT_GBAN
        BMERNU_SCUT_SRELFTI = Config.BMERNU_SCUT_SRELFTI
        TEMP_DOWNLOAD_DIRECTORY = Config.TEMP_DOWNLOAD_DIRECTORY
        LOAD = getattr(Config, 'LOAD', [])
        NO_LOAD = getattr(Config, 'NO_LOAD', [])
    except ImportError:
        LOGGER.error("Config file not found and ENV not set!")
        sys.exit(1)

# التأكد من وجود TOKEN
if not TOKEN:
    LOGGER.error("TOKEN not configured!")
    sys.exit(1)

# إنشاء التطبيق
application = Application.builder().token(TOKEN).build()

# متغيرات للتوافق
dispatcher = application
updater = application
bot = application.bot

# دمج OWNER_ID مع SUDO_USERS (إذا كان OWNER_ID معرفاً)
if OWNER_ID:
    SUDO_USERS.add(OWNER_ID)

# قوائم الصلاحيات
whitelist = WHITELIST_USERS
support = SUPPORT_USERS
sudo = SUDO_USERS

# قائمة معرفات للمساعدة
TELE_GRAM_ID_S = list(SUDO_USERS) + list(SUPPORT_USERS) + list(WHITELIST_USERS)

# معلومات الإصدار
try:
    from telegram import __version__ as pver
except ImportError:
    pver = "Unknown"

LOGGER.info("Successfully loaded config!")
LOGGER.info(f"Python version: {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}")
LOGGER.info(f"python-telegram-bot version: {pver}")
LOGGER.info(f"Users: sudo - {len(SUDO_USERS)} | support - {len(SUPPORT_USERS)} | whitelist - {len(WHITELIST_USERS)}")
if LOAD:
    LOGGER.info(f"Loading modules: {LOAD}")
if NO_LOAD:
    LOGGER.info(f"Not loading modules: {NO_LOAD}")
