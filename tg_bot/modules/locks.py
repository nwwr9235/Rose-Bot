import html
from typing import Optional, List

import telegram.ext as tg
from telegram import Message, Chat, Update, Bot, ParseMode, User, MessageEntity
from telegram import TelegramError
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

import tg_bot.modules.sql.locks_sql as sql
from tg_bot import dispatcher, SUDO_USERS, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import can_delete, is_user_admin, user_not_admin, user_admin, \
    bot_can_delete, is_bot_admin
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import users_sql

LOCK_TYPES = {'sticker': Filters.sticker,
              'audio': Filters.audio,
              'voice': Filters.voice,
              'document': Filters.document,
              'video': Filters.video,
              'contact': Filters.contact,
              'photo': Filters.photo,
              'gif': Filters.document & CustomFilters.mime_type("video/mp4"),
              'url': Filters.entity(MessageEntity.URL) | Filters.caption_entity(MessageEntity.URL),
              'bots': Filters.status_update.new_chat_members,
              'forward': Filters.forwarded,
              'game': Filters.game,
              'location': Filters.location,
              }

GIF = Filters.document & CustomFilters.mime_type("video/mp4")
OTHER = Filters.game | Filters.sticker | GIF
MEDIA = Filters.audio | Filters.document | Filters.video | Filters.voice | Filters.photo
MESSAGES = Filters.text | Filters.contact | Filters.location | Filters.venue | Filters.command | MEDIA | OTHER
PREVIEWS = Filters.entity("url")

RESTRICTION_TYPES = {'messages': MESSAGES,
                     'media': MEDIA,
                     'other': OTHER,
                     'all': Filters.all}

PERM_GROUP = 1
REST_GROUP = 2


class CustomCommandHandler(tg.CommandHandler):
    def __init__(self, command, callback, **kwargs):
        super().__init__(command, callback, **kwargs)

    def check_update(self, update):
        return super().check_update(update) and not (
                sql.is_restr_locked(update.effective_chat.id, 'messages') and not is_user_admin(update.effective_chat,
                                                                                                update.effective_user.id))


tg.CommandHandler = CustomCommandHandler


# NOT ASYNC
def restr_members(bot, chat_id, members, messages=False, media=False, other=False, previews=False):
    for mem in members:
        if mem.user in SUDO_USERS:
            pass
        try:
            bot.restrict_chat_member(chat_id, mem.user,
                                     can_send_messages=messages,
                                     can_send_media_messages=media,
                                     can_send_other_messages=other,
                                     can_add_web_page_previews=previews)
        except TelegramError:
            pass


# NOT ASYNC
def unrestr_members(bot, chat_id, members, messages=True, media=True, other=True, previews=True):
    for mem in members:
        try:
            bot.restrict_chat_member(chat_id, mem.user,
                                     can_send_messages=messages,
                                     can_send_media_messages=media,
                                     can_send_other_messages=other,
                                     can_add_web_page_previews=previews)
        except TelegramError:
            pass


@run_async
def locktypes(bot: Bot, update: Update):
    update.effective_message.reply_text("\n - ".join(["أنواع القفل: "] + list(LOCK_TYPES) + list(RESTRICTION_TYPES)))


@user_admin
@bot_can_delete
@loggable
def lock(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    if can_delete(chat, bot.id):
        if len(args) >= 1:
            if args[0] in LOCK_TYPES:
                sql.update_lock(chat.id, args[0], locked=True)
                message.reply_text("تم قفل {} لجميع غير المشرفين!".format(args[0]))

                return "<b>{}:</b>" \
                       "\n#قفل" \
                       "\n<b>المشرف:</b> {}" \
                       "\nتم قفل <code>{}</code>.".format(html.escape(chat.title),
                                                          mention_html(user.id, user.first_name), args[0])

            elif args[0] in RESTRICTION_TYPES:
                sql.update_restriction(chat.id, args[0], locked=True)
                if args[0] == "previews":
                    members = users_sql.get_chat_members(str(chat.id))
                    restr_members(bot, chat.id, members, messages=True, media=True, other=True)

                message.reply_text("تم قفل {} لجميع غير المشرفين!".format(args[0]))
                return "<b>{}:</b>" \
                       "\n#قفل" \
                       "\n<b>المشرف:</b> {}" \
                       "\nتم قفل <code>{}</code>.".format(html.escape(chat.title),
                                                          mention_html(user.id, user.first_name), args[0])

            else:
                message.reply_text("ماذا تحاول قفله...؟ جرب /locktypes لقائمة العناصر القابلة للقفل")

    else:
        message.reply_text("أنا لست مشرفاً، أو ليس لدي صلاحيات الحذف.")

    return ""


@run_async
@user_admin
@loggable
def unlock(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    if is_user_admin(chat, message.from_user.id):
        if len(args) >= 1:
            if args[0] in LOCK_TYPES:
                sql.update_lock(chat.id, args[0], locked=False)
                message.reply_text("تم فتح {} للجميع!".format(args[0]))
                return "<b>{}:</b>" \
                       "\n#فتح" \
                       "\n<b>المشرف:</b> {}" \
                       "\nتم فتح <code>{}</code>.".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name), args[0])

            elif args[0] in RESTRICTION_TYPES:
                sql.update_restriction(chat.id, args[0], locked=False)
                message.reply_text("تم فتح {} للجميع!".format(args[0]))

                return "<b>{}:</b>" \
                       "\n#فتح" \
                       "\n<b>المشرف:</b> {}" \
                       "\nتم فتح <code>{}</code>.".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name), args[0])
            else:
                message.reply_text("ماذا تحاول فتحه...؟ جرب /locktypes لقائمة العناصر القابلة للقفل")

        else:
            bot.sendMessage(chat.id, "ماذا تحاول فتحه...؟")

    return ""


