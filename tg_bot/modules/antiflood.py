import html
from typing import Optional, List

from telegram import Update, Chat, User, Message
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes, MessageHandler, CommandHandler, filters
from telegram.helpers import mention_html

from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.chat_status import is_user_admin, user_admin, can_restrict
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import antiflood_sql as sql

FLOOD_GROUP = 3


@loggable
async def check_flood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user = update.effective_user
    chat = update.effective_chat
    msg = update.effective_message

    if not user:  # تجاهل القنوات
        return ""

    # تجاهل المشرفين
    if await is_user_admin(chat, user.id):
        sql.update_flood(chat.id, None)
        return ""

    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    try:
        await context.bot.ban_chat_member(chat.id, user.id)
        await msg.reply_text("تقوم بالتكرار... تم حظرك.")

        return f"<b>{html.escape(chat.title)}:</b>" \
               f"\n#BANNED" \
               f"\n<b>User:</b> {mention_html(user.id, user.first_name)}" \
               f"\nFlooded the group."

    except BadRequest:
        await msg.reply_text("لا أستطيع حظر الأشخاص هنا، أعطني الصلاحيات أولاً! حتى ذلك الحين، سأقوم بتعطيل مكافحة التكرار.")
        sql.set_flood(chat.id, 0)
        return f"<b>{html.escape(chat.title)}:</b>" \
               f"\n#INFO" \
               f"\nليس لدي صلاحيات الحظر، لذا تم تعطيل مكافحة التكرار تلقائيًا."


@user_admin
@can_restrict
@loggable
async def set_flood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    args = context.args

    if len(args) >= 1:
        val = args[0].lower()
        if val == "off" or val == "no" or val == "0":
            sql.set_flood(chat.id, 0)
            await message.reply_text("تم تعطيل مكافحة التكرار.")
            return f"<b>{html.escape(chat.title)}:</b>" \
                   f"\n#SETFLOOD" \
                   f"\n<b>Admin:</b> {mention_html(user.id, user.first_name)}" \
                   f"\nتم تعطيل مكافحة التكرار."

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat.id, 0)
                await message.reply_text("تم تعطيل مكافحة التكرار.")
                return f"<b>{html.escape(chat.title)}:</b>" \
                       f"\n#SETFLOOD" \
                       f"\n<b>Admin:</b> {mention_html(user.id, user.first_name)}" \
                       f"\nتم تعطيل مكافحة التكرار."

            elif amount < 3:
                await message.reply_text("يجب أن تكون قيمة مكافحة التكرار إما 0 (معطل) أو رقم أكبر من 3!")
                return ""

            else:
                sql.set_flood(chat.id, amount)
                await message.reply_text(f"تم تحديث مكافحة التكرار وتعيينها إلى {amount}")
                return f"<b>{html.escape(chat.title)}:</b>" \
                       f"\n#SETFLOOD" \
                       f"\n<b>Admin:</b> {mention_html(user.id, user.first_name)}" \
                       f"\nتم تعيين مكافحة التكرار إلى <code>{amount}</code>."

        else:
            await message.reply_text("معامل غير معروف - الرجاء استخدام رقم، أو 'off'، أو 'no'.")

    return ""


async def flood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    limit = sql.get_flood_limit(chat.id)
    if limit == 0:
        await update.effective_message.reply_text("أنا لا أطبق مكافحة التكرار حاليًا!")
    else:
        await update.effective_message.reply_text(
            f"أقوم حاليًا بحظر المستخدمين إذا أرسلوا أكثر من {limit} رسالة متتالية.")


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


async def __chat_settings__(chat_id: int, user_id: int) -> str:
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        return "*لا* يتم تطبيق مكافحة التكرار حاليًا."
    else:
        return f"مكافحة التكرار مضبوطة على `{limit}` رسالة."


__help__ = """
- /flood: الحصول على إعداد مكافحة التكرار الحالي

*للمشرفين فقط:*
- /setflood <رقم/'no'/'off'>: تفعيل أو تعطيل مكافحة التكرار
"""

__mod_name__ = "مكافحة التكرار"

FLOOD_BAN_HANDLER = MessageHandler(filters.ALL & ~filters.StatusUpdate.ALL & filters.ChatType.GROUPS, check_flood)
SET_FLOOD_HANDLER = CommandHandler("setflood", set_flood, filters=filters.ChatType.GROUPS)
FLOOD_HANDLER = CommandHandler("flood", flood, filters=filters.ChatType.GROUPS)

dispatcher.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(FLOOD_HANDLER)
