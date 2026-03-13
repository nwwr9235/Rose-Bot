import html
import re

from feedparser import parse
from telegram import ParseMode, constants
from telegram.ext import CommandHandler, MessageHandler, Filters

from tg_bot import dispatcher, updater
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.sql import rss_sql as sql


def show_url(bot, update, args):
    tg_chat_id = str(update.effective_chat.id)

    if len(args) >= 1:
        tg_feed_link = args[0]
        link_processed = parse(tg_feed_link)

        if link_processed.bozo == 0:
            feed_title = link_processed.feed.get("title", default="غير معروف")
            feed_description = "<i>{}</i>".format(
                re.sub('<[^<]+?>', '', link_processed.feed.get("description", default="غير معروف")))
            feed_link = link_processed.feed.get("link", default="غير معروف")

            feed_message = "<b>عنوان التغذية:</b> \n{}" \
                           "\n\n<b>وصف التغذية:</b> \n{}" \
                           "\n\n<b>رابط التغذية:</b> \n{}".format(html.escape(feed_title),
                                                               feed_description,
                                                               html.escape(feed_link))

            if len(link_processed.entries) >= 1:
                entry_title = link_processed.entries[0].get("title", default="غير معروف")
                entry_description = "<i>{}</i>".format(
                    re.sub('<[^<]+?>', '', link_processed.entries[0].get("description", default="غير معروف")))
                entry_link = link_processed.entries[0].get("link", default="غير معروف")

                entry_message = "\n\n<b>عنوان المدخلة:</b> \n{}" \
                                "\n\n<b>وصف المدخلة:</b> \n{}" \
                                "\n\n<b>رابط المدخلة:</b> \n{}".format(html.escape(entry_title),
                                                                     entry_description,
                                                                     html.escape(entry_link))
                final_message = feed_message + entry_message

                bot.send_message(chat_id=tg_chat_id, text=final_message, parse_mode=ParseMode.HTML)
            else:
                bot.send_message(chat_id=tg_chat_id, text=feed_message, parse_mode=ParseMode.HTML)
        else:
            update.effective_message.reply_text("هذا الرابط ليس رابط تغذية RSS")
    else:
        update.effective_message.reply_text("الرابط مفقود")


def list_urls(bot, update):
    tg_chat_id = str(update.effective_chat.id)

    user_data = sql.get_urls(tg_chat_id)

    links_list = [row.feed_link for row in user_data]

    final_content = "\n\n".join(links_list)

    if len(final_content) == 0:
        bot.send_message(chat_id=tg_chat_id, text="هذه الدردشة غير مشتركة في أي روابط")
    elif len(final_content) <= constants.MAX_MESSAGE_LENGTH:
        bot.send_message(chat_id=tg_chat_id, text="هذه الدردشة مشتركة في الروابط التالية:\n" + final_content)
    else:
        bot.send_message(chat_id=tg_chat_id, parse_mode=ParseMode.HTML,
                         text="<b>تحذير:</b> الرسالة طويلة جداً ولا يمكن إرسالها")


@user_admin
def add_url(bot, update, args):
    if len(args) >= 1:
        chat = update.effective_chat

        tg_chat_id = str(update.effective_chat.id)

        tg_feed_link = args[0]

        link_processed = parse(tg_feed_link)

        if link_processed.bozo == 0:
            if len(link_processed.entries[0]) >= 1:
                tg_old_entry_link = link_processed.entries[0].link
            else:
                tg_old_entry_link = ""

            row = sql.check_url_availability(tg_chat_id, tg_feed_link)

            if row:
                update.effective_message.reply_text("هذا الرابط تمت إضافته بالفعل")
            else:
                sql.add_url(tg_chat_id, tg_feed_link, tg_old_entry_link)

                update.effective_message.reply_text("تمت إضافة الرابط إلى الاشتراكات")
        else:
            update.effective_message.reply_text("هذا الرابط ليس رابط تغذية RSS")
    else:
        update.effective_message.reply_text("الرابط مفقود")


@user_admin
def remove_url(bot, update, args):
    if len(args) >= 1:
        tg_chat_id = str(update.effective_chat.id)

        tg_feed_link = args[0]

        link_processed = parse(tg_feed_link)

        if link_processed.bozo == 0:
            user_data = sql.check_url_availability(tg_chat_id, tg_feed_link)

            if user_data:
                sql.remove_url(tg_chat_id, tg_feed_link)

                update.effective_message.reply_text("تمت إزالة الرابط من الاشتراكات")
            else:
                update.effective_message.reply_text("لم تشترك في هذا الرابط بعد")
        else:
            update.effective_message.reply_text("هذا الرابط ليس رابط تغذية RSS")
    else:
        update.effective_message.reply_text("الرابط مفقود")


