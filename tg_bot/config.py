import os

class Config(object):
    LOGGER = True

    # REQUIRED
    API_KEY = os.environ.get("BOT_TOKEN", "")
    OWNER_ID = int(os.environ.get("OWNER_ID", 0))
    OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "")

    # RECOMMENDED
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "")
    MESSAGE_DUMP = os.environ.get("MESSAGE_DUMP", "")
    LOAD = os.environ.get("LOAD", "").split()
    NO_LOAD = os.environ.get("NO_LOAD", "translation rss").split()
    WEBHOOK = os.environ.get("WEBHOOK", "False").lower() == "true"
    URL = os.environ.get("URL", None)

    # OPTIONAL
    SUDO_USERS = [int(x) for x in os.environ.get("SUDO_USERS", "").split() if x.isdigit()]
    SUPPORT_USERS = [int(x) for x in os.environ.get("SUPPORT_USERS", "").split() if x.isdigit()]
    WHITELIST_USERS = [int(x) for x in os.environ.get("WHITELIST_USERS", "").split() if x.isdigit()]
    DONATION_LINK = os.environ.get("DONATION_LINK", None)
    CERT_PATH = os.environ.get("CERT_PATH", None)
    PORT = int(os.environ.get("PORT", 5000))
    DEL_CMDS = os.environ.get("DEL_CMDS", "False").lower() == "true"
    STRICT_GBAN = os.environ.get("STRICT_GBAN", "False").lower() == "true"
    WORKERS = int(os.environ.get("WORKERS", 8))
    BAN_STICKER = os.environ.get("BAN_STICKER", 'CAADAgADOwADPPEcAXkko5EB3YGYAg')
    ALLOW_EXCL = os.environ.get("ALLOW_EXCL", "False").lower() == "true"
    BMERNU_SCUT_SRELFTI = int(os.environ.get("BMERNU_SCUT_SRELFTI", 0))


class Production(Config):
    LOGGER = False


class Development(Config):
    LOGGER = True
