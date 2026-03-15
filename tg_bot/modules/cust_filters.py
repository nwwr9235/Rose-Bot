import re
from typing import Optional

import telegram
from telegram import Update, Message, Chat, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.helpers import escape_markdown

from tg_bot import dispatcher, LOGGER, BMERNU_SCUT_SRELFTI, SUDO_USERS
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.helper_funcs.extraction import extract_text
from tg_bot.modules.helper_funcs.misc import build_keyboard
from tg_bot.modules.helper_funcs.string_handling import split_quotes, button_markdown_parser
from tg_bot.modules.sql import cust_filters_sql as sql
from tg_bot.modules.connection import connected

HANDLER_GROUP = 15
BASIC_FILTER_STRING = "*الفلاتر في هذه المجموعة:*\n"


async def list_handlers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    conn = await connected(update, context, chat, user.id, need_admin=False)
    if conn:
        chat_id = conn
        chat_name = (await context.bot.get_chat(conn)).title
        filter_list = f"*الفلاتر في {chat_name}:*\n"
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = "الفلاتر المحلية"
            filter_list = "*الفلاتر المحلية:*\n"
        else:
            chat_name = chat.title
            filter_list = f"*الفلاتر في {chat_name}:*\n"

    total_count_f_fliters = sql.num_filters_per_chat(chat_id)
    filter_list += f"**عدد الفلاتر**: {total_count_f_fliters}\n"

    all_handlers = sql.get_chat_triggers(chat_id)

    if not all_handlers:
        await update.effective_message.reply_text(f"لا توجد فلاتر في {chat_name}!")
        return

    for keyword in all_handlers:
        entry = f" - {escape_markdown(keyword)}\n"
        if len(entry) + len(filter_list) > telegram.constants.MessageLimit.MAX_TEXT_LENGTH:
            await update.effective_message.reply_text(filter_list, parse_mode=ParseMode.MARKDOWN)
            filter_list = entry
        else:
            filter_list += entry

    if filter_list != BASIC_FILTER_STRING:
        await update.effective_message.reply_text(filter_list, parse_mode=ParseMode.MARKDOWN)


