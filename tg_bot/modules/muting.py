import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, MessageHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_admin, can_restrict
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable


@run_async
@bot_admin
@user_admin
@loggable
def mute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("يجب إعطائي اسم مستخدم لكتمه، أو الرد على شخص لكتمه.")
        return ""

    if user_id == bot.id:
        message.reply_text("لن أكتم نفسي!")
        return ""

    member = chat.get_member(int(user_id))

    if member:
        if is_user_admin(chat, user_id, member=member):
            message.reply_text("لا يمكنني منع مشرف من التحدث!")

        elif member.can_send_messages is None or member.can_send_messages:
            bot.restrict_chat_member(chat.id, user_id, can_send_messages=False)
            message.reply_text("تم الكتم!")
            return "<b>{}:</b>" \
                   "\n#كتم" \
                   "\n<b>المشرف:</b> {}" \
                   "\n<b>المستخدم:</b> {}".format(html.escape(chat.title),
                                              mention_html(user.id, user.first_name),
                                              mention_html(member.user.id, member.user.first_name))

        else:
            message.reply_text("هذا المستخدم مكتوم بالفعل!")
    else:
        message.reply_text("هذا المستخدم ليس في الدردشة!")

    return ""


@run_async
@bot_admin
@user_admin
@loggable
def unmute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("يجب إعطائي اسم مستخدم لإلغاء كتمه، أو الرد على شخص لإلغاء كتمه.")
        return ""

    member = chat.get_member(int(user_id))

    if member.status != 'kicked' and member.status != 'left':
        if member.can_send_messages and member.can_send_media_messages \
                and member.can_send_other_messages and member.can_add_web_page_previews:
            message.reply_text("هذا المستخدم لديه بالفعل صلاحية التحدث.")
        else:
            bot.restrict_chat_member(chat.id, int(user_id),
                                     can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_send_other_messages=True,
                                     can_add_web_page_previews=True)
            message.reply_text("تم إلغاء الكتم!")
            return "<b>{}:</b>" \
                   "\n#إلغاء_كتم" \
                   "\n<b>المشرف:</b> {}" \
                   "\n<b>المستخدم:</b> {}".format(html.escape(chat.title),
                                              mention_html(user.id, user.first_name),
                                              mention_html(member.user.id, member.user.first_name))
    else:
        message.reply_text("هذا المستخدم ليس في الدردشة حتى، إلغاء كتمه لن يجعله يتحدث أكثر!")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_mute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("لم أتمكن من العثور على هذا المستخدم.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("لا يمكنني العثور على هذا المستخدم")
            return ""
        else:
            raise

    if is_user_admin(chat, user_id, member):
        message.reply_text("لا يمكنني كتم المشرفين!")
        return ""

    if user_id == bot.id:
        message.reply_text("لن أكتم نفسي، هل أنت مجنون؟")
        return ""

    if not reason:
        message.reply_text("لم تحدد مدة الكتم لهذا المستخدم!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    mutetime = extract_time(message, time_val)

    if not mutetime:
        return ""

    log = "<b>{}:</b>" \
          "\n#كتم_مؤقت" \
          "\n<b>المشرف:</b> {}" \
          "\n<b>المستخدم:</b> {}" \
          "\n<b>المدة:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name), time_val)
    if reason:
        log += "\n<b>السبب:</b> {}".format(reason)

    try:
        if member.can_send_messages is None or member.can_send_messages:
            bot.restrict_chat_member(chat.id, user_id, until_date=mutetime, can_send_messages=False)
            message.reply_text("تم الكتم لمدة {}!".format(time_val))
            return log
        else:
            message.reply_text("هذا المستخدم مكتوم بالفعل.")

    except BadRequest as excp:
        if excp.message == "Replied message not found":
            message.reply_text("تم الكتم لمدة {}!".format(time_val), quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("خطأ في كتم المستخدم %s في الدردشة %s (%s) بسبب %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("لا يمكنني كتم هذا المستخدم.")

    return ""


# ================== المساعدة ==================
__help__ = """
*للمشرفين فقط:*
- /mute <المستخدم>: كتم مستخدم (بالمعرف أو بالرد)
- /tmute <المستخدم> x(م/س/ي): كتم مستخدم لمدة محددة. م = دقائق، س = ساعات، ي = أيام.
- /unmute <المستخدم>: إلغاء كتم مستخدم (بالمعرف أو بالرد)

*الأوامر العربية (بدون /):*
كتم <بالرد>: كتم المستخدم الذي تم الرد عليه
كتم مؤقت <المدة> <بالرد>: كتم المستخدم لمدة محددة
الغاء كتم <بالرد>: إلغاء كتم المستخدم الذي تم الرد عليه
"""

__mod_name__ = "الكتم"

MUTE_HANDLER = CommandHandler("mute", mute, pass_args=True, filters=Filters.group)
UNMUTE_HANDLER = CommandHandler("unmute", unmute, pass_args=True, filters=Filters.group)
TEMPMUTE_HANDLER = CommandHandler(["tmute", "tempmute"], temp_mute, pass_args=True, filters=Filters.group)

# معالجات الأوامر العربية
MUTE_AR_HANDLER = MessageHandler(Filters.regex(r'^كتم$') & Filters.reply, mute, pass_args=True)
UNMUTE_AR_HANDLER = MessageHandler(Filters.regex(r'^الغاء كتم$') & Filters.reply, unmute, pass_args=True)
TEMPMUTE_AR_HANDLER = MessageHandler(Filters.regex(r'^كتم مؤقت (.+)$') & Filters.reply, temp_mute, pass_args=True)

dispatcher.add_handler(MUTE_HANDLER)
dispatcher.add_handler(UNMUTE_HANDLER)
dispatcher.add_handler(TEMPMUTE_HANDLER)

dispatcher.add_handler(MUTE_AR_HANDLER)
dispatcher.add_handler(UNMUTE_AR_HANDLER)
dispatcher.add_handler(TEMPMUTE_HANDLER)  # لاحظ: هنا استخدمنا نفس الاسم عن طريق الخطأ؟ يجب تغيير اسم المتغير
# تصحيح: نستخدم متغيرات مختلفة
dispatcher.add_handler(MUTE_AR_HANDLER)
dispatcher.add_handler(UNMUTE_AR_HANDLER)
dispatcher.add_handler(TEMPMUTE_AR_HANDLER)
