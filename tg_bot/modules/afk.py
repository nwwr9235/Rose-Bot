from typing import Optional

from telegram import Message, Update, Bot, User
from telegram import MessageEntity
from telegram.ext import Filters, MessageHandler, run_async

from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler, DisableAbleRegexHandler
from tg_bot.modules.sql import afk_sql as sql
from tg_bot.modules.users import get_user_id

AFK_GROUP = 7
AFK_REPLY_GROUP = 8


@run_async
def afk(bot: Bot, update: Update):
    args = update.effective_message.text.split(None, 1)
    if len(args) >= 2:
        reason = args[1]
    else:
        reason = ""

    sql.set_afk(update.effective_user.id, reason)
    update.effective_message.reply_text("{} هو الآن AFK!".format(update.effective_user.first_name))


@run_async
def no_longer_afk(bot: Bot, update: Update):
    user = update.effective_user

    if not user:  # تجاهل القنوات
        return

    res = sql.rm_afk(user.id)
    if res:
        update.effective_message.reply_text("{} لم يعد AFK!".format(update.effective_user.first_name))


@run_async
def reply_afk(bot: Bot, update: Update):
    message = update.effective_message
    if message.entities and message.parse_entities([MessageEntity.TEXT_MENTION, MessageEntity.MENTION]):
        entities = message.parse_entities([MessageEntity.TEXT_MENTION, MessageEntity.MENTION])
        for ent in entities:
            if ent.type == MessageEntity.TEXT_MENTION:
                user_id = ent.user.id
                fst_name = ent.user.first_name

            elif ent.type == MessageEntity.MENTION:
                user_id = get_user_id(message.text[ent.offset:ent.offset + ent.length])
                if not user_id:
                    # لا ينبغي أن يحدث، لأنه لكي يصبح المستخدم AFK يجب أن يكون قد تحدث. ربما تغير اسم المستخدم؟
                    return
                chat = bot.get_chat(user_id)
                fst_name = chat.first_name

            else:
                return

            if sql.is_afk(user_id):
                user = sql.check_afk_status(user_id)
                if not user.reason:
                    res = "{} هو AFK!".format(fst_name)
                else:
                    res = "{} هو AFK! يقول السبب:\n{}".format(fst_name, user.reason)
                message.reply_text(res)


def __gdpr__(user_id):
    sql.rm_afk(user_id)


# ================== المساعدة ==================
__help__ = """
- /afk <السبب>: حدد نفسك كـ AFK.
- brb <السبب>: نفس الأمر afk - لكنه ليس أمراً رسمياً.

عندما يتم وضع علامة AFK، سيتم الرد على أي منشن برسالة تفيد بأنك غير متاح!

*الأوامر العربية (بدون /):*
afk <السبب>: تعيينك كـ AFK
معك حق <السبب>: نفس afk
"""

__mod_name__ = "AFK"

AFK_HANDLER = DisableAbleCommandHandler("afk", afk)
AFK_REGEX_HANDLER = DisableAbleRegexHandler("(?i)brb", afk, friendly="afk")
NO_AFK_HANDLER = MessageHandler(Filters.all & Filters.group, no_longer_afk)
AFK_REPLY_HANDLER = MessageHandler(Filters.entity(MessageEntity.MENTION) | Filters.entity(MessageEntity.TEXT_MENTION),
                                   reply_afk)

# معالجات الأوامر العربية
AFK_AR_HANDLER = DisableAbleCommandHandler(["afk", "معك حق"], afk)

dispatcher.add_handler(AFK_HANDLER, AFK_GROUP)
dispatcher.add_handler(AFK_REGEX_HANDLER, AFK_GROUP)
dispatcher.add_handler(NO_AFK_HANDLER, AFK_GROUP)
dispatcher.add_handler(AFK_REPLY_HANDLER, AFK_REPLY_GROUP)

dispatcher.add_handler(AFK_AR_HANDLER, AFK_GROUP)