@user_admin
async def filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    args = msg.text.split(None, 1)

    conn = await connected(update, context, chat, user.id)
    if conn:
        chat_id = conn
        chat_name = (await context.bot.get_chat(conn)).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = "الفلاتر المحلية"
        else:
            chat_name = chat.title

    if len(args) < 2:
        return

    # التحقق من الحد الأقصى للفلاتر
    if BMERNU_SCUT_SRELFTI:
        total_fs = sql.num_filters_per_chat(chat_id)
        if total_fs >= BMERNU_SCUT_SRELFTI:
            await msg.reply_text(
                f"لديك حاليًا {total_fs} فلتر. "
                f"الحد الأقصى المسموح به هو {BMERNU_SCUT_SRELFTI}. "
                "يجب حذف بعض الفلاتر قبل إضافة المزيد."
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
    has_caption = False
    media_caption = None
    content = None
    buttons = []

    # تحديد محتوى الفلتر
    if len(extracted) >= 2:
        offset = len(extracted[1]) - len(msg.text)
        content, buttons = button_markdown_parser(extracted[1], entities=msg.parse_entities(), offset=offset)
        content = content.strip()

    if msg.reply_to_message and msg.reply_to_message.sticker:
        content = msg.reply_to_message.sticker.file_id
        is_sticker = True

    elif msg.reply_to_message and msg.reply_to_message.document:
        offset = len(msg.reply_to_message.caption or "")
        media_caption, buttons = button_markdown_parser(
            msg.reply_to_message.caption,
            entities=msg.reply_to_message.parse_entities(),
            offset=offset
        )
        content = msg.reply_to_message.document.file_id
        is_document = True
        has_caption = True

    elif msg.reply_to_message and msg.reply_to_message.photo:
        offset = len(msg.reply_to_message.caption or "")
        media_caption, buttons = button_markdown_parser(
            msg.reply_to_message.caption,
            entities=msg.reply_to_message.parse_entities(),
            offset=offset
        )
        content = msg.reply_to_message.photo[-1].file_id
        is_image = True
        has_caption = True

    elif msg.reply_to_message and msg.reply_to_message.audio:
        offset = len(msg.reply_to_message.caption or "")
        media_caption, buttons = button_markdown_parser(
            msg.reply_to_message.caption,
            entities=msg.reply_to_message.parse_entities(),
            offset=offset
        )
        content = msg.reply_to_message.audio.file_id
        is_audio = True
        has_caption = True

    elif msg.reply_to_message and msg.reply_to_message.voice:
        offset = len(msg.reply_to_message.caption or "")
        media_caption, buttons = button_markdown_parser(
            msg.reply_to_message.caption,
            entities=msg.reply_to_message.parse_entities(),
            offset=offset
        )
        content = msg.reply_to_message.voice.file_id
        is_voice = True
        has_caption = True

    elif msg.reply_to_message and msg.reply_to_message.video:
        offset = len(msg.reply_to_message.caption or "")
        media_caption, buttons = button_markdown_parser(
            msg.reply_to_message.caption,
            entities=msg.reply_to_message.parse_entities(),
            offset=offset
        )
        content = msg.reply_to_message.video.file_id
        is_video = True
        has_caption = True

    elif msg.reply_to_message and msg.reply_to_message.text:
        content = msg.reply_to_message.text

    elif not content:
        await msg.reply_text("لا توجد رسالة للفلتر - لا يمكنك إضافة أزرار فقط، يجب أن يكون هناك رسالة مصاحبة!")
        return

    # إزالة المعالج القديم إذا وجد
    for handler in dispatcher.handlers.get(HANDLER_GROUP, []):
        if hasattr(handler, 'filters') and handler.filters == (keyword, chat_id):
            dispatpatcher.remove_handler(handler, HANDLER_GROUP)
            break

    sql.add_filter(chat_id, keyword, content, is_sticker, is_document, is_image, is_audio, is_voice, is_video,
                   buttons, media_caption, has_caption)

    await msg.reply_text(f"تم إضافة الفلتر '{keyword}' في *{chat_name}*!", parse_mode=ParseMode.MARKDOWN)


@user_admin
async def stop_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    args = update.effective_message.text.split(None, 1)

    conn = await connected(update, context, chat, user.id)
    if conn:
        chat_id = conn
        chat_name = (await context.bot.get_chat(conn)).title
    else:
        chat_id = chat.id
        if chat.type == "private":
            chat_name = "الفلاتر المحلية"
        else:
            chat_name = chat.title

    if len(args) < 2:
        return

    chat_filters = sql.get_chat_triggers(chat_id)

    if not chat_filters:
        await update.effective_message.reply_text("لا توجد فلاتر مفعلة هنا!")
        return

    for keyword in chat_filters:
        if keyword == args[1]:
            sql.remove_filter(chat_id, args[1])
            await update.effective_message.reply_text(f"تم إيقاف الرد على ذلك في *{chat_name}*.", parse_mode=ParseMode.MARKDOWN)
            return

    await update.effective_message.reply_text("هذا ليس فلترًا حاليًا - استخدم /filters لعرض الفلاتر النشطة.")


async def reply_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            if buttons:
                keyboard = InlineKeyboardMarkup(build_keyboard(buttons))

            try:
                if filt.is_sticker:
                    await message.reply_sticker(
                        filt.reply,
                        reply_markup=keyboard,
                        api_kwargs={"allow_sending_without_reply": True}
                    )
                elif filt.is_document:
                    await message.reply_document(
                        filt.reply,
                        caption=media_caption,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=keyboard,
                        api_kwargs={"allow_sending_without_reply": True}
                    )
                elif filt.is_image:
                    await message.reply_photo(
                        filt.reply,
                        caption=media_caption,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=keyboard,
                        api_kwargs={"allow_sending_without_reply": True}
                    )
                elif filt.is_audio:
                    await message.reply_audio(
                        filt.reply,
                        caption=media_caption,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=keyboard,
                        api_kwargs={"allow_sending_without_reply": True}
                    )
                elif filt.is_voice:
                    await message.reply_voice(
                        filt.reply,
                        caption=media_caption,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=keyboard,
                        api_kwargs={"allow_sending_without_reply": True}
                    )
                elif filt.is_video:
                    await message.reply_video(
                        filt.reply,
                        caption=media_caption,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=keyboard,
                        api_kwargs={"allow_sending_without_reply": True}
                    )
                elif filt.has_markdown:
                    should_preview_disabled = True
                    if "telegra.ph" in filt.reply or "youtu.be" in filt.reply:
                        should_preview_disabled = False

                    await message.reply_text(
                        filt.reply,
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=should_preview_disabled,
                        reply_markup=keyboard
                    )
                else:
                    await message.reply_text(filt.reply)
                break
            except BadRequest as excp:
                if excp.message == "Unsupported url protocol":
                    await message.reply_text("يبدو أنك تحاول استخدام بروتوكول رابط غير مدعوم. تيليجرام لا يدعم الأزرار لبعض البروتوكولات مثل tg://. حاول مرة أخرى.")
                elif excp.message == "Replied message not found":
                    await context.bot.send_message(chat.id, filt.reply, parse_mode=ParseMode.MARKDOWN,
                                                   disable_web_page_preview=True, reply_markup=keyboard)
                else:
                    await message.reply_text("لا يمكن إرسال هذا الفلتر، ربما بسبب تنسيق غير صحيح.")
                    LOGGER.warning("Message %s could not be parsed", str(filt.reply))
                    LOGGER.exception("Could not parse filter %s in chat %s", str(filt.keyword), str(chat.id))
            break


async def rmall_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    member = await chat.get_member(user.id)
    if member.status != "creator" and user.id not in SUDO_USERS:
        await update.effective_message.reply_text("فقط منشئ المجموعة يمكنه مسح جميع الفلاتر دفعة واحدة.")
    else:
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton(text="إيقاف جميع الفلاتر", callback_data="filters_rmall")],
            [InlineKeyboardButton(text="إلغاء", callback_data="filters_cancel")]
        ])
        await update.effective_message.reply_text(
            f"هل أنت متأكد من رغبتك في إيقاف جميع الفلاتر في {chat.title}؟ لا يمكن التراجع عن هذا الإجراء.",
            reply_markup=buttons,
            parse_mode=ParseMode.MARKDOWN
        )


