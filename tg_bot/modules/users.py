# tg_bot/modules/users.py
from io import BytesIO
from time import sleep
from typing import Optional

from telegram import TelegramError, Chat, Message
from telegram import Update, Bot
from telegram.error import BadRequest, Unauthorized
from telegram.ext import MessageHandler, Filters, CommandHandler
from telegram.ext.dispatcher import run_async

import tg_bot.modules.sql.users_sql as sql
from tg_bot import dispatcher, OWNER_ID, LOGGER
from tg_bot.modules.helper_funcs.filters import CustomFilters

USERS_GROUP = 4
CHAT_GROUP = 10


def get_user_id(username):
    if len(username) <= 5:
        return None
    if username.startswith('@'):
        username = username[1:]
    users = sql.get_userid_by_name(username)
    if not users:
        return None
    elif len(users) == 1:
        return users[0].user_id
    else:
        for user_obj in users:
            try:
                userdat = dispatcher.bot.get_chat(user_obj.user_id)
                if userdat.username == username:
                    return userdat.id
            except BadRequest as excp:
                if excp.message == 'Chat not found':
                    pass
                else:
                    LOGGER.exception("خطأ في استخراج معرف المستخدم")
    return None


@run_async
def broadcast(bot: Bot, update: Update):
    to_send = update.effective_message.text.split(None, 1)
    if len(to_send) >= 2:
        chats = sql.get_all_chats() or []
        failed = 0
        for chat in chats:
            try:
                bot.sendMessage(int(chat.chat_id), to_send[1])
                sleep(0.1)
            except TelegramError:
                failed += 1
                LOGGER.warning("تعذر إرسال البث إلى %s، اسم المجموعة %s", str(chat.chat_id), str(chat.chat_name))
        update.effective_message.reply_text(f"تم البث بنجاح. {failed} مجموعة فشلت في استلام الرسالة، ربما بسبب الطرد.")


@run_async
def userbroadcast(bot: Bot, update: Update):
    to_send = update.effective_message.text.split(None, 1)
    if len(to_send) >= 2:
        users = sql.get_all_users() or []
        failed = 0
        success = 0
        for user in users:
            try:
                bot.sendMessage(int(user.user_id), to_send[1])
                success += 1
                LOGGER.warning("تم إرسال البث إلى %s، اسم المستخدم %s، العدد: %s", str(user.user_id), str(user.username), str(success))
                sleep(0.5)
            except TelegramError:
                failed += 1
        update.effective_message.reply_text(f"تم البث بنجاح.\n{failed} مستخدم فشلوا\n{success} مستخدم استلموا")


@run_async
def log_user(bot: Bot, update: Update):
    chat = update.effective_chat
    msg = update.effective_message
    sql.update_user(msg.from_user.id, msg.from_user.username, chat.id, chat.title)
    if msg.reply_to_message:
        sql.update_user(msg.reply_to_message.from_user.id,
                        msg.reply_to_message.from_user.username,
                        chat.id, chat.title)
    if msg.forward_from:
        sql.update_user(msg.forward_from.id, msg.forward_from.username, chat.id, chat.title)


@run_async
def chats(bot: Bot, update: Update):
    all_chats = sql.get_all_chats() or []
    chatfile = 'قائمة الدردشات.\n'
    for chat in all_chats:
        chatfile += f"{chat.chat_name} - ({chat.chat_id})\n"
    with BytesIO(str.encode(chatfile)) as output:
        output.name = "chatlist.txt"
        update.effective_message.reply_document(
            document=output,
            filename="chatlist.txt",
            caption="هذه قائمة الدردشات في قاعدة بياناتي."
        )


@run_async
def chat_checker(bot: Bot, update: Update):
    try:
        member = update.effective_message.chat.get_member(bot.id)
        # نتحقق فقط إذا كان can_send_messages صراحةً False (وليس None)
        # لتجنب مغادرة البوت عند إضافته لأول مرة قبل منحه الصلاحيات
        if member and member.can_send_messages == False:
            bot.leaveChat(update.effective_message.chat.id)
    except Unauthorized:
        # البوت ليس عضواً في الدردشة، نتجاهل
        pass
    except BadRequest as e:
        if "chat not found" in str(e).lower():
            # الدردشة غير موجودة، ربما تم حذفها
            pass
        else:
            LOGGER.exception(f"خطأ في chat_checker: {e}")
    except Exception as e:
        LOGGER.exception(f"خطأ غير متوقع في chat_checker: {e}")


def __user_info__(user_id):
    if user_id == dispatcher.bot.id:
        return """لقد رأيتهم في... واو. هل يتتبعونني؟ إنهم في كل الأماكن التي أتواجد فيها... أوه، إنه أنا."""
    num_chats = sql.get_user_num_chats(user_id)
    return f"<code>{num_chats}</code> دردشة رأيت هذا المستخدم فيها."


def __stats__():
    return f"{sql.num_users()} مستخدم، عبر {sql.num_chats()} دردشة"


def __gdpr__(user_id):
    sql.del_user(user_id)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


__help__ = ""
__mod_name__ = "المستخدمون"

BROADCAST_HANDLER = CommandHandler("broadcast", broadcast, filters=Filters.user(OWNER_ID))
USER_HANDLER = MessageHandler(Filters.all & Filters.group, log_user)
USER_BROADCAST_HANDLER = CommandHandler("userbroadcast", userbroadcast, filters=Filters.user(OWNER_ID))
CHATLIST_HANDLER = CommandHandler("chatlist", chats, filters=CustomFilters.sudo_filter)
CHAT_CHECKER_HANDLER = MessageHandler(Filters.all & Filters.group, chat_checker)

# معالجات الأوامر العربية
BROADCAST_AR_HANDLER = CommandHandler("بث", broadcast, filters=Filters.user(OWNER_ID))
USERBROADCAST_AR_HANDLER = CommandHandler("بث_مستخدمين", userbroadcast, filters=Filters.user(OWNER_ID))
CHATLIST_AR_HANDLER = CommandHandler("قائمة_الدردشات", chats, filters=CustomFilters.sudo_filter)

dispatcher.add_handler(USER_HANDLER, USERS_GROUP)
dispatcher.add_handler(BROADCAST_HANDLER)
dispatcher.add_handler(USER_BROADCAST_HANDLER)
dispatcher.add_handler(CHATLIST_HANDLER)
dispatcher.add_handler(CHAT_CHECKER_HANDLER, CHAT_GROUP)

dispatcher.add_handler(BROADCAST_AR_HANDLER)
dispatcher.add_handler(USERBROADCAST_AR_HANDLER)
dispatcher.add_handler(CHATLIST_AR_HANDLER)
