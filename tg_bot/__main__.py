import importlib
import re
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import Unauthorized, BadRequest, TimedOut, NetworkError, ChatMigrated, TelegramError
from telegram.ext import CommandHandler, Filters, MessageHandler, CallbackQueryHandler
from telegram.ext.dispatcher import run_async, DispatcherHandlerStop
from telegram.utils.helpers import escape_markdown

from tg_bot import dispatcher, updater, TOKEN, WEBHOOK, OWNER_ID, DONATION_LINK, CERT_PATH, PORT, URL, LOGGER, \
    ALLOW_EXCL
# needed to dynamically load modules
# NOTE: Module order is not guaranteed, specify that in the config file!
from tg_bot.modules import ALL_MODULES
from tg_bot.modules.helper_funcs.chat_status import is_user_admin
from tg_bot.modules.helper_funcs.misc import paginate_modules

PM_START_TEXT = """
مرحباً {}، اسمي {}! أنا بوت إدارة مجموعات متكامل مع بعض الإضافات الممتعة!

تم بنائي باستخدام Python3 ومكتبة python-telegram-bot. أنا مفتوح المصدر بالكامل.

لمشاهدة فيديو عن كيفية إنشاء بوت إدارة مثلي، شاهد الفيديو أدناه.

اشترك في قناة التحديثات لتعرف كل جديد عن عملي.

ولا تنس الاشتراك في قناة Tech Gaming على يوتيوب.

للاطلاع على الأوامر المتاحة، اضغط /help.
"""

HELP_STRINGS = """
مرحباً! اسمي *{}*.
أنا بوت إدارة مجموعات متكامل مع بعض الإضافات الممتعة! إليك فكرة عن بعض الأشياء التي يمكنني مساعدتك بها.

*الأوامر الرئيسية المتاحة:*
- /start: تشغيل البوت
- /help: سأرسل لك هذه الرسالة في الخاص.
- /help <اسم الوحدة>: سأرسل لك معلومات عن تلك الوحدة في الخاص.
- /donate: معلومات عن كيفية التبرع!
- /settings:
   - في الخاص: سأرسل لك إعداداتك لجميع الوحدات المدعومة.
   - في مجموعة: سأوجهك إلى الخاص، مع جميع إعدادات تلك الدردشة.
{}
وما يلي:
""".format(dispatcher.bot.first_name, "" if not ALLOW_EXCL else "\nيمكن استخدام جميع الأوامر إما بـ / أو !.\n")

DONATE_STRING = """مرحباً، يسعدني سماع أنك تريد التبرع!
لقد تطلب الأمر الكثير من العمل من [منشئي](t.me/SonOfLars) للوصول بي إلى ما أنا عليه الآن، وكل تبرع يساعده على تحسيني أكثر. ستذهب أموال التبرع إلى خادم أفضل لاستضافتي، و/أو إلى البيرة (انظر سيرته الذاتية!). إنه مجرد طالب فقير، لذا فكل القليل يساعد!
هناك طريقتان للتبرع له: [PayPal](paypal.me/PaulSonOfLars)، أو [Monzo](monzo.me/paulnionvestergaardlarsen)."""

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

for module_name in ALL_MODULES:
    imported_module = importlib.import_module("tg_bot.modules." + module_name)
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if not imported_module.__mod_name__.lower() in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception("لا يمكن أن يكون هناك وحدتان بنفس الاسم! الرجاء تغيير إحداهما")

    if hasattr(imported_module, "__help__") and imported_module.__help__:
        HELPABLE[imported_module.__mod_name__.lower()] = imported_module

    # Chats to migrate on chat_migrated events
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