async def rmall_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat = update.effective_chat
    msg = update.effective_message
    member = await chat.get_member(query.from_user.id)

    if query.data == 'filters_rmall':
        if member.status == "creator" or query.from_user.id in SUDO_USERS:
            allfilters = sql.get_chat_triggers(chat.id)
            if not allfilters:
                await msg.edit_text("لا توجد فلاتر في هذه المجموعة، لا شيء لإيقافه!")
                return

            count = 0
            filterlist = list(allfilters)
            for i in filterlist:
                sql.remove_filter(chat.id, i)
                count += 1

            await msg.edit_text(f"تم مسح {count} فلتر في {chat.title}")
        elif member.status == "administrator":
            await query.answer("فقط منشئ المجموعة يمكنه فعل ذلك.")
        else:
            await query.answer("يجب أن تكون مشرفًا لفعل ذلك.")
    elif query.data == 'filters_cancel':
        if member.status == "creator" or query.from_user.id in SUDO_USERS:
            await msg.edit_text("تم إلغاء مسح جميع الفلاتر.")
        elif member.status == "administrator":
            await query.answer("فقط منشئ المجموعة يمكنه فعل ذلك.")
        else:
            await query.answer("يجب أن تكون مشرفًا لفعل ذلك.")
    await query.answer()


def __stats__():
    return f"{sql.num_filters()} فلتر، في {sql.num_chats()} مجموعة."


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


async def __chat_settings__(chat_id: int, user_id: int) -> str:
    cust_filters = sql.get_chat_triggers(chat_id)
    return f"يوجد `{len(cust_filters)}` فلتر مخصص هنا."


__help__ = """
- /filters: عرض جميع الفلاتر النشطة في هذه المجموعة.

*للمشرفين فقط:*
- /filter <الكلمة> <رسالة الرد>: إضافة فلتر إلى هذه المجموعة. سيقوم البوت الآن بالرد بتلك الرسالة كلما تم ذكر 'الكلمة'. إذا قمت بالرد على ملصق بكلمة، سيرد البوت بذلك الملصق. ملاحظة: جميع كلمات الفلاتر تُكتب بأحرف صغيرة. إذا أردت أن تكون الكلمة جملة، استخدم علامات الاقتباس. مثال: /filter "مرحبا" كيف حالك؟
- /stop <كلمة الفلتر>: إيقاف ذلك الفلتر.
*منشئ المجموعة فقط:*
- /removeallfilters: إيقاف جميع الفلاتر في المجموعة مرة واحدة.
"""

__mod_name__ = "الفلاتر"

FILTER_HANDLER = CommandHandler("filter", filters, filters=filters.ChatType.GROUPS)
STOP_HANDLER = CommandHandler("stop", stop_filter, filters=filters.ChatType.GROUPS)
RMALLFILTER_HANDLER = CommandHandler("removeallfilters", rmall_filters, filters=filters.ChatType.GROUPS)
RMALLFILTER_CALLBACK = CallbackQueryHandler(rmall_callback, pattern=r"filters_.*")
LIST_HANDLER = DisableAbleCommandHandler("filters", list_handlers, admin_ok=True)
CUST_FILTER_HANDLER = MessageHandler(filters.TEXT & ~filters.COMMAND, reply_filter)

dispatcher.add_handler(FILTER_HANDLER)
dispatcher.add_handler(STOP_HANDLER)
dispatcher.add_handler(RMALLFILTER_HANDLER)
dispatcher.add_handler(RMALLFILTER_CALLBACK)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(CUST_FILTER_HANDLER, HANDLER_GROUP)
