import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, ParseMode
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, RegexHandler, run_async, Filters, MessageHandler
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.helper_funcs.chat_status import user_not_admin, user_admin
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import reporting_sql as sql

REPORT_GROUP = 5


@run_async
@user_admin
def report_setting(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat
    msg = update.effective_message

    if chat.type == chat.PRIVATE:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_user_setting(chat.id, True)
                msg.reply_text("تم تشغيل الإبلاغ! سيتم إعلامك عندما يبلغ شخص ما.")

            elif args[0] in ("no", "off"):
                sql.set_user_setting(chat.id, False)
                msg.reply_text("تم إيقاف الإبلاغ! لن تستقبل أي تقارير.")
        else:
            msg.reply_text("تفضيل الإبلاغ الحالي لديك هو: `{}`".format(sql.user_should_report(chat.id)),
                           parse_mode=ParseMode.MARKDOWN)

    else:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_chat_setting(chat.id, True)
                msg.reply_text("تم تشغيل الإبلاغ! سيتم إعلام المشرفين الذين فعّلوا الإبلاغ عند استخدام /report أو @admin.")

            elif args[0] in ("no", "off"):
                sql.set_chat_setting(chat.id, False)
                msg.reply_text("تم إيقاف الإبلاغ! لن يتم إعلام أي مشرف عند استخدام /report أو @admin.")
        else:
            msg.reply_text("الإعداد الحالي لهذه الدردشة هو: `{}`".format(sql.chat_should_report(chat.id)),
                           parse_mode=ParseMode.MARKDOWN)


@run_async
@user_not_admin
@loggable
def report(bot: Bot, update: Update) -> str:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if chat and message.reply_to_message and sql.chat_should_report(chat.id):
        reported_user = message.reply_to_message.from_user
        chat_name = chat.title or chat.first or chat.username
        admin_list = chat.get_administrators()

        if chat.username and chat.type == Chat.SUPERGROUP:
            msg = "<b>{}:</b>" \
                  "\n<b>المستخدم المُبلغ عنه:</b> {} (<code>{}</code>)" \
                  "\n<b>أبلغ بواسطة:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                                      mention_html(
                                                                          reported_user.id,
                                                                          reported_user.first_name),
                                                                      reported_user.id,
                                                                      mention_html(user.id,
                                                                                   user.first_name),
                                                                      user.id)
            link = "\n<b>الرابط:</b> " \
                   "<a href=\"http://telegram.me/{}/{}\">اضغط هنا</a>".format(chat.username, message.message_id)

            should_forward = False

        else:
            msg = "{} يستدعي المشرفين في \"{}\"!".format(mention_html(user.id, user.first_name),
                                                               html.escape(chat_name))
            link = ""
            should_forward = True

        for admin in admin_list:
            if admin.user.is_bot:
                continue

            if sql.user_should_report(admin.user.id):
                try:
                    bot.send_message(admin.user.id, msg + link, parse_mode=ParseMode.HTML)

                    if should_forward:
                        message.reply_to_message.forward(admin.user.id)

                        if len(message.text.split()) > 1:
                            message.forward(admin.user.id)

                except Unauthorized:
                    pass
                except BadRequest as excp:
                    LOGGER.exception("استثناء أثناء الإبلاغ عن مستخدم")
        return msg

    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "هذه الدردشة مضبوطة لإرسال تقارير المستخدمين إلى المشرفين، عبر /report و @admin: `{}`".format(
        sql.chat_should_report(chat_id))


def __user_settings__(user_id):
    return "أنت تستقبل تقارير من الدردشات التي أنت مشرف فيها: `{}`.\nبدّل هذا باستخدام /reports في الخاص.".format(
        sql.user_should_report(user_id))


# ================== المساعدة ==================
__mod_name__ = "الإبلاغ"

__help__ = """
- /report <السبب>: قم بالرد على رسالة للإبلاغ عنها للمشرفين.
- @admin: قم بالرد على رسالة للإبلاغ عنها للمشرفين.
ملاحظة: لن يتم تفعيل أي من هذه إذا استخدمها المشرفون.

*للمشرفين فقط:*
- /reports <on/off>: تغيير إعداد الإبلاغ، أو عرض الحالة الحالية.
   - إذا تم في الخاص، يبدل حالتك.
   - إذا تم في الدردشة، يبدل حالة تلك الدردشة.

*الأوامر العربية (بدون /):*
تبليغ <بالرد>: الإبلاغ عن رسالة للمشرفين
إعدادات التبليغ: عرض إعدادات الإبلاغ الحالية
تشغيل التبليغ: تفعيل الإبلاغ (للمشرفين)
إيقاف التبليغ: تعطيل الإبلاغ (للمشرفين)
"""

REPORT_HANDLER = CommandHandler("report", report, filters=Filters.group)
SETTING_HANDLER = CommandHandler("reports", report_setting, pass_args=True)
ADMIN_REPORT_HANDLER = RegexHandler("(?i)@admin(s)?", report)

# معالجات الأوامر العربية
REPORT_AR_HANDLER = CommandHandler("تبليغ", report, filters=Filters.group)
REPORT_SETTING_AR_HANDLER = CommandHandler("إعدادات التبليغ", lambda b,u: report_setting(b,u,args=[]), filters=Filters.group)
REPORT_SETTING_ON_AR_HANDLER = CommandHandler("تشغيل التبليغ", lambda b,u: report_setting(b,u,args=["on"]), filters=Filters.group)
REPORT_SETTING_OFF_AR_HANDLER = CommandHandler("إيقاف التبليغ", lambda b,u: report_setting(b,u,args=["off"]), filters=Filters.group)

dispatcher.add_handler(REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(ADMIN_REPORT_HANDLER, REPORT_GROUP)
dispatcher.add_handler(SETTING_HANDLER)

dispatcher.add_handler(REPORT_AR_HANDLER, REPORT_GROUP)
dispatcher.add_handler(REPORT_SETTING_AR_HANDLER)
dispatcher.add_handler(REPORT_SETTING_ON_AR_HANDLER)
dispatcher.add_handler(REPORT_SETTING_OFF_AR_HANDLER)
