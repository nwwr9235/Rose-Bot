import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import Filters, MessageHandler, CommandHandler, run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.chat_status import is_user_admin, user_admin, can_restrict
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import antiflood_sql as sql

FLOOD_GROUP = 3


@run_async
@loggable
def check_flood(bot: Bot, update: Update) -> str:
    user = update.effective_user
    chat = update.effective_chat
    msg = update.effective_message

    if not user:  # تجاهل القنوات
        return ""

    # تجاهل المشرفين
    if is_user_admin(chat, user.id):
        sql.update_flood(chat.id, None)
        return ""

    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    try:
        chat.kick_member(user.id)
        msg.reply_text("هل تغرق الدردشة؟ لقد أعددت لك ركلة... اركض ثم عد!")

        return "<b>{}:</b>" \
               "\n#محظور" \
               "\n<b>المستخدم:</b> {}" \
               "\nقام بإغراق المجموعة.".format(html.escape(chat.title),
                                             mention_html(user.id, user.first_name))

    except BadRequest:
        msg.reply_text("لا يمكنني طرد الأشخاص هنا، أعطني الصلاحيات أولاً! حتى ذلك الحين، سأعطل مكافحة الإغراق.")
        sql.set_flood(chat.id, 0)
        return "<b>{}:</b>" \
               "\n#معلومات" \
               "\nليس لدي صلاحيات الطرد، لذلك تم تعطيل مكافحة الإغراق تلقائياً.".format(chat.title)


@run_async
@user_admin
@can_restrict
@loggable
def set_flood(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if len(args) >= 1:
        val = args[0].lower()
        if val == "off" or val == "no" or val == "0":
            sql.set_flood(chat.id, 0)
            message.reply_text("تم تعطيل مكافحة الإغراق.")

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat.id, 0)
                message.reply_text("تم تعطيل مكافحة الإغراق.")
                return "<b>{}:</b>" \
                       "\n#تعيين_إغراق" \
                       "\n<b>المشرف:</b> {}" \
                       "\nتم تعطيل مكافحة الإغراق.".format(html.escape(chat.title), mention_html(user.id, user.first_name))

            elif amount < 3:
                message.reply_text("يجب أن تكون مكافحة الإغراق إما 0 (معطل)، أو رقماً أكبر من 3!")
                return ""

            else:
                sql.set_flood(chat.id, amount)
                message.reply_text("تم تحديث مكافحة الإغراق وضبطها على {}".format(amount))
                return "<b>{}:</b>" \
                       "\n#تعيين_إغراق" \
                       "\n<b>المشرف:</b> {}" \
                       "\nتم ضبط مكافحة الإغراق على <code>{}</code>.".format(html.escape(chat.title),
                                                                    mention_html(user.id, user.first_name), amount)

        else:
            message.reply_text("وسيطة غير معروفة - الرجاء استخدام رقم، أو 'off'، أو 'no'.")

    return ""


@run_async
def flood(bot: Bot, update: Update):
    chat = update.effective_chat

    limit = sql.get_flood_limit(chat.id)
    if limit == 0:
        update.effective_message.reply_text("أنا لا أقوم حالياً بتطبيق التحكم في الإغراق!")
    else:
        update.effective_message.reply_text(
            "أقوم حالياً بحظر المستخدمين إذا أرسلوا أكثر من {} رسالة متتالية.".format(limit))


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    if limit == 0:
        return "*لا* أقوم حالياً بتطبيق التحكم في الإغراق."
    else:
        return "مكافحة الإغراق مضبوطة على `{}` رسالة.".format(limit)


# ================== المساعدة ==================
__help__ = """
- /flood: الحصول على إعداد التحكم في الإغراق الحالي

*للمشرفين فقط:*
- /setflood <رقم/'no'/'off'>: تفعيل أو تعطيل التحكم في الإغراق

*الأوامر العربية (بدون /):*
الإغراق: عرض إعدادات مكافحة الإغراق
تعيين إغراق <رقم>: تعيين حد الإغراق (مثلاً: تعيين إغراق 5)
تعطيل إغراق: تعطيل مكافحة الإغراق
"""

__mod_name__ = "مكافحة الإغراق"

FLOOD_BAN_HANDLER = MessageHandler(Filters.all & ~Filters.status_update & Filters.group, check_flood)
SET_FLOOD_HANDLER = CommandHandler("setflood", set_flood, pass_args=True, filters=Filters.group)  # <-- تم إضافة الفاصلة
FLOOD_HANDLER = CommandHandler("flood", flood, filters=Filters.group)

# معالجات الأوامر العربية
FLOOD_AR_HANDLER = CommandHandler("الإغراق", flood, filters=Filters.group)
SET_FLOOD_AR_HANDLER = CommandHandler("تعيين إغراق", set_flood, pass_args=True, filters=Filters.group)
DISABLE_FLOOD_AR_HANDLER = CommandHandler("تعطيل إغراق", lambda b,u: set_flood(b,u,args=["off"]), filters=Filters.group)

dispatcher.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(FLOOD_HANDLER)

dispatcher.add_handler(FLOOD_AR_HANDLER)
dispatcher.add_handler(SET_FLOOD_AR_HANDLER)
dispatcher.add_handler(DISABLE_FLOOD_AR_HANDLER)