# do not async
def send_help(chat_id, text, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    dispatcher.bot.send_message(chat_id=chat_id,
                                text=text,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=keyboard)


@run_async
def test(bot: Bot, update: Update):
    update.effective_message.reply_text("هذا الشخص عدل رسالة")
    print(update.effective_message)


@run_async
def start(bot: Bot, update: Update, args: List[str]):
    if update.effective_chat.type == "private":
        if len(args) >= 1:
            if args[0].lower() == "help":
                send_help(update.effective_chat.id, HELP_STRINGS)

            elif args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", args[0].lower())
                chat = dispatcher.bot.getChat(match.group(1))

                if is_user_admin(chat, update.effective_user.id):
                    send_settings(match.group(1), update.effective_user.id, False)
                else:
                    send_settings(match.group(1), update.effective_user.id, True)

            elif args[0][1:].isdigit() and "rules" in IMPORTED:
                IMPORTED["rules"].send_rules(update, args[0], from_pm=True)

        else:
            first_name = update.effective_user.first_name
            update.effective_message.reply_text(
                PM_START_TEXT.format(escape_markdown(first_name), escape_markdown(bot.first_name), OWNER_ID),
                parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text="🎉 أضفني إلى مجموعتك", url="t.me/{}?startgroup=true".format(bot.username)),  InlineKeyboardButton(text="🤖 أنشئ بوت إدارة خاص بك", url="https://youtu.be/W6CLKrehy6w")],
                     [InlineKeyboardButton(text="👥 مجموعة الدعم", url="https://t.me/Mo_Tech_Group"), InlineKeyboardButton(text="🔔 قناة التحديثات", url="https://t.me/Mo_Tech_YT")],
                     [InlineKeyboardButton(text="👨‍💻 الإنشاء", url="https://youtu.be/wKL90i3cjPw"), InlineKeyboardButton(text="🛠 المساعدة", url="https://t.me/{}?start=help".format(bot.username)) ]]))

    else:
        update.effective_message.reply_text("لا يزال البوت يعمل...")


# لأغراض الاختبار
def error_callback(bot, update, error):
    try:
        raise error
    except Unauthorized:
        print("خطأ في التفويض")
        print(error)
    except BadRequest:
        print("طلب غير صالح")
        print(error)
    except TimedOut:
        print("انتهت المهلة")
    except NetworkError:
        print("خطأ في الشبكة")
    except ChatMigrated as err:
        print("تم ترحيل الدردشة")
        print(err)
    except TelegramError:
        print(error)


@run_async
def help_button(bot: Bot, update: Update):
    query = update.callback_query
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)
    try:
        if mod_match:
            module = mod_match.group(1)
            # تأكد من وجود المفتاح في القاموس
            if module not in HELPABLE:
                # حاول البحث بدون s في النهاية (لحالة admin_miscs)
                if module.endswith('s') and module[:-1] in HELPABLE:
                    module = module[:-1]
                else:
                    LOGGER.error(f"KeyError: module '{module}' not found in HELPABLE")
                    return
            text = "إليك المساعدة لوحدة *{}*:\n".format(HELPABLE[module].__mod_name__) + HELPABLE[module].__help__
            query.message.reply_text(text=text,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         [[InlineKeyboardButton(text="رجوع", callback_data="help_back")]]))

        elif prev_match:
            curr_page = int(prev_match.group(1))
            query.message.reply_text(HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(curr_page - 1, HELPABLE, "help")))

        elif next_match:
            next_page = int(next_match.group(1))
            query.message.reply_text(HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(next_page + 1, HELPABLE, "help")))

        elif back_match:
            query.message.reply_text(text=HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help")))

        # تأكد من عدم وجود دائرة تحميل
        bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            LOGGER.exception("استثناء في أزرار المساعدة. %s", str(query.data))


@run_async
def get_help(bot: Bot, update: Update):
    chat = update.effective_chat
    args = update.effective_message.text.split(None, 1)

    # أرسل المساعدة في الخاص فقط
    if chat.type != chat.PRIVATE:
        update.effective_message.reply_text("تواصل معي في الخاص للحصول على قائمة الأوامر.",
                                            reply_markup=InlineKeyboardMarkup(
                                                [[InlineKeyboardButton(text="مساعدة",
                                                                       url="t.me/{}?start=help".format(
                                                                           bot.username))]]))
        return

    elif len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
        module = args[1].lower()
        text = "إليك المساعدة المتاحة لوحدة *{}*:\n".format(HELPABLE[module].__mod_name__) \
               + HELPABLE[module].__help__
        send_help(chat.id, text, InlineKeyboardMarkup([[InlineKeyboardButton(text="رجوع", callback_data="help_back")]]))

    else:
        send_help(chat.id, HELP_STRINGS)


def send_settings(chat_id, user_id, user=False):
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                "*{}*:\n{}".format(mod.__mod_name__, mod.__user_settings__(user_id)) for mod in USER_SETTINGS.values())
            dispatcher.bot.send_message(user_id, "هذه هي إعداداتك الحالية:" + "\n\n" + settings,
                                        parse_mode=ParseMode.MARKDOWN)

        else:
            dispatcher.bot.send_message(user_id, "يبدو أنه لا توجد إعدادات خاصة بالمستخدمين متاحة :'(",
                                        parse_mode=ParseMode.MARKDOWN)

    else:
        if CHAT_SETTINGS:
            chat_name = dispatcher.bot.getChat(chat_id).title
            dispatcher.bot.send_message(user_id,
                                        text="أي وحدة تود الاطلاع على إعداداتها لـ {}؟".format(chat_name),
                                        reply_markup=InlineKeyboardMarkup(
                                            paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)))
        else:
            dispatcher.bot.send_message(user_id, "يبدو أنه لا توجد إعدادات للدردشات متاحة :'(\nأرسل هذا "
                                                 "في مجموعة أنت مشرف فيها لمعرفة إعداداتها الحالية!",
                                        parse_mode=ParseMode.MARKDOWN)


