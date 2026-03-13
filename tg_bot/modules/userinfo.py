import html
from typing import Optional, List

from telegram import Message, Update, Bot, User
from telegram import ParseMode, MAX_MESSAGE_LENGTH
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown

import tg_bot.modules.sql.userinfo_sql as sql
from tg_bot import dispatcher, SUDO_USERS
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.extraction import extract_user


@run_async
def about_me(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    user_id = extract_user(message, args)

    if user_id:
        user = bot.get_chat(user_id)
    else:
        user = message.from_user

    info = sql.get_user_me_info(user.id)

    if info:
        update.effective_message.reply_text("*{}*:\n{}".format(user.first_name, escape_markdown(info)),
                                            parse_mode=ParseMode.MARKDOWN)
    elif message.reply_to_message:
        username = message.reply_to_message.from_user.first_name
        update.effective_message.reply_text(username + " لم يقم بتعيين معلومات عن نفسه بعد!")
    else:
        update.effective_message.reply_text("لم تقم بتعيين معلومات عن نفسك بعد!")


@run_async
def set_about_me(bot: Bot, update: Update):
    message = update.effective_message
    user_id = message.from_user.id
    text = message.text
    info = text.split(None, 1)
    if len(info) == 2:
        if len(info[1]) < MAX_MESSAGE_LENGTH // 4:
            sql.set_user_me_info(user_id, info[1])
            message.reply_text("تم تحديث معلوماتك!")
        else:
            message.reply_text(
                "معلوماتك يجب أن تكون أقل من {} حرفاً! لديك {}.".format(MAX_MESSAGE_LENGTH // 4, len(info[1])))


@run_async
def about_bio(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    user_id = extract_user(message, args)
    if user_id:
        user = bot.get_chat(user_id)
    else:
        user = message.from_user

    info = sql.get_user_bio(user.id)

    if info:
        update.effective_message.reply_text("*{}*:\n{}".format(user.first_name, escape_markdown(info)),
                                            parse_mode=ParseMode.MARKDOWN)
    elif message.reply_to_message:
        username = user.first_name
        update.effective_message.reply_text("{} لم يتم تعيين سيرة ذاتية له بعد!".format(username))
    else:
        update.effective_message.reply_text("لم يتم تعيين سيرة ذاتية لك بعد!")


@run_async
def set_about_bio(bot: Bot, update: Update):
    message = update.effective_message
    sender = update.effective_user
    if message.reply_to_message:
        repl_message = message.reply_to_message
        user_id = repl_message.from_user.id
        if user_id == message.from_user.id:
            message.reply_text("لا يمكنك تعيين سيرتك الذاتية بنفسك! أنت تحت رحمة الآخرين هنا...")
            return
        elif user_id == bot.id and sender.id not in SUDO_USERS:
            message.reply_text("همم... نعم، أنا أثق فقط بمستخدمي sudo لتعيين سيرتي الذاتية.")
            return

        text = message.text
        bio = text.split(None, 1)
        if len(bio) == 2:
            if len(bio[1]) < MAX_MESSAGE_LENGTH // 4:
                sql.set_user_bio(user_id, bio[1])
                message.reply_text("تم تحديث السيرة الذاتية لـ {}!".format(repl_message.from_user.first_name))
            else:
                message.reply_text(
                    "يجب أن تكون السيرة الذاتية أقل من {} حرفاً! لقد حاولت تعيين {}.".format(
                        MAX_MESSAGE_LENGTH // 4, len(bio[1])))
    else:
        message.reply_text("قم بالرد على رسالة شخص ما لتعيين سيرته الذاتية!")


def __user_info__(user_id):
    bio = html.escape(sql.get_user_bio(user_id) or "")
    me = html.escape(sql.get_user_me_info(user_id) or "")
    if bio and me:
        return "<b>عن المستخدم:</b>\n{me}\n<b>ما يقوله الآخرون:</b>\n{bio}".format(me=me, bio=bio)
    elif bio:
        return "<b>ما يقوله الآخرون:</b>\n{bio}\n".format(me=me, bio=bio)
    elif me:
        return "<b>عن المستخدم:</b>\n{me}".format(me=me, bio=bio)
    else:
        return ""


def __gdpr__(user_id):
    sql.clear_user_info(user_id)
    sql.clear_user_bio(user_id)


# ================== المساعدة ==================
__help__ = """
- /setbio <نص>: بالرد على رسالة، سيحفظ السيرة الذاتية لمستخدم آخر.
- /bio: يعرض سيرتك الذاتية أو سيرة مستخدم آخر (لا يمكنك تعيينها لنفسك).
- /setme <نص>: يحدد معلوماتك الشخصية.
- /me: يعرض معلوماتك أو معلومات مستخدم آخر.

*الأوامر العربية (بدون /):*
تعيين سيرتي <نص>: تعيين معلوماتك الشخصية
سيرتي: عرض معلوماتك
تعيين سيرة <نص> <بالرد>: تعيين سيرة ذاتية لمستخدم آخر بالرد عليه
سيرة <بالرد>: عرض سيرة مستخدم
"""

__mod_name__ = "السيرة الذاتية"

SET_BIO_HANDLER = DisableAbleCommandHandler("setbio", set_about_bio)
GET_BIO_HANDLER = DisableAbleCommandHandler("bio", about_bio, pass_args=True)
SET_ABOUT_HANDLER = DisableAbleCommandHandler("setme", set_about_me)
GET_ABOUT_HANDLER = DisableAbleCommandHandler("me", about_me, pass_args=True)

# معالجات الأوامر العربية
SET_ABOUT_AR_HANDLER = CommandHandler("تعيين سيرتي", set_about_me)
GET_ABOUT_AR_HANDLER = CommandHandler("سيرتي", lambda b,u: about_me(b,u,args=[]))
SET_BIO_AR_HANDLER = CommandHandler("تعيين سيرة", set_about_bio)
GET_BIO_AR_HANDLER = CommandHandler("سيرة", lambda b,u: about_bio(b,u,args=[]))

dispatcher.add_handler(SET_BIO_HANDLER)
dispatcher.add_handler(GET_BIO_HANDLER)
dispatcher.add_handler(SET_ABOUT_HANDLER)
dispatcher.add_handler(GET_ABOUT_HANDLER)

dispatcher.add_handler(SET_ABOUT_AR_HANDLER)
dispatcher.add_handler(GET_ABOUT_AR_HANDLER)
dispatcher.add_handler(SET_BIO_AR_HANDLER)
dispatcher.add_handler(GET_BIO_AR_HANDLER)
