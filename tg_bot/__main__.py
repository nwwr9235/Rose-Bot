import importlib
import re
import logging
from typing import Optional, List

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telegram.error import (
    Unauthorized,
    BadRequest,
    TimedOut,
    NetworkError,
    ChatMigrated,
    TelegramError,
)

from tg_bot import TOKEN, WEBHOOK, OWNER_ID, DONATION_LINK, CERT_PATH, PORT, URL, LOGGER, ALLOW_EXCL
from tg_bot.modules import ALL_MODULES
from tg_bot.modules.helper_funcs.chat_status import is_user_admin
from tg_bot.modules.helper_funcs.misc import paginate_modules

# =================== المتغيرات العامة ===================
IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
DATA_IMPORT = []
DATA_EXPORT = []
CHAT_SETTINGS = {}
USER_SETTINGS = {}
GDPR = []

# =================== تحميل جميع الوحدات ===================
for module_name in ALL_MODULES:
    imported_module = importlib.import_module("tg_bot.modules." + module_name)
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if imported_module.__mod_name__.lower() not in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception("لا يمكن وجود وحدتين بنفس الاسم! الرجاء تغيير إحداهما")

    if hasattr(imported_module, "__help__") and imported_module.__help__:
        HELPABLE[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__migrate__"):
        MIGRATEABLE.append(imported_module)

    if hasattr(imported_module, "__stats__"):
        STATS.append(imported_module)

    if hasattr(imported_module, "__gdpr__"):
        GDPR.append(imported_module)

    if hasattr(imported_module, "__user_info__"):
        USER_INFO.append(imported_module)

    if hasattr(imported_module, "__import_data__"):
        DATA_IMPORT.append(imported_module)

    if hasattr(imported_module, "__export_data__"):
        DATA_EXPORT.append(imported_module)

    if hasattr(imported_module, "__chat_settings__"):
        CHAT_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__user_settings__"):
        USER_SETTINGS[imported_module.__mod_name__.lower()] = imported_module


# =================== نصوص البوت (عربية) ===================
PM_START_TEXT = """
مرحباً {}! أنا اسمي {}! أنا بوت إدارة متطور.
تم إنشائي باستخدام Python و python-telegram-bot.
لمعرفة الأوامر المتاحة، استخدم /help.
"""

HELP_STRINGS = """
أهلاً! اسمي *{}*.
أنا بوت إدارة متكامل للمجموعات مع بعض الميزات الإضافية.
*الأوامر الرئيسية:*
- /start: بدء البوت
- /help: عرض هذه المساعدة في الخاص
- /help <اسم الوحدة>: عرض مساعدة وحدة معينة
- /settings: إعداداتك (في الخاص) أو إعدادات المجموعة (في المجموعة)
{}
والوحدات التالية:
""".format("", "" if not ALLOW_EXCL else "\nيمكن استخدام الأوامر بـ / أو !\n")

DONATE_STRING = """إذا أردت دعم المطور، يمكنك التبرع عبر الرابط: {}""".format(DONATION_LINK if DONATION_LINK else "لا يوجد رابط تبرع حالياً.")


# =================== دوال مساعدة (غير متزامنة) ===================
async def send_help(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    keyboard: InlineKeyboardMarkup = None,
):
    """إرسال رسالة المساعدة."""
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


async def send_settings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
    user: bool = False,
):
    """إرسال إعدادات المستخدم أو المجموعة."""
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                f"*{mod.__mod_name__}*:\n{mod.__user_settings__(user_id)}"
                for mod in USER_SETTINGS.values()
            )
            await context.bot.send_message(
                user_id,
                "إعداداتك الحالية:\n\n" + settings,
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await context.bot.send_message(
                user_id,
                "لا توجد إعدادات خاصة بالمستخدم حالياً.",
                parse_mode=ParseMode.MARKDOWN,
            )
    else:
        if CHAT_SETTINGS:
            chat = await context.bot.get_chat(chat_id)
            await context.bot.send_message(
                user_id,
                f"اختر الوحدة التي تريد عرض إعداداتها لمجموعة {chat.title}:",
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )
        else:
            await context.bot.send_message(
                user_id,
                "لا توجد إعدادات للمجموعة حالياً.",
                parse_mode=ParseMode.MARKDOWN,
            )


# =================== معالجات الأوامر (غير متزامنة) ===================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start."""
    if update.effective_chat.type == "private":
        args = context.args
        if args:
            if args[0].lower() == "help":
                await send_help(update, context, update.effective_chat.id, HELP_STRINGS)
            elif args[0].lower().startswith("stngs_"):
                match = re.match(r"stngs_(.*)", args[0].lower())
                if match:
                    chat_id = match.group(1)
                    chat = await context.bot.get_chat(chat_id)
                    if await is_user_admin(chat, update.effective_user.id):
                        await send_settings(
                            update, context, int(chat_id), update.effective_user.id, user=False
                        )
                    else:
                        await send_settings(
                            update, context, int(chat_id), update.effective_user.id, user=True
                        )
            elif args[0][1:].isdigit() and "rules" in HELPABLE:
                await IMPORTED["rules"].send_rules(update, args[0], from_pm=True)
        else:
            first_name = update.effective_user.first_name
            bot_username = context.bot.username
            await update.message.reply_text(
                PM_START_TEXT.format(first_name, context.bot.first_name, OWNER_ID),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="➕ أضفني إلى مجموعتك",
                                url=f"t.me/{bot_username}?startgroup=true",
                            ),
                            InlineKeyboardButton(
                                text="🤖 اصنع بوتك الخاص",
                                url="https://youtu.be/W6CLKrehy6w",
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                text="👥 مجموعة الدعم",
                                url="https://t.me/Mo_Tech_Group",
                            ),
                            InlineKeyboardButton(
                                text="🔔 قناة التحديثات",
                                url="https://t.me/Mo_Tech_YT",
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                text="👨‍💻 الشرح",
                                url="https://youtu.be/wKL90i3cjPw",
                            ),
                            InlineKeyboardButton(
                                text="🛠 المساعدة",
                                url=f"t.me/{bot_username}?start=help",
                            ),
                        ],
                    ]
                ),
            )
    else:
        await update.message.reply_text("البوت يعمل!")