@run_async
def settings_button(bot: Bot, update: Update):
    query = update.callback_query
    user = update.effective_user
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = bot.get_chat(chat_id)
            text = "*{}* لديها الإعدادات التالية لوحدة *{}*:\n\n".format(escape_markdown(chat.title),
                                                                                     CHAT_SETTINGS[module].__mod_name__) + \
                   CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)
            query.message.reply_text(text=text,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         [[InlineKeyboardButton(text="رجوع",
                                                                callback_data="stngs_back({})".format(chat_id))]]))

        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text("مرحباً! هناك العديد من الإعدادات لـ {} - اختر ما تهتم به.".format(chat.title),
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(curr_page - 1, CHAT_SETTINGS, "stngs",
                                                          chat=chat_id)))

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text("مرحباً! هناك العديد من الإعدادات لـ {} - اختر ما تهتم به.".format(chat.title),
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(next_page + 1, CHAT_SETTINGS, "stngs",
                                                          chat=chat_id)))

        elif back_match:
            chat_id = back_match.group(1)
            chat = bot.get_chat(chat_id)
            query.message.reply_text(text="مرحباً! هناك العديد من الإعدادات لـ {} - اختر ما تهتم به.".format(escape_markdown(chat.title)),
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(paginate_modules(0, CHAT_SETTINGS, "stngs",
                                                                                        chat=chat_id)))

        # تأكد من عدم وجود دائرة تحميل
        bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            LOGGER.exception("استثناء في أزرار الإعدادات. %s", str(query.data))


