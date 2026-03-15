from typing import Optional

from telegram import Update, User, MessageEntity
from telegram.ext import ContextTypes, MessageHandler, filters

from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler, DisableAbleRegexHandler
from tg_bot.modules.sql import afk_sql as sql
from tg_bot.modules.users import get_user_id

AFK_GROUP = 7
AFK_REPLY_GROUP = 8


async def afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.effective_message.text.split(None, 1)
    if len(args) >= 2:
        reason = args[1]
    else:
        reason = ""

    sql.set_afk(update.effective_user.id, reason)
    await update.effective_message.reply_text(f"{update.effective_user.first_name} هو الآن في وضع AFK!")


async def no_longer_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user:  # تجاهل القنوات
        return

    res = sql.rm_afk(user.id)
    if res:
        await update.effective_message.reply_text(f"{update.effective_user.first_name} لم يعد في وضع AFK!")


async def reply_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                    # لا ينبغي أن يحدث، لأن المستخدم يجب أن يكون قد تحدث ليصبح AFK. ربما تغير اليوزر؟
                    return
                chat = await context.bot.get_chat(user_id)
                fst_name = chat.first_name

            else:
                return

            if sql.is_afk(user_id):
                user = sql.check_afk_status(user_id)
                if not user.reason:
                    res = f"{fst_name} في وضع AFK!"
                else:
                    res = f"{fst_name} في وضع AFK! السبب:\n{user.reason}"
                await message.reply_text(res)


def __gdpr__(user_id):
    sql.rm_afk(user_id)


__help__ = """
- /afk <السبب>: ضع نفسك في وضع AFK.
- brb <السبب>: نفس الأمر ولكن ليس أمرًا (يكتب بدون شرطة).

عند وضع AFK، سيتم الرد على أي منشن برسالة تفيد بأنك غير متاح!
"""

__mod_name__ = "AFK"

AFK_HANDLER = DisableAbleCommandHandler("afk", afk)
AFK_REGEX_HANDLER = DisableAbleRegexHandler(r"(?i)brb", afk, friendly="afk")
NO_AFK_HANDLER = MessageHandler(filters.ALL & filters.ChatType.GROUPS, no_longer_afk)
AFK_REPLY_HANDLER = MessageHandler(
    filters.Entity(MessageEntity.MENTION) | filters.Entity(MessageEntity.TEXT_MENTION),
    reply_afk
)

dispatcher.add_handler(AFK_HANDLER, AFK_GROUP)
dispatcher.add_handler(AFK_REGEX_HANDLER, AFK_GROUP)
dispatcher.add_handler(NO_AFK_HANDLER, AFK_GROUP)
dispatcher.add_handler(AFK_REPLY_HANDLER, AFK_REPLY_GROUP)