async def help_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار المساعدة."""
    query = update.callback_query
    await query.answer()
    data = query.data
    mod_match = re.match(r"help_module\((.+?)\)", data)
    prev_match = re.match(r"help_prev\((.+?)\)", data)
    next_match = re.match(r"help_next\((.+?)\)", data)
    back_match = re.match(r"help_back", data)

    try:
        if mod_match:
            module_name = mod_match.group(1)
            module = HELPABLE[module_name]
            text = f"*وحدة {module.__mod_name__}*:\n\n{module.__help__}"
            await query.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text="🔙 رجوع", callback_data="help_back")]]
                ),
            )
            await query.message.delete()
        elif prev_match:
            curr_page = int(prev_match.group(1))
            await query.message.reply_text(
                HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(curr_page - 1, HELPABLE, "help")
                ),
            )
            await query.message.delete()
        elif next_match:
            next_page = int(next_match.group(1))
            await query.message.reply_text(
                HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(next_page + 1, HELPABLE, "help")
                ),
            )
            await query.message.delete()
        elif back_match:
            await query.message.reply_text(
                HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, HELPABLE, "help")
                ),
            )
            await query.message.delete()
    except BadRequest as e:
        if e.message not in ("Message is not modified", "Query_id_invalid", "Message can't be deleted"):
            LOGGER.exception("Exception in help buttons: %s", str(query.data))


async def get_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /help."""
    chat = update.effective_chat
    if chat.type != "private":
        await update.message.reply_text(
            "لرؤية قائمة الأوامر، تواصل معي في الخاص.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="المساعدة",
                            url=f"t.me/{context.bot.username}?start=help",
                        )
                    ]
                ]
            ),
        )
        return

    args = context.args
    if args and args[0].lower() in HELPABLE:
        module_name = args[0].lower()
        module = HELPABLE[module_name]
        text = f"*وحدة {module.__mod_name__}*:\n\n{module.__help__}"
        await send_help(
            update,
            context,
            chat.id,
            text,
            InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="🔙 رجوع", callback_data="help_back")]]
            ),
        )
    else:
        await send_help(update, context, chat.id, HELP_STRINGS)