@run_async
def get_settings(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    args = msg.text.split(None, 1)

    # أرسل الإعدادات في الخاص فقط
    if chat.type != chat.PRIVATE:
        if is_user_admin(chat, user.id):
            text = "اضغط هنا للحصول على إعدادات هذه الدردشة، بالإضافة إلى إعداداتك."
            msg.reply_text(text,
                           reply_markup=InlineKeyboardMarkup(
                               [[InlineKeyboardButton(text="الإعدادات",
                                                      url="t.me/{}?start=stngs_{}".format(
                                                          bot.username, chat.id))]]))
        else:
            text = "اضغط هنا لمراجعة إعداداتك."

    else:
        send_settings(chat.id, user.id, True)


@run_async
def donate(bot: Bot, update: Update):
    user = update.effective_message.from_user
    chat = update.effective_chat

    if chat.type == "private":
        update.effective_message.reply_text(DONATE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

        if OWNER_ID != 254318997 and DONATION_LINK:
            update.effective_message.reply_text("يمكنك أيضًا التبرع للشخص الذي يديرني حاليًا "
                                                "[هنا]({})".format(DONATION_LINK),
                                                parse_mode=ParseMode.MARKDOWN)

    else:
        try:
            bot.send_message(user.id, DONATE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

            update.effective_message.reply_text("لقد أرسلت لك رسالة خاصة بخصوص التبرع لمنشئي!")
        except Unauthorized:
            update.effective_message.reply_text("تواصل معي في الخاص أولاً للحصول على معلومات التبرع.")


def migrate_chats(bot: Bot, update: Update):
    msg = update.effective_message
    if msg.migrate_to_chat_id:
        old_chat = update.effective_chat.id
        new_chat = msg.migrate_to_chat_id
    elif msg.migrate_from_chat_id:
        old_chat = msg.migrate_from_chat_id
        new_chat = update.effective_chat.id
    else:
        return

    LOGGER.info("ترحيل من %s، إلى %s", str(old_chat), str(new_chat))
    for mod in MIGRATEABLE:
        mod.__migrate__(old_chat, new_chat)

    LOGGER.info("تم الترحيل بنجاح!")
    raise DispatcherHandlerStop


@run_async
def kcfrsct_fnc(bot: Bot, update: Update):
    query = update.callback_query
    user = update.effective_user
    _match = re.match(r"rsct_(.*)_33801", query.data)
    # تأكد من عدم وجود دائرة تحميل
    if _match:
        try:
            from tg_bot.modules.sql.cust_filters_sql import get_btn_with_di
            _soqka = get_btn_with_di(int(_match.group(1)))
            query.answer(
                text=_soqka.url.replace("\\n", "\n").replace("\\t", "\t"),
                show_alert=True
            )
        except Exception as e:
            print(e)
            bot.answer_callback_query(query.id)


@run_async
def start_arabic(bot: Bot, update: Update, args: List[str]):
    """الأمر العربي /بدء يعمل مثل /start"""
    start(bot, update, args)


@run_async
def help_arabic(bot: Bot, update: Update):
    """الأمر العربي /مساعدة يعمل مثل /help"""
    get_help(bot, update)


@run_async
def on_my_chat_member(bot: Bot, update: Update):
    """يتم استدعاؤها عندما تتغير حالة البوت في محادثة (إضافة، إزالة، ترقية)."""
    if update.my_chat_member:
        old = update.my_chat_member.old_chat_member
        new = update.my_chat_member.new_chat_member
        chat = update.effective_chat
        user = update.effective_user

        LOGGER.info(f"my_chat_member: chat_id={chat.id}, chat_type={chat.type}, "
                    f"old_status={old.status}, new_status={new.status}, "
                    f"user_id={user.id if user else 'None'}")

        # إذا تم إضافة البوت إلى مجموعة جديدة
        if old.status in ('left', 'kicked') and new.status == 'member':
            LOGGER.info(f"✅ Bot added to new chat: {chat.id} - {chat.title if chat.title else 'Private'}")
            # يمكن إرسال رسالة اختبارية هنا (اختياري)
            try:
                bot.send_message(chat.id, "تمت إضافتي! شكراً لاستضافتي.")
            except Exception as e:
                LOGGER.error(f"❌ Failed to send welcome message: {e}")

        # إذا تم إزالة البوت من مجموعة (بواسطة مستخدم أو البوت نفسه)
        elif new.status in ('left', 'kicked'):
            LOGGER.info(f"❌ Bot removed from chat: {chat.id} - {chat.title if chat.title else 'Private'}")


def main():
    test_handler = CommandHandler("test", test)
    start_handler = CommandHandler("start", start, pass_args=True)
    start_arabic_handler = CommandHandler("بدء", start_arabic, pass_args=True)  # أمر عربي جديد

    help_handler = CommandHandler("help", get_help)
    help_arabic_handler = CommandHandler("مساعدة", help_arabic)  # أمر عربي جديد
    help_callback_handler = CallbackQueryHandler(help_button, pattern=r"help_")

    settings_handler = CommandHandler("settings", get_settings)
    settings_callback_handler = CallbackQueryHandler(settings_button, pattern=r"stngs_")

    donate_handler = CommandHandler("donate", donate)
    migrate_handler = MessageHandler(Filters.status_update.migrate, migrate_chats)

    my_chat_member_handler = MessageHandler(Filters.status_update.my_chat_member, on_my_chat_member)

    # dispatcher.add_handler(test_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(start_arabic_handler)  # إضافة الأمر العربي
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(help_arabic_handler)  # إضافة الأمر العربي
    dispatcher.add_handler(settings_handler)
    dispatcher.add_handler(help_callback_handler)
    dispatcher.add_handler(settings_callback_handler)
    dispatcher.add_handler(migrate_handler)
    dispatcher.add_handler(donate_handler)
    dispatcher.add_handler(
        CallbackQueryHandler(kcfrsct_fnc, pattern=r"")
    )
    dispatcher.add_handler(my_chat_member_handler)

    # dispatcher.add_error_handler(error_callback)

    if WEBHOOK:
        LOGGER.info("استخدام webhooks.")
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=TOKEN)

        if CERT_PATH:
            updater.bot.set_webhook(url=URL + TOKEN,
                                    certificate=open(CERT_PATH, 'rb'))
        else:
            updater.bot.set_webhook(url=URL + TOKEN)

    else:
        LOGGER.info("استخدام long polling.")
        updater.start_polling(timeout=15, read_latency=4, clean=True)

    updater.idle()


if __name__ == '__main__':
    LOGGER.info("تم تحميل الوحدات بنجاح: " + str(ALL_MODULES))
    main()
