import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters, CommandHandler, run_async
from telegram.utils.helpers import mention_markdown, mention_html, escape_markdown

import tg_bot.modules.sql.welcome_sql as sql
from tg_bot import dispatcher, OWNER_ID, LOGGER
from tg_bot.modules.helper_funcs.chat_status import user_admin, can_delete
from tg_bot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from tg_bot.modules.helper_funcs.msg_types import get_welcome_type
from tg_bot.modules.helper_funcs.string_handling import markdown_parser, \
    escape_invalid_curly_brackets
from tg_bot.modules.log_channel import loggable

VALID_WELCOME_FORMATTERS = ['first', 'last', 'fullname', 'username', 'id', 'count', 'chatname', 'mention']

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video
}


# لا تستخدم async
def send(update, message, keyboard, backup_message):
    msg = None
    try:
        msg = update.effective_message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard, api_kwargs={"allow_sending_without_reply": True})
    except IndexError:
        msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                  "\nملاحظة: الرسالة الحالية غير صالحة بسبب مشاكل في الماركداون. قد يكون ذلك بسبب اسم المستخدم."),
                                                  parse_mode=ParseMode.MARKDOWN)
    except KeyError:
        msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                  "\nملاحظة: الرسالة الحالية غير صالحة بسبب مشكلة في الأقواس. يرجى التحديث."),
                                                  parse_mode=ParseMode.MARKDOWN)
    except BadRequest as excp:
        if excp.message == "Button_url_invalid":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nملاحظة: الرسالة الحالية تحتوي على رابط غير صالح في أحد الأزرار. يرجى التحديث."),
                                                      parse_mode=ParseMode.MARKDOWN)
        elif excp.message == "Unsupported url protocol":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nملاحظة: الرسالة الحالية تحتوي على أزرار تستخدم بروتوكولات روابط غير مدعومة من تليجرام. يرجى التحديث."),
                                                      parse_mode=ParseMode.MARKDOWN)
        elif excp.message == "Wrong url host":
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nملاحظة: الرسالة الحالية تحتوي على بعض الروابط الخاطئة. يرجى التحديث."),
                                                      parse_mode=ParseMode.MARKDOWN)
            LOGGER.warning(message)
            LOGGER.warning(keyboard)
            LOGGER.exception("تعذر التحليل! حدث خطأ في مضيف الرابط.")
        elif excp.message == "Replied message not found":
            LOGGER.warning("الرسالة الأصلية محذوفة")
        elif excp.message == "Have no rights to send a message":
            LOGGER.warning("مكتوم في الدردشة أدناه")
            print(update.effective_message.chat.id)
        else:
            msg = update.effective_message.reply_text(markdown_parser(backup_message +
                                                                      "\nملاحظة: حدث خطأ عند إرسال الرسالة المخصصة. يرجى التحديث."),
                                                      parse_mode=ParseMode.MARKDOWN)
            LOGGER.exception()

    return msg


