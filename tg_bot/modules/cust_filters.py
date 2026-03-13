import re
from typing import Optional

import telegram
from telegram import ParseMode, InlineKeyboardMarkup, Message, Chat, InlineKeyboardButton
from telegram import Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, DispatcherHandlerStop, run_async, Filters, CallbackQueryHandler
from telegram.utils.helpers import escape_markdown

from tg_bot import dispatcher, LOGGER, BMERNU_SCUT_SRELFTI, SUDO_USERS
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.helper_funcs.extraction import extract_text
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import build_keyboard
from tg_bot.modules.helper_funcs.string_handling import split_quotes, button_markdown_parser
from tg_bot.modules.sql import cust_filters_sql as sql

from tg_bot.modules.connection import connected

HANDLER_GROUP = 15
BASIC_FILTER_STRING = "*عوامل التصفية في هذه الدردشة:*\n"


@run_async
def list_handlers(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user

    conn = connected(bot, update, chat, user.id, need_admin=False)
    if not conn == False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
        filter_list = f"*عوامل التصفية في {chat_name}:*\n"
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = "عوامل التصفية المحلية"
            filter_list = "*عوامل التصفية المحلية:*\n"
        else:
            chat_name = chat.title
            filter_list = "*عوامل التصفية في {}*:\n".format(chat_name)

    total_count_f_fliters = sql.num_filters_per_chat(chat_id)
    filter_list += f"**عدد عوامل التصفية**: {total_count_f_fliters}\n"

    all_handlers = sql.get_chat_triggers(chat_id)

    if not all_handlers:
        update.effective_message.reply_text("لا توجد عوامل تصفية في {}!".format(chat_name))
        return

    for keyword in all_handlers:
        entry = " - {}\n".format(escape_markdown(keyword))
        if len(entry) + len(filter_list) > telegram.MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(filter_list, parse_mode=telegram.ParseMode.MARKDOWN)
            filter_list = entry
        else:
            filter_list += entry

    if not filter_list == BASIC_FILTER_STRING:
        update.effective_message.reply_text(filter_list, parse_mode=telegram.ParseMode.MARKDOWN)


# NOT ASYNC BECAUSE DISPATCHER HANDLER RAISED
@user_admin
def filters(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    args = msg.text.split(None, 1)

    conn = connected(bot, update, chat, user.id)
    if not conn == False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = "عوامل التصفية المحلية"
        else:
            chat_name = chat.title

    if len(args) < 2:
        return

    # check irfst
    if BMERNU_SCUT_SRELFTI:
        total_fs = sql.num_filters_per_chat(chat_id)
        if total_fs >= BMERNU_SCUT_SRELFTI:
            msg.reply_text(
                f"لديك حالياً {total_fs} عامل تصفية. "
                f"الحد الأقصى المسموح به هو {BMERNU_SCUT_SRELFTI}. "
                "يجب حذف بعض عوامل التصفية قبل إضافة المزيد "
                "أو استخدم @kochufilterbot لعوامل تصفية غير محدودة."
            )
            return

    extracted = split_quotes(args[1])
    if len(extracted) < 1:
        return
    keyword = extracted[0].lower()

    is_sticker = False
    is_document = False
    is_image = False
    is_voice = False
    is_audio = False
    is_video = False
    media_caption = None
    has_caption = False
    content = None
    buttons = []

    if len(extracted) >= 2:
        offset = len(extracted[1]) - len(msg.text)
        content, buttons = button_markdown_parser(extracted[1], entities=msg.parse_entities(), offset=offset)
        content = content.strip()

    if msg.reply_to_message and msg.reply_to_message.sticker:
        content = msg.reply_to_message.sticker.file_id
        is_sticker = True

    elif msg.reply_to_message and msg.reply_to_message.document:
        offset = len(msg.reply_to_message.caption or "")
        media_caption, buttons = button_markdown_parser(msg.reply_to_message.caption, entities=msg.reply_to_message.parse_entities(), offset=offset)
        content = msg.reply_to_message.document.file_id
        is_document = True
        has_caption = True

    elif msg.reply_to_message and msg.reply_to_message.photo:
        offset = len(msg.reply_to_message.caption or "")
        media_caption, buttons = button_markdown_parser(msg.reply_to_message.caption, entities=msg.reply_to_message.parse_entities(), offset=offset)
        content = msg.reply_to_message.photo[-1].file_id
        is_image = True
        has_caption = True

    elif msg.reply_to_message and msg.reply_to_message.audio:
        offset = len(msg.reply_to_message.caption or "")
        media_caption, buttons = button_markdown_parser(msg.reply_to_message.caption, entities=msg.reply_to_message.parse_entities(), offset=offset)
        content = msg.reply_to_message.audio.file_id
        is_audio = True
        has_caption = True

    elif msg.reply_to_message and msg.reply_to_message.voice:
        offset = len(msg.reply_to_message.caption or "")
        media_caption, buttons = button_markdown_parser(msg.reply_to_message.caption, entities=msg.reply_to_message.parse_entities(), offset=offset)
        content = msg.reply_to_message.voice.file_id
        is_voice = True
        has_caption = True

    elif msg.reply_to_message and msg.reply_to_message.video:
        offset = len(msg.reply_to_message.caption or "")
        media_caption, buttons = button_markdown_parser(msg.reply_to_message.caption, entities=msg.reply_to_message.parse_entities(), offset=offset)
        content = msg.reply_to_message.video.file_id
        is_video = True
        has_caption = True

    elif msg.reply_to_message and msg.reply_to_message.text:
        content = msg.reply_to_message.text

    elif not content:
        msg.reply_text("لا توجد رسالة ملاحظة - لا يمكن أن يكون لديك أزرار فقط، تحتاج إلى رسالة معها!")
        return

    for handler in dispatcher.handlers.get(HANDLER_GROUP, []):
        if handler.filters == (keyword, chat.id):
            dispatcher.remove_handler(handler, HANDLER_GROUP)

    sql.add_filter(chat_id, keyword, content, is_sticker, is_document, is_image, is_audio, is_voice, is_video,
                   buttons, media_caption, has_caption)

    msg.reply_text("تمت إضافة عامل التصفية '{}' في *{}*!".format(keyword, chat_name), parse_mode=telegram.ParseMode.MARKDOWN)
    raise DispatcherHandlerStop


# NOT ASYNC BECAUSE DISPATCHER HANDLER RAISED
@user_admin
def stop_filter(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user
    args = update.effective_message.text.split(None, 1)

    conn = connected(bot, update, chat, user.id)
    if not conn == False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = chat.id
        if chat.type == "private":
            chat_name = "الملاحظات المحلية"
        else:
            chat_name = chat.title

    if len(args) < 2:
        return

    chat_filters = sql.get_chat_triggers(chat_id)

    if not chat_filters:
        update.effective_message.reply_text("لا توجد عوامل تصفية نشطة هنا!")
        return

    for keyword in chat_filters:
        if keyword == args[1]:
            sql.remove_filter(chat_id, args[1])
            update.effective_message.reply_text("تم إيقاف الرد على ذلك في *{}*.".format(chat_name), parse_mode=telegram.ParseMode.MARKDOWN)
            raise DispatcherHandlerStop

    update.effective_message.reply_text("هذا ليس عامل تصفية حالياً - استخدم /filters لعرض جميع عوامل التصفية النشطة.")


@run_async
def reply_filter(bot: Bot, update: Update):
    chat = update.effective_chat
    message = update.effective_message
    to_match = extract_text(message)
    if not to_match:
        return

    if message.reply_to_message:
        message = message.reply_to_message

    chat_filters = sql.get_chat_triggers(chat.id)
    for keyword in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            filt = sql.get_filter(chat.id, keyword)
            buttons = sql.get_buttons(chat.id, filt.keyword)
            media_caption = filt.caption if filt.caption is not None else ""
            keyboard = None
            if len(buttons) > 0:
                keyboard = InlineKeyboardMarkup(build_keyboard(buttons))
            if filt.is_sticker:
                message.reply_sticker(
                    filt.reply,
                    reply_markup=keyboard,
                    api_kwargs={"allow_sending_without_reply": True}
                )
            elif filt.is_document:
                message.reply_document(
                    filt.reply,
                    caption=media_caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard,
                    api_kwargs={"allow_sending_without_reply": True}
                )
            elif filt.is_image:
                message.reply_photo(
                    filt.reply,
                    caption=media_caption,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN,
                    api_kwargs={"allow_sending_without_reply": True}
                )
            elif filt.is_audio:
                message.reply_audio(
                    filt.reply,
                    caption=media_caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard,
                    api_kwargs={"allow_sending_without_reply": True}
                )
            elif filt.is_voice:
                message.reply_voice(
                    filt.reply,
                    caption=media_caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard,
                    api_kwargs={"allow_sending_without_reply": True}
                )
            elif filt.is_video:
                message.reply_video(
                    filt.reply,
                    caption=media_caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard,
                    api_kwargs={"allow_sending_without_reply": True}
                )
            elif filt.has_markdown:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                should_preview_disabled = True
                if "telegra.ph" in filt.reply or "youtu.be" in filt.reply:
                    should_preview_disabled = False

                try:
                    message.reply_text(filt.reply, parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=should_preview_disabled,
                                       reply_markup=keyboard)
                except BadRequest as excp:
                    if excp.message == "Unsupported url protocol":
                        message.reply_text("يبدو أنك تحاول استخدام بروتوكول رابط غير مدعوم. تليجرام لا يدعم الأزرار لبعض البروتوكولات، مثل tg://. يرجى المحاولة مرة أخرى، أو اسأل في @KeralaBots للمساعدة.")
                    elif excp.message == "Replied message not found":
                        bot.send_message(chat.id, filt.reply, parse_mode=ParseMode.MARKDOWN,
                                         disable_web_page_preview=True,
                                         reply_markup=keyboard)
                    else:
                        message.reply_text("تعذر إرسال هذه الملاحظة، لأن تنسيقها غير صحيح. اسأل في @KeralaBots إذا كنت لا تستطيع معرفة السبب!")
                        LOGGER.warning("الرسالة %s تعذر تحليلها", str(filt.reply))
                        LOGGER.exception("تعذر تحليل عامل التصفية %s في الدردشة %s", str(filt.keyword), str(chat.id))
            else:
                message.reply_text(filt.reply)
            break


@run_async
def rmall_filters(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user
    member = chat.get_member(user.id)
    if member.status != "creator" and user.id not in SUDO_USERS:
        update.effective_message.reply_text("فقط منشئ الدردشة يمكنه مسح جميع عوامل التصفية دفعة واحدة.")
    else:
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton(text="إيقاف جميع عوامل التصفية", callback_data="filters_rmall")], [
                                       InlineKeyboardButton(text="إلغاء", callback_data="filters_cancel")]])
        update.effective_message.reply_text(
            f"هل أنت متأكد أنك تريد إيقاف جميع عوامل التصفية في {chat.title}؟ لا يمكن التراجع عن هذا الإجراء.", reply_markup=buttons, parse_mode=ParseMode.MARKDOWN)


@run_async
def rmall_callback(bot: Bot, update: Update):
    query = update.callback_query
    chat = update.effective_chat
    msg = update.effective_message
    member = chat.get_member(query.from_user.id)
    if query.data == 'filters_rmall':
        if member.status == "creator" or query.from_user.id in SUDO_USERS:
            allfilters = sql.get_chat_triggers(chat.id)
            if not allfilters:
                msg.edit_text("لا توجد عوامل تصفية في هذه الدردشة، لا شيء لإيقافه!")
                return

            count = 0
            filterlist = []
            for x in allfilters:
                count += 1
                filterlist.append(x)

            for i in filterlist:
                sql.remove_filter(chat.id, i)

            msg.edit_text(f"تم تنظيف {count} عامل تصفية في {chat.title}")

        if member.status == "administrator":
            query.answer("فقط منشئ الدردشة يمكنه القيام بذلك.")

        if member.status == "member":
            query.answer("يجب أن تكون مشرفاً للقيام بذلك.")
    elif query.data == 'filters_cancel':
        if member.status == "creator" or query.from_user.id in SUDO_USERS:
            msg.edit_text("تم إلغاء مسح جميع عوامل التصفية.")
            return
        if member.status == "administrator":
            query.answer("فقط منشئ الدردشة يمكنه القيام بذلك.")
        if member.status == "member":
            query.answer("يجب أن تكون مشرفاً للقيام بذلك.")


def __stats__():
    return "{} عامل تصفية، عبر {} دردشة.".format(sql.num_filters(), sql.num_chats())


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    cust_filters = sql.get_chat_triggers(chat_id)
    return "هناك `{}` عامل تصفية مخصص هنا.".format(len(cust_filters))


# ================== المساعدة ==================
__help__ = """
- /filters: قائمة بجميع عوامل التصفية النشطة في هذه الدردشة.

*للمشرفين فقط:*
- /filter <كلمة مفتاحية> <رسالة الرد>: إضافة عامل تصفية إلى هذه الدردشة. سيقوم البوت الآن بالرد بتلك الرسالة كلما تم ذكر 'الكلمة المفتاحية'. إذا قمت بالرد على ملصق بكلمة مفتاحية، سيرد البوت بذلك الملصق. ملاحظة: جميع الكلمات المفتاحية لعوامل التصفية تكون بأحرف صغيرة. إذا أردت أن تكون كلمتك المفتاحية جملة، استخدم علامات الاقتباس. مثال: /filter "مرحباً" كيف حالك؟
- /stop <كلمة مفتاحية>: إيقاف عامل التصفية هذا.
*لمنشئ الدردشة فقط:*
- /removeallfilters: إيقاف جميع عوامل التصفية في الدردشة دفعة واحدة (مقتصر على المنشئين فقط).

*الأوامر العربية (بدون /):*
عوامل التصفية: عرض جميع عوامل التصفية
إضافة عامل تصفية <كلمة> <الرد>: إضافة عامل تصفية جديد
إيقاف عامل تصفية <كلمة>: إيقاف عامل تصفية معين
إزالة كل عوامل التصفية: إزالة جميع عوامل التصفية (للمنشئ فقط)
"""

__mod_name__ = "عوامل التصفية"

FILTER_HANDLER = CommandHandler("filter", filters)
STOP_HANDLER = CommandHandler("stop", stop_filter)
RMALLFILTER_HANDLER = CommandHandler("removeallfilters", rmall_filters, filters=Filters.group)
RMALLFILTER_CALLBACK = CallbackQueryHandler(rmall_callback, pattern=r"filters_.*")
LIST_HANDLER = DisableAbleCommandHandler("filters", list_handlers, admin_ok=True)
CUST_FILTER_HANDLER = MessageHandler(CustomFilters.has_text, reply_filter)

# معالجات الأوامر العربية
LIST_AR_HANDLER = CommandHandler("عوامل التصفية", list_handlers)
FILTER_AR_HANDLER = CommandHandler("إضافة عامل تصفية", filters)
STOP_AR_HANDLER = CommandHandler("إيقاف عامل تصفية", stop_filter)
RMALL_AR_HANDLER = CommandHandler("إزالة كل عوامل التصفية", rmall_filters, filters=Filters.group)

dispatcher.add_handler(FILTER_HANDLER)
dispatcher.add_handler(STOP_HANDLER)
dispatcher.add_handler(RMALLFILTER_HANDLER)
dispatcher.add_handler(RMALLFILTER_CALLBACK)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(CUST_FILTER_HANDLER, HANDLER_GROUP)

dispatcher.add_handler(LIST_AR_HANDLER)
dispatcher.add_handler(FILTER_AR_HANDLER)
dispatcher.add_handler(STOP_AR_HANDLER)
dispatcher.add_handler(RMALL_AR_HANDLER)