async def settings_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار الإعدادات."""
    query = update.callback_query
    await query.answer()
    data = query.data
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", data)
    back_match = re.match(r"stngs_back\((.+?)\)", data)

    try:
        if mod_match:
            chat_id = int(mod_match.group(1))
            module_name = mod_match.group(2)
            chat = await context.bot.get_chat(chat_id)
            module = CHAT_SETTINGS[module_name]
            # محاولة استدعاء __chat_settings__ (قد تكون متزامنة أو غير متزامنة)
            if hasattr(module.__chat_settings__, "__call__") and not hasattr(module.__chat_settings__, "func"):
                settings_text = await module.__chat_settings__(chat_id, update.effective_user.id)
            else:
                settings_text = module.__chat_settings__(chat_id, update.effective_user.id)

            text = f"*إعدادات مجموعة {chat.title} لوحدة {module.__mod_name__}*:\n\n{settings_text}"
            await query.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="🔙 رجوع",
                                callback_data=f"stngs_back({chat_id})",
                            )
                        ]
                    ]
                ),
            )
            await query.message.delete()
        elif prev_match:
            chat_id = int(prev_match.group(1))
            curr_page = int(prev_match.group(2))
            chat = await context.bot.get_chat(chat_id)
            await query.message.reply_text(
                f"إليك إعدادات {chat.title} - اختر الوحدة:",
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(curr_page - 1, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )
            await query.message.delete()
        elif next_match:
            chat_id = int(next_match.group(1))
            next_page = int(next_match.group(2))
            chat = await context.bot.get_chat(chat_id)
            await query.message.reply_text(
                f"إليك إعدادات {chat.title} - اختر الوحدة:",
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(next_page + 1, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )
            await query.message.delete()
        elif back_match:
            chat_id = int(back_match.group(1))
            chat = await context.bot.get_chat(chat_id)
            await query.message.reply_text(
                f"إليك إعدادات {chat.title} - اختر الوحدة:",
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )
            await query.message.delete()
    except BadRequest as e:
        if e.message not in ("Message is not modified", "Query_id_invalid", "Message can't be deleted"):
            LOGGER.exception("Exception in settings buttons: %s", str(query.data))


async def get_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /settings."""
    chat = update.effective_chat
    user = update.effective_user
    if chat.type != "private":
        if await is_user_admin(chat, user.id):
            text = "اضغط هنا لرؤية إعدادات هذه المجموعة."
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="الإعدادات",
                                url=f"t.me/{context.bot.username}?start=stngs_{chat.id}",
                            )
                        ]
                    ]
                ),
            )
        else:
            text = "اضغط هنا لرؤية إعداداتك الشخصية."
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="إعداداتي",
                                url=f"t.me/{context.bot.username}?start=stngs_{chat.id}",
                            )
                        ]
                    ]
                ),
            )
    else:
        await send_settings(update, context, chat.id, user.id, user=True)


async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /donate."""
    chat = update.effective_chat
    if chat.type == "private":
        await update.message.reply_text(
            DONATE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )
    else:
        try:
            await context.bot.send_message(
                update.effective_user.id,
                DONATE_STRING,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
            await update.message.reply_text("لقد أرسلت لك معلومات التبرع في الخاص.")
        except Unauthorized:
            await update.message.reply_text("تواصل معي في الخاص أولاً لرؤية معلومات التبرع.")


async def migrate_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج ترحيل المجموعات عند الترقية إلى supergroup."""
    message = update.effective_message
    if message.migrate_to_chat_id:
        old_chat = update.effective_chat.id
        new_chat = message.migrate_to_chat_id
    elif message.migrate_from_chat_id:
        old_chat = message.migrate_from_chat_id
        new_chat = update.effective_chat.id
    else:
        return

    LOGGER.info("Migrating from %s to %s", old_chat, new_chat)
    for mod in MIGRATEABLE:
        if hasattr(mod, "__migrate__"):
            mod.__migrate__(old_chat, new_chat)
    LOGGER.info("Migration successful.")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأخطاء العام."""
    LOGGER.error("Exception while handling an update:", exc_info=context.error)


# =================== الدالة الرئيسية ===================
def main() -> None:
    """تشغيل البوت."""
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()

    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", get_help))
    application.add_handler(CommandHandler("settings", get_settings))
    application.add_handler(CommandHandler("donate", donate))
    application.add_handler(CallbackQueryHandler(help_button, pattern=r"^help_"))
    application.add_handler(CallbackQueryHandler(settings_button, pattern=r"^stngs_"))
    application.add_handler(MessageHandler(filters.StatusUpdate.MIGRATE, migrate_chats))

    # إضافة معالج الأخطاء
    application.add_error_handler(error_handler)

    # تشغيل البوت
    if WEBHOOK:
        LOGGER.info("Using webhooks.")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=URL + TOKEN,
            cert=CERT_PATH or None,
        )
    else:
        LOGGER.info("Using long polling.")
        application.run_polling()


if __name__ == "__main__":
    LOGGER.info("Successfully loaded modules: %s", str(ALL_MODULES))
    main()
