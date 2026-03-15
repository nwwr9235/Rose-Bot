from time import sleep

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest, Unauthorized
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, filters

import tg_bot.modules.sql.global_bans_sql as gban_sql
import tg_bot.modules.sql.users_sql as user_sql
from tg_bot import dispatcher, OWNER_ID
from tg_bot.modules.helper_funcs.filters import CustomFilters


async def get_invalid_chats(update: Update, context: ContextTypes.DEFAULT_TYPE, remove: bool = False):
    bot = context.bot
    chat_id = update.effective_chat.id
    chats = user_sql.get_all_chats()
    kicked_chats, progress = 0, 0
    chat_list = []
    progress_message = None

    for chat in chats:
        if ((100 * chats.index(chat)) / len(chats)) > progress:
            progress_bar = f"{progress}% completed in getting invalid chats."
            if progress_message:
                try:
                    await bot.edit_message_text(progress_bar, chat_id, progress_message.message_id)
                except:
                    pass
            else:
                progress_message = await bot.send_message(chat_id, progress_bar)
            progress += 5

        cid = chat.chat_id
        sleep(0.1)
        try:
            await bot.get_chat(cid, timeout=120)
        except (BadRequest, Unauthorized):
            kicked_chats += 1
            chat_list.append(cid)
        except:
            pass

    if progress_message:
        try:
            await progress_message.delete()
        except:
            pass

    if not remove:
        return kicked_chats
    else:
        for muted_chat in chat_list:
            sleep(0.1)
            user_sql.rem_chat(muted_chat)
        return kicked_chats


async def get_invalid_gban(update: Update, context: ContextTypes.DEFAULT_TYPE, remove: bool = False):
    bot = context.bot
    banned = gban_sql.get_gban_list()
    ungbanned_users = 0
    ungban_list = []

    for user in banned:
        user_id = user["user_id"]
        sleep(0.1)
        try:
            await bot.get_chat(user_id)
        except BadRequest:
            ungbanned_users += 1
            ungban_list.append(user_id)
        except:
            pass

    if not remove:
        return ungbanned_users
    else:
        for user_id in ungban_list:
            sleep(0.1)
            gban_sql.ungban_user(user_id)
        return ungbanned_users


async def dbcleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    await msg.reply_text("جاري حساب عدد المجموعات غير الصالحة ...")
    invalid_chat_count = await get_invalid_chats(update, context)

    await msg.reply_text("جاري حساب عدد المحظورين عمومًا غير الصالحين ...")
    invalid_gban_count = await get_invalid_gban(update, context)

    reply = f"إجمالي المجموعات غير الصالحة - {invalid_chat_count}\n"
    reply += f"إجمالي المحظورين عمومًا غير الصالحين - {invalid_gban_count}"

    buttons = [
        [InlineKeyboardButton("تنظيف قاعدة البيانات", callback_data="db_cleanup")]
    ]

    await update.effective_message.reply_text(reply, reply_markup=InlineKeyboardMarkup(buttons))


async def get_muted_chats(update: Update, context: ContextTypes.DEFAULT_TYPE, leave: bool = False):
    bot = context.bot
    chat_id = update.effective_chat.id
    chats = user_sql.get_all_chats()
    muted_chats, progress = 0, 0
    chat_list = []
    progress_message = None

    for chat in chats:
        if ((100 * chats.index(chat)) / len(chats)) > progress:
            progress_bar = f"{progress}% completed in getting muted chats."
            if progress_message:
                try:
                    await bot.edit_message_text(progress_bar, chat_id, progress_message.message_id)
                except:
                    pass
            else:
                progress_message = await bot.send_message(chat_id, progress_bar)
            progress += 5

        cid = chat.chat_id
        sleep(0.1)

        try:
            await bot.send_chat_action(cid, "TYPING", timeout=120)
        except (BadRequest, Unauthorized):
            muted_chats += 1
            chat_list.append(cid)
        except:
            pass

    if progress_message:
        try:
            await progress_message.delete()
        except:
            pass

    if not leave:
        return muted_chats
    else:
        for muted_chat in chat_list:
            sleep(0.1)
            try:
                await bot.leave_chat(muted_chat, timeout=120)
            except:
                pass
            user_sql.rem_chat(muted_chat)
        return muted_chats


async def leave_muted_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    progress_message = await message.reply_text("جاري حساب عدد المجموعات ...")
    muted_chats = await get_muted_chats(update, context)

    buttons = [
        [InlineKeyboardButton("مغادرة المجموعات", callback_data="db_leave_chat")]
    ]

    await update.effective_message.reply_text(f"أنا مكتوم في {muted_chats} مجموعة.",
                                              reply_markup=InlineKeyboardMarkup(buttons))
    await progress_message.delete()


async def callback_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    message = query.message
    chat_id = update.effective_chat.id
    query_type = query.data

    admin_list = [OWNER_ID]

    await query.answer()

    if query_type == "db_leave_chat":
        if query.from_user.id in admin_list:
            await context.bot.edit_message_text("جاري مغادرة المجموعات ...", chat_id, message.message_id)
            chat_count = await get_muted_chats(update, context, leave=True)
            await context.bot.send_message(chat_id, f"غادرت {chat_count} مجموعة.")
        else:
            await query.answer("غير مسموح لك باستخدام هذا.")
    elif query_type == "db_cleanup":
        if query.from_user.id in admin_list:
            await context.bot.edit_message_text("جاري تنظيف قاعدة البيانات ...", chat_id, message.message_id)
            invalid_chat_count = await get_invalid_chats(update, context, remove=True)
            invalid_gban_count = await get_invalid_gban(update, context, remove=True)
            reply = f"تم تنظيف {invalid_chat_count} مجموعة و {invalid_gban_count} محظور عمومي من قاعدة البيانات."
            await context.bot.send_message(chat_id, reply)
        else:
            await query.answer("غير مسموح لك باستخدام هذا.")


__mod_name__ = "تنظيف قاعدة البيانات"

DB_CLEANUP_HANDLER = CommandHandler("dbcleanup", dbcleanup, filters=CustomFilters.sudo_filter)
LEAVE_MUTED_CHATS_HANDLER = CommandHandler("leavemutedchats", leave_muted_chats, filters=CustomFilters.sudo_filter)
BUTTON_HANDLER = CallbackQueryHandler(callback_button, pattern="db_.*")

dispatcher.add_handler(DB_CLEANUP_HANDLER)
dispatcher.add_handler(LEAVE_MUTED_CHATS_HANDLER)
dispatcher.add_handler(BUTTON_HANDLER)