@run_async
@user_not_admin
def del_lockables(bot: Bot, update: Update):
    chat = update.effective_chat
    message = update.effective_message

    for lockable, filter in LOCK_TYPES.items():
        if filter(message) and sql.is_locked(chat.id, lockable) and can_delete(chat, bot.id):
            if lockable == "bots":
                new_members = update.effective_message.new_chat_members
                for new_mem in new_members:
                    if new_mem.is_bot:
                        if not is_bot_admin(chat, bot.id):
                            message.reply_text("أرى بوتاً، وقد طُلب مني منعهم من الانضمام... لكني لست مشرفاً!")
                            return

                        chat.kick_member(new_mem.id)
                        message.reply_text("فقط المشرفون مسموح لهم بإضافة البوتات إلى هذه الدردشة! اخرج من هنا.")
            else:
                try:
                    message.delete()
                except BadRequest as excp:
                    if excp.message == "Message to delete not found":
                        pass
                    else:
                        LOGGER.exception("خطأ في العناصر القابلة للقفل")

            break


@run_async
@user_not_admin
def rest_handler(bot: Bot, update: Update):
    msg = update.effective_message
    chat = update.effective_chat
    for restriction, filter in RESTRICTION_TYPES.items():
        if filter(msg) and sql.is_restr_locked(chat.id, restriction) and can_delete(chat, bot.id):
            try:
                msg.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("خطأ في القيود")
            break


def build_lock_message(chat_id):
    locks = sql.get_locks(chat_id)
    restr = sql.get_restr(chat_id)
    if not (locks or restr):
        res = "لا توجد أقفال حالية في هذه الدردشة."
    else:
        res = "هذه هي الأقفال في هذه الدردشة:"
        if locks:
            res += "\n - ملصق = `{}`" \
                   "\n - صوت = `{}`" \
                   "\n - مكالمة صوتية = `{}`" \
                   "\n - مستند = `{}`" \
                   "\n - فيديو = `{}`" \
                   "\n - جهة اتصال = `{}`" \
                   "\n - صورة = `{}`" \
                   "\n - متحركة = `{}`" \
                   "\n - رابط = `{}`" \
                   "\n - بوتات = `{}`" \
                   "\n - إعادة توجيه = `{}`" \
                   "\n - لعبة = `{}`" \
                   "\n - موقع = `{}`".format(locks.sticker, locks.audio, locks.voice, locks.document,
                                                 locks.video, locks.contact, locks.photo, locks.gif, locks.url,
                                                 locks.bots, locks.forward, locks.game, locks.location)
        if restr:
            res += "\n - رسائل = `{}`" \
                   "\n - وسائط = `{}`" \
                   "\n - أخرى = `{}`" \
                   "\n - الكل = `{}`".format(restr.messages, restr.media, restr.other,
                                            all([restr.messages, restr.media, restr.other]))
    return res


@run_async
@user_admin
def list_locks(bot: Bot, update: Update):
    chat = update.effective_chat

    res = build_lock_message(chat.id)

    update.effective_message.reply_text(res, parse_mode=ParseMode.MARKDOWN)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return build_lock_message(chat_id)