@run_async
@user_admin
@loggable
def del_joined(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user

    if not args:
        del_pref = sql.get_del_pref(chat.id)
        if del_pref:
            update.effective_message.reply_text("يجب أن أحذف رسائل انضمام المستخدم الآن.")
        else:
            update.effective_message.reply_text("أنا لا أحذف رسائل الانضمام القديمة حالياً!")
        return ""

    if args[0].lower() in ("on", "yes"):
        sql.set_del_joined(str(chat.id), True)
        update.effective_message.reply_text("سأحاول حذف رسائل الانضمام القديمة!")
        return "<b>{}:</b>" \
               "\n#تنظيف_رسائل_الانضمام" \
               "\n<b>المشرف:</b> {}" \
               "\nقام بتشغيل حذف رسائل الانضمام إلى <code>ON</code>.".format(html.escape(chat.title),
                                                                         mention_html(user.id, user.first_name))
    elif args[0].lower() in ("off", "no"):
        sql.set_del_joined(str(chat.id), False)
        update.effective_message.reply_text("لن أحذف رسائل الانضمام القديمة.")
        return "<b>{}:</b>" \
               "\n#تنظيف_رسائل_الانضمام" \
               "\n<b>المشرف:</b> {}" \
               "\nقام بإيقاف حذف رسائل الانضمام إلى <code>OFF</code>.".format(html.escape(chat.title),
                                                                          mention_html(user.id, user.first_name))
    else:
        update.effective_message.reply_text("أنا أفهم 'on/yes' أو 'off/no' فقط!")
        return ""


@run_async
def delete_join(bot: Bot, update: Update):
    chat = update.effective_chat
    join = update.effective_message.new_chat_members
    if can_delete(chat, bot.id):
        del_join = sql.get_del_pref(chat.id)
        if del_join:
            update.message.delete()


@run_async
def new_member(bot: Bot, update: Update):
    chat = update.effective_chat

    should_welc, cust_welcome, welc_type = sql.get_welc_pref(chat.id)
    if should_welc:
        sent = None
        new_members = update.effective_message.new_chat_members
        for new_mem in new_members:
            if new_mem.id == OWNER_ID:
                update.effective_message.reply_text("المالك في المنزل، فلنبدأ الحفلة!")
                continue
            elif new_mem.id == bot.id:
                continue
            else:
                if welc_type != sql.Types.TEXT and welc_type != sql.Types.BUTTON_TEXT:
                    ENUM_FUNC_MAP[welc_type](chat.id, cust_welcome)
                    return
                first_name = new_mem.first_name or "شخص_بدون_اسم"

                if cust_welcome:
                    if new_mem.last_name:
                        fullname = "{} {}".format(first_name, new_mem.last_name)
                    else:
                        fullname = first_name
                    count = chat.get_members_count()
                    mention = mention_markdown(new_mem.id, escape_markdown(first_name))
                    if new_mem.username:
                        username = "@" + escape_markdown(new_mem.username)
                    else:
                        username = mention

                    valid_format = escape_invalid_curly_brackets(cust_welcome, VALID_WELCOME_FORMATTERS)

                    if not valid_format:
                        return

                    res = valid_format.format(first=escape_markdown(first_name),
                                              last=escape_markdown(new_mem.last_name or first_name),
                                              fullname=escape_markdown(fullname), username=username, mention=mention,
                                              count=count, chatname=escape_markdown(chat.title), id=new_mem.id)
                    buttons = sql.get_welc_buttons(chat.id)
                    keyb = build_keyboard(buttons)
                else:
                    res = sql.DEFAULT_WELCOME.format(first=first_name)
                    keyb = []

                keyboard = InlineKeyboardMarkup(keyb)

                sent = send(update, res, keyboard,
                            sql.DEFAULT_WELCOME.format(first=first_name))
            delete_join(bot, update)

        prev_welc = sql.get_clean_pref(chat.id)
        if prev_welc:
            try:
                bot.delete_message(chat.id, prev_welc)
            except BadRequest as excp:
                pass

            if sent:
                sql.set_clean_welcome(chat.id, sent.message_id)


@run_async
def left_member(bot: Bot, update: Update):
    chat = update.effective_chat
    should_goodbye, cust_goodbye, goodbye_type = sql.get_gdbye_pref(chat.id)
    if should_goodbye:
        left_mem = update.effective_message.left_chat_member
        if left_mem:
            if left_mem.id == bot.id:
                return
            if left_mem.id == OWNER_ID:
                update.effective_message.reply_text("وداعاً أيها المالك")
                return

            if goodbye_type != sql.Types.TEXT and goodbye_type != sql.Types.BUTTON_TEXT:
                ENUM_FUNC_MAP[goodbye_type](chat.id, cust_goodbye)
                return

            first_name = left_mem.first_name or "شخص_بدون_اسم"
            if cust_goodbye:
                if left_mem.last_name:
                    fullname = "{} {}".format(first_name, left_mem.last_name)
                else:
                    fullname = first_name
                count = chat.get_members_count()
                mention = mention_markdown(left_mem.id, first_name)
                if left_mem.username:
                    username = "@" + escape_markdown(left_mem.username)
                else:
                    username = mention

                valid_format = escape_invalid_curly_brackets(cust_goodbye, VALID_WELCOME_FORMATTERS)
                res = valid_format.format(first=escape_markdown(first_name),
                                          last=escape_markdown(left_mem.last_name or first_name),
                                          fullname=escape_markdown(fullname), username=username, mention=mention,
                                          count=count, chatname=escape_markdown(chat.title), id=left_mem.id)
                buttons = sql.get_gdbye_buttons(chat.id)
                keyb = build_keyboard(buttons)

            else:
                res = sql.DEFAULT_GOODBYE
                keyb = []

            keyboard = InlineKeyboardMarkup(keyb)

            send(update, res, keyboard, sql.DEFAULT_GOODBYE)
            delete_join(bot, update)


@run_async
@user_admin
def welcome(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    if len(args) == 0 or args[0].lower() == "noformat":
        noformat = args and args[0].lower() == "noformat"
        pref, welcome_m, welcome_type = sql.get_welc_pref(chat.id)
        update.effective_message.reply_text(
            "إعدادات الترحيب لهذه الدردشة: `{}`.\n*رسالة الترحيب (بدون تعبئة الـ {{}}):*".format(pref),
            parse_mode=ParseMode.MARKDOWN)

        if welcome_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                update.effective_message.reply_text(welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, welcome_m, keyboard, sql.DEFAULT_WELCOME)

        else:
            if noformat:
                ENUM_FUNC_MAP[welcome_type](chat.id, welcome_m)

            else:
                ENUM_FUNC_MAP[welcome_type](chat.id, welcome_m, parse_mode=ParseMode.MARKDOWN)

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_welc_preference(str(chat.id), True)
            update.effective_message.reply_text("سأكون مهذباً!")

        elif args[0].lower() in ("off", "no"):
            sql.set_welc_preference(str(chat.id), False)
            update.effective_message.reply_text("لن أقول مرحباً بعد الآن.")

        else:
            update.effective_message.reply_text("أنا أفهم 'on/yes' أو 'off/no' فقط!")


@run_async
@user_admin
def goodbye(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat

    if len(args) == 0 or args[0] == "noformat":
        noformat = args and args[0] == "noformat"
        pref, goodbye_m, goodbye_type = sql.get_gdbye_pref(chat.id)
        update.effective_message.reply_text(
            "إعدادات الوداع لهذه الدردشة: `{}`.\n*رسالة الوداع (بدون تعبئة الـ {{}}):*".format(pref),
            parse_mode=ParseMode.MARKDOWN)

        if goodbye_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_gdbye_buttons(chat.id)
            if noformat:
                goodbye_m += revert_buttons(buttons)
                update.effective_message.reply_text(goodbye_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, goodbye_m, keyboard, sql.DEFAULT_GOODBYE)

        else:
            if noformat:
                ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m)

            else:
                ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m, parse_mode=ParseMode.MARKDOWN)

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_gdbye_preference(str(chat.id), True)
            update.effective_message.reply_text("سأشعر بالأسف عندما يغادر الناس!")

        elif args[0].lower() in ("off", "no"):
            sql.set_gdbye_preference(str(chat.id), False)
            update.effective_message.reply_text("يغادرون، إنهم أموات بالنسبة لي.")

        else:
            update.effective_message.reply_text("أنا أفهم 'on/yes' أو 'off/no' فقط!")


@run_async
@user_admin
@loggable
def set_welcome(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("لم تحدد ماذا تريد الرد به!")
        return ""

    sql.set_custom_welcome(chat.id, content or text, data_type, buttons)
    msg.reply_text("تم تعيين رسالة ترحيب مخصصة بنجاح!")

    return "<b>{}:</b>" \
           "\n#تعيين_ترحيب" \
           "\n<b>المشرف:</b> {}" \
           "\nقام بتعيين رسالة الترحيب.".format(html.escape(chat.title),
                                               mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def reset_welcome(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user
    sql.set_custom_welcome(chat.id, sql.DEFAULT_WELCOME, sql.Types.TEXT)
    update.effective_message.reply_text("تم إعادة تعيين رسالة الترحيب إلى الافتراضية بنجاح!")
    return "<b>{}:</b>" \
           "\n#إعادة_تعيين_ترحيب" \
           "\n<b>المشرف:</b> {}" \
           "\nقام بإعادة تعيين رسالة الترحيب إلى الافتراضية.".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def set_goodbye(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("لم تحدد ماذا تريد الرد به!")
        return ""

    sql.set_custom_gdbye(chat.id, content or text, data_type, buttons)
    msg.reply_text("تم تعيين رسالة وداع مخصصة بنجاح!")
    return "<b>{}:</b>" \
           "\n#تعيين_وداع" \
           "\n<b>المشرف:</b> {}" \
           "\nقام بتعيين رسالة الوداع.".format(html.escape(chat.title),
                                               mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def reset_goodbye(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user
    sql.set_custom_gdbye(chat.id, sql.DEFAULT_GOODBYE, sql.Types.TEXT)
    update.effective_message.reply_text("تم إعادة تعيين رسالة الوداع إلى الافتراضية بنجاح!")
    return "<b>{}:</b>" \
           "\n#إعادة_تعيين_وداع" \
           "\n<b>المشرف:</b> {}" \
           "\nقام بإعادة تعيين رسالة الوداع.".format(html.escape(chat.title),
                                                 mention_html(user.id, user.first_name))


@run_async
@user_admin
@loggable
def clean_welcome(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user

    if not args:
        clean_pref = sql.get_clean_pref(chat.id)
        if clean_pref:
            update.effective_message.reply_text("يجب أن أحذف رسائل الترحيب القديمة حتى عمر يومين.")
        else:
            update.effective_message.reply_text("أنا لا أحذف رسائل الترحيب القديمة حالياً!")
        return ""

    if args[0].lower() in ("on", "yes"):
        sql.set_clean_welcome(str(chat.id), True)
        update.effective_message.reply_text("سأحاول حذف رسائل الترحيب القديمة!")
        return "<b>{}:</b>" \
               "\n#تنظيف_ترحيب" \
               "\n<b>المشرف:</b> {}" \
               "\nقام بتشغيل تنظيف الترحيب إلى <code>ON</code>.".format(html.escape(chat.title),
                                                                         mention_html(user.id, user.first_name))
    elif args[0].lower() in ("off", "no"):
        sql.set_clean_welcome(str(chat.id), False)
        update.effective_message.reply_text("لن أحذف رسائل الترحيب القديمة.")
        return "<b>{}:</b>" \
               "\n#تنظيف_ترحيب" \
               "\n<b>المشرف:</b> {}" \
               "\nقام بإيقاف تنظيف الترحيب إلى <code>OFF</code>.".format(html.escape(chat.title),
                                                                          mention_html(user.id, user.first_name))
    else:
        update.effective_message.reply_text("أنا أفهم 'on/yes' أو 'off/no' فقط!")
        return ""


WELC_HELP_TXT = """
يمكن تخصيص رسائل الترحيب/الوداع لمجموعتك بعدة طرق. إذا كنت تريد أن يتم إنشاء الرسائل بشكل فردي، مثل رسالة الترحيب الافتراضية، يمكنك استخدام *هذه* المتغيرات:
- `{{first}}`: يمثل الاسم *الأول* للمستخدم.
- `{{last}}`: يمثل الاسم *الأخير* للمستخدم. يتحول إلى *الاسم الأول* إذا لم يكن للمستخدم اسم أخير.
- `{{fullname}}`: يمثل الاسم *الكامل* للمستخدم. يتحول إلى *الاسم الأول* إذا لم يكن للمستخدم اسم أخير.
- `{{username}}`: يمثل *اسم المستخدم* للمستخدم. يتحول إلى *منشن* للمستخدم إذا لم يكن له اسم مستخدم.
- `{{mention}}`: يقوم ببساطة بعمل *منشن* للمستخدم.
- `{{id}}`: يمثل *معرف* المستخدم.
- `{{count}}`: يمثل *رقم العضوية* للمستخدم.
- `{{chatname}}`: يمثل *اسم الدردشة الحالية*.

يجب أن يكون كل متغير محاطاً بـ `{{}}` ليتم استبداله.
رسائل الترحيب تدعم أيضاً الماركداون، لذا يمكنك جعل أي عناصر عريضة/مائلة/كود/روابط. الأزرار مدعومة أيضاً، لذا يمكنك جعل ترحيباتك رائعة مع بعض أزرار المقدمة الجميلة.
لإنشاء زر يربط بقوانينك، استخدم هذا: `[القوانين](buttonurl://t.me/{}?start=group_id)`. فقط استبدل `group_id` بمعرف مجموعتك، والذي يمكن الحصول عليه عبر /id، وكل شيء سيكون على ما يرام. لاحظ أن معرفات المجموعات عادة ما يسبقها علامة `-`، وهذا مطلوب، لذا يرجى عدم إزالتها.
إذا كنت تشعر بالمرح، يمكنك حتى تعيين صور/gifs/فيديو/رسائل صوتية كرسالة ترحيب من خلال الرد على الوسائط المرغوبة واستدعاء /setwelcome.
""".format(dispatcher.bot.username)


@run_async
@user_admin
def welcome_help(bot: Bot, update: Update):
    update.effective_message.reply_text(WELC_HELP_TXT, parse_mode=ParseMode.MARKDOWN)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    welcome_pref, _, _ = sql.get_welc_pref(chat_id)
    goodbye_pref, _, _ = sql.get_gdbye_pref(chat_id)
    return "إعدادات الترحيب لهذه الدردشة: `{}`.\nإعدادات الوداع: `{}`.".format(welcome_pref, goodbye_pref)


# ================== المساعدة ==================
__help__ = """
{}
*للمشرفين فقط:*
- /welcome <on/off>: تفعيل/تعطيل رسائل الترحيب.
- /welcome: عرض إعدادات الترحيب الحالية.
- /welcome noformat: عرض إعدادات الترحيب الحالية بدون تنسيق - مفيد لإعادة استخدام رسائلك!
- /goodbye: نفس الاستخدام والوسائط كـ /welcome.
- /setwelcome <نص>: تعيين رسالة ترحيب مخصصة. إذا استخدمت بالرد على وسائط، يستخدم تلك الوسائط.
- /setgoodbye <نص>: تعيين رسالة وداع مخصصة. إذا استخدمت بالرد على وسائط، يستخدم تلك الوسائط.
- /resetwelcome: إعادة تعيين رسالة الترحيب إلى الافتراضية.
- /resetgoodbye: إعادة تعيين رسالة الوداع إلى الافتراضية.
- /cleanwelcome <on/off>: عند عضو جديد، حاول حذف رسالة الترحيب السابقة لتجنب إزعاج الدردشة.
- /rmjoin <on/off>: عندما ينضم شخص، حاول حذف رسالة انضمام المستخدم.
- /welcomehelp: عرض المزيد من معلومات التنسيق لرسائل الترحيب/الوداع المخصصة.

*الأوامر العربية (بدون /):*
تشغيل الترحيب: تفعيل رسائل الترحيب
إيقاف الترحيب: تعطيل رسائل الترحيب
الترحيب: عرض إعدادات الترحيب
تعيين ترحيب <نص>: تعيين رسالة ترحيب مخصصة
إعادة ترحيب: إعادة تعيين الترحيب إلى الافتراضي
وداع: عرض إعدادات الوداع
تعيين وداع <نص>: تعيين رسالة وداع مخصصة
إعادة وداع: إعادة تعيين الوداع إلى الافتراضي
تنظيف ترحيب <on/off>: تفعيل/تعطيل تنظيف الترحيب
حذف انضمام <on/off>: تفعيل/تعطيل حذف رسائل الانضمام
مساعدة ترحيب: عرض تعليمات الترحيب
""".format(WELC_HELP_TXT)

__mod_name__ = "الترحيب"

NEW_MEM_HANDLER = MessageHandler(Filters.status_update.new_chat_members, new_member)
LEFT_MEM_HANDLER = MessageHandler(Filters.status_update.left_chat_member, left_member)
WELC_PREF_HANDLER = CommandHandler("welcome", welcome, pass_args=True, filters=Filters.group)
GOODBYE_PREF_HANDLER = CommandHandler("goodbye", goodbye, pass_args=True, filters=Filters.group)
SET_WELCOME = CommandHandler("setwelcome", set_welcome, filters=Filters.group)
SET_GOODBYE = CommandHandler("setgoodbye", set_goodbye, filters=Filters.group)
RESET_WELCOME = CommandHandler("resetwelcome", reset_welcome, filters=Filters.group)
RESET_GOODBYE = CommandHandler("resetgoodbye", reset_goodbye, filters=Filters.group)
CLEAN_WELCOME = CommandHandler("cleanwelcome", clean_welcome, pass_args=True, filters=Filters.group)
DEL_JOINED = CommandHandler("rmjoin", del_joined, pass_args=True, filters=Filters.group)
WELCOME_HELP = CommandHandler("welcomehelp", welcome_help)

# معالجات الأوامر العربية
WELCOME_AR_ON = MessageHandler(Filters.regex(r'^تشغيل الترحيب$'), lambda b,u: welcome(b,u,args=["on"]))
WELCOME_AR_OFF = MessageHandler(Filters.regex(r'^إيقاف الترحيب$'), lambda b,u: welcome(b,u,args=["off"]))
WELCOME_AR_SHOW = MessageHandler(Filters.regex(r'^الترحيب$'), lambda b,u: welcome(b,u,args=[]))
WELCOME_AR_NOFORMAT = MessageHandler(Filters.regex(r'^الترحيب بدون تنسيق$'), lambda b,u: welcome(b,u,args=["noformat"]))
SET_WELCOME_AR = MessageHandler(Filters.regex(r'^تعيين ترحيب (.+)$'), set_welcome)
RESET_WELCOME_AR = MessageHandler(Filters.regex(r'^إعادة ترحيب$'), reset_welcome)
GOODBYE_AR_ON = MessageHandler(Filters.regex(r'^تشغيل الوداع$'), lambda b,u: goodbye(b,u,args=["on"]))
GOODBYE_AR_OFF = MessageHandler(Filters.regex(r'^إيقاف الوداع$'), lambda b,u: goodbye(b,u,args=["off"]))
GOODBYE_AR_SHOW = MessageHandler(Filters.regex(r'^وداع$'), lambda b,u: goodbye(b,u,args=[]))
GOODBYE_AR_NOFORMAT = MessageHandler(Filters.regex(r'^وداع بدون تنسيق$'), lambda b,u: goodbye(b,u,args=["noformat"]))
SET_GOODBYE_AR = MessageHandler(Filters.regex(r'^تعيين وداع (.+)$'), set_goodbye)
RESET_GOODBYE_AR = MessageHandler(Filters.regex(r'^إعادة وداع$'), reset_goodbye)
CLEAN_WELCOME_AR_ON = MessageHandler(Filters.regex(r'^تشغيل تنظيف ترحيب$'), lambda b,u: clean_welcome(b,u,args=["on"]))
CLEAN_WELCOME_AR_OFF = MessageHandler(Filters.regex(r'^إيقاف تنظيف ترحيب$'), lambda b,u: clean_welcome(b,u,args=["off"]))
CLEAN_WELCOME_AR_SHOW = MessageHandler(Filters.regex(r'^تنظيف ترحيب$'), lambda b,u: clean_welcome(b,u,args=[]))
DEL_JOINED_AR_ON = MessageHandler(Filters.regex(r'^تشغيل حذف انضمام$'), lambda b,u: del_joined(b,u,args=["on"]))
DEL_JOINED_AR_OFF = MessageHandler(Filters.regex(r'^إيقاف حذف انضمام$'), lambda b,u: del_joined(b,u,args=["off"]))
DEL_JOINED_AR_SHOW = MessageHandler(Filters.regex(r'^حذف انضمام$'), lambda b,u: del_joined(b,u,args=[]))
WELCOME_HELP_AR = MessageHandler(Filters.regex(r'^مساعدة ترحيب$'), welcome_help)

dispatcher.add_handler(NEW_MEM_HANDLER)
dispatcher.add_handler(LEFT_MEM_HANDLER)
dispatcher.add_handler(WELC_PREF_HANDLER)
dispatcher.add_handler(GOODBYE_PREF_HANDLER)
dispatcher.add_handler(SET_WELCOME)
dispatcher.add_handler(SET_GOODBYE)
dispatcher.add_handler(RESET_WELCOME)
dispatcher.add_handler(RESET_GOODBYE)
dispatcher.add_handler(CLEAN_WELCOME)
dispatcher.add_handler(DEL_JOINED)
dispatcher.add_handler(WELCOME_HELP)

dispatcher.add_handler(WELCOME_AR_ON)
dispatcher.add_handler(WELCOME_AR_OFF)
dispatcher.add_handler(WELCOME_AR_SHOW)
dispatcher.add_handler(WELCOME_AR_NOFORMAT)
dispatcher.add_handler(SET_WELCOME_AR)
dispatcher.add_handler(RESET_WELCOME_AR)
dispatcher.add_handler(GOODBYE_AR_ON)
dispatcher.add_handler(GOODBYE_AR_OFF)
dispatcher.add_handler(GOODBYE_AR_SHOW)
dispatcher.add_handler(GOODBYE_AR_NOFORMAT)
dispatcher.add_handler(SET_GOODBYE_AR)
dispatcher.add_handler(RESET_GOODBYE_AR)
dispatcher.add_handler(CLEAN_WELCOME_AR_ON)
dispatcher.add_handler(CLEAN_WELCOME_AR_OFF)
dispatcher.add_handler(CLEAN_WELCOME_AR_SHOW)
dispatcher.add_handler(DEL_JOINED_AR_ON)
dispatcher.add_handler(DEL_JOINED_AR_OFF)
dispatcher.add_handler(DEL_JOINED_AR_SHOW)
dispatcher.add_handler(WELCOME_HELP_AR)