def rss_update(bot, job):
    user_data = sql.get_all()

    for row in user_data:
        row_id = row.id
        tg_chat_id = row.chat_id
        tg_feed_link = row.feed_link

        feed_processed = parse(tg_feed_link)

        tg_old_entry_link = row.old_entry_link

        new_entry_links = []
        new_entry_titles = []

        for entry in feed_processed.entries:
            if entry.link != tg_old_entry_link:
                new_entry_links.append(entry.link)
                new_entry_titles.append(entry.title)
            else:
                break

        if new_entry_links:
            sql.update_url(row_id, new_entry_links)
        else:
            pass

        if len(new_entry_links) < 5:
            for link, title in zip(reversed(new_entry_links), reversed(new_entry_titles)):
                final_message = "<b>{}</b>\n\n{}".format(html.escape(title), html.escape(link))

                if len(final_message) <= constants.MAX_MESSAGE_LENGTH:
                    bot.send_message(chat_id=tg_chat_id, text=final_message, parse_mode=ParseMode.HTML)
                else:
                    bot.send_message(chat_id=tg_chat_id, text="<b>تحذير:</b> الرسالة طويلة جداً ولا يمكن إرسالها",
                                     parse_mode=ParseMode.HTML)
        else:
            for link, title in zip(reversed(new_entry_links[-5:]), reversed(new_entry_titles[-5:])):
                final_message = "<b>{}</b>\n\n{}".format(html.escape(title), html.escape(link))

                if len(final_message) <= constants.MAX_MESSAGE_LENGTH:
                    bot.send_message(chat_id=tg_chat_id, text=final_message, parse_mode=ParseMode.HTML)
                else:
                    bot.send_message(chat_id=tg_chat_id, text="<b>تحذير:</b> الرسالة طويلة جداً ولا يمكن إرسالها",
                                     parse_mode=ParseMode.HTML)

            bot.send_message(chat_id=tg_chat_id, parse_mode=ParseMode.HTML,
                             text="<b>تحذير: </b>{} تكراراً تم تجاهلها لمنع البريد المزعج"
                             .format(len(new_entry_links) - 5))


def rss_set(bot, job):
    user_data = sql.get_all()

    for row in user_data:
        row_id = row.id
        tg_feed_link = row.feed_link
        tg_old_entry_link = row.old_entry_link

        feed_processed = parse(tg_feed_link)

        new_entry_links = []
        new_entry_titles = []

        for entry in feed_processed.entries:
            if entry.link != tg_old_entry_link:
                new_entry_links.append(entry.link)
                new_entry_titles.append(entry.title)
            else:
                break

        if new_entry_links:
            sql.update_url(row_id, new_entry_links)


# ================== المساعدة ==================
__help__ = """
- /addrss <رابط>: إضافة رابط RSS إلى الاشتراكات.
- /removerss <رابط>: إزالة رابط RSS من الاشتراكات.
- /rss <رابط>: عرض بيانات الرابط وآخر مدخلة، لأغراض الاختبار.
- /listrss: عرض قائمة تغذيات RSS التي تشترك فيها الدردشة حالياً.

ملاحظة: في المجموعات، يمكن للمشرفين فقط إضافة/إزالة روابط RSS إلى اشتراكات المجموعة.

*الأوامر العربية (بدون /):*
إضافة RSS <الرابط>: إضافة رابط RSS
إزالة RSS <الرابط>: إزالة رابط RSS
عرض RSS <الرابط>: عرض معلومات الرابط
قائمة RSS: عرض قائمة الروابط المشترك بها
"""

__mod_name__ = "تغذية RSS"

job = updater.job_queue

job_rss_set = job.run_once(rss_set, 5)
job_rss_update = job.run_repeating(rss_update, interval=60, first=60)
job_rss_set.enabled = True
job_rss_update.enabled = True

SHOW_URL_HANDLER = CommandHandler("rss", show_url, pass_args=True)
ADD_URL_HANDLER = CommandHandler("addrss", add_url, pass_args=True)
REMOVE_URL_HANDLER = CommandHandler("removerss", remove_url, pass_args=True)
LIST_URLS_HANDLER = CommandHandler("listrss", list_urls)

# معالجات الأوامر العربية
SHOW_URL_AR_HANDLER = CommandHandler("عرض RSS", show_url, pass_args=True)
ADD_URL_AR_HANDLER = CommandHandler("إضافة RSS", add_url, pass_args=True)
REMOVE_URL_AR_HANDLER = CommandHandler("إزالة RSS", remove_url, pass_args=True)
LIST_URLS_AR_HANDLER = CommandHandler("قائمة RSS", list_urls)

dispatcher.add_handler(SHOW_URL_HANDLER)
dispatcher.add_handler(ADD_URL_HANDLER)
dispatcher.add_handler(REMOVE_URL_HANDLER)
dispatcher.add_handler(LIST_URLS_HANDLER)

dispatcher.add_handler(SHOW_URL_AR_HANDLER)
dispatcher.add_handler(ADD_URL_AR_HANDLER)
dispatcher.add_handler(REMOVE_URL_AR_HANDLER)
dispatcher.add_handler(LIST_URLS_AR_HANDLER)