# ================== المساعدة ==================
__help__ = """
- /locktypes: قائمة بأنواع الأقفال الممكنة

*للمشرفين فقط:*
- /lock <نوع>: قفل عناصر من نوع معين (غير متاح في الخاص)
- /unlock <نوع>: فتح عناصر من نوع معين (غير متاح في الخاص)
- /locks: القائمة الحالية للأقفال في هذه الدردشة.

يمكن استخدام الأقفال لتقييد مستخدمي المجموعة.
مثال:
قفل الروابط سيحذف تلقائياً جميع الرسائل التي تحتوي على روابط، قفل الملصقات سيحذف جميع الملصقات، إلخ.
قفل البوتات سيمنع غير المشرفين من إضافة البوتات إلى الدردشة.

*الأوامر العربية (بدون /):*
قفل <النوع>: لقفل نوع معين (مثال: "قفل الروابط")
فتح <النوع>: لفتح نوع معين (مثال: "فتح الصور")
أنواع الأقفال: عرض جميع أنواع الأقفال المتاحة
الأقفال: عرض الأقفال الحالية
"""

__mod_name__ = "الأقفال"

LOCKTYPES_HANDLER = DisableAbleCommandHandler("locktypes", locktypes)
LOCK_HANDLER = CommandHandler("lock", lock, pass_args=True, filters=Filters.group)
UNLOCK_HANDLER = CommandHandler("unlock", unlock, pass_args=True, filters=Filters.group)
LOCKED_HANDLER = CommandHandler("locks", list_locks, filters=Filters.group)

# معالجات الأوامر العربية (بدون /)
def lock_arabic(bot: Bot, update: Update, args: List[str]):
    # args هنا سيتم تمريرها من خلال معالج الرسائل (لكننا سنستخرج من النص)
    text = update.effective_message.text
    # نتوقع صيغة مثل "قفل الروابط" أو "فتح الصور"
    parts = text.split()
    if len(parts) == 2 and parts[0] == "قفل":
        lock_type = parts[1]
        # نحتاج لتحويل الأسماء العربية إلى الإنجليزية
        type_map = {
            "الروابط": "url",
            "الملصقات": "sticker",
            "الصور": "photo",
            "الفيديو": "video",
            "الصوت": "audio",
            "البوتات": "bots",
            "الرسائل": "messages",
            "الوسائط": "media",
            "الكل": "all",
            "إعادة التوجيه": "forward",
            "الموقع": "location",
            "الملفات": "document",
            "المتحركة": "gif",
            "جهات الاتصال": "contact",
            "الألعاب": "game",
        }
        eng_type = type_map.get(lock_type, lock_type)
        # استدعاء الدالة الأصلية مع args محاكاة
        update.effective_message.text = f"/lock {eng_type}"
        return lock(bot, update, [eng_type])
    elif len(parts) == 2 and parts[0] == "فتح":
        lock_type = parts[1]
        type_map = {
            "الروابط": "url",
            "الملصقات": "sticker",
            "الصور": "photo",
            "الفيديو": "video",
            "الصوت": "audio",
            "البوتات": "bots",
            "الرسائل": "messages",
            "الوسائط": "media",
            "الكل": "all",
            "إعادة التوجيه": "forward",
            "الموقع": "location",
            "الملفات": "document",
            "المتحركة": "gif",
            "جهات الاتصال": "contact",
            "الألعاب": "game",
        }
        eng_type = type_map.get(lock_type, lock_type)
        update.effective_message.text = f"/unlock {eng_type}"
        return unlock(bot, update, [eng_type])
    else:
        update.effective_message.reply_text("استخدم: قفل <النوع> أو فتح <النوع>")

LOCK_AR_HANDLER = MessageHandler(Filters.regex(r'^(قفل|فتح)\s+(.+)$'), lock_arabic)

LOCKTYPES_AR_HANDLER = CommandHandler("أنواع الأقفال", locktypes)
LOCKS_AR_HANDLER = CommandHandler("الأقفال", list_locks)

dispatcher.add_handler(LOCK_HANDLER)
dispatcher.add_handler(UNLOCK_HANDLER)
dispatcher.add_handler(LOCKTYPES_HANDLER)
dispatcher.add_handler(LOCKED_HANDLER)

dispatcher.add_handler(MessageHandler(Filters.all & Filters.group, del_lockables), PERM_GROUP)
dispatcher.add_handler(MessageHandler(Filters.all & Filters.group, rest_handler), REST_GROUP)

dispatcher.add_handler(LOCK_AR_HANDLER)
dispatcher.add_handler(LOCKTYPES_AR_HANDLER)
dispatcher.add_handler(LOCKS_AR_HANDLER)
