from typing import Optional, List

from telegram import Update, Chat, User
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes, CommandHandler, filters

import tg_bot.modules.sql.connection_sql as sql
from tg_bot import dispatcher, LOGGER, SUDO_USERS
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.keyboard import keyboard


@user_admin
async def allow_connections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type != chat.PRIVATE:
        args = context.args
        if len(args) >= 1:
            var = args[0]
            if var == "no":
                sql.set_allow_connect_to_chat(chat.id, False)
                await update.effective_message.reply_text("تم تعطيل الاتصال بهذه المجموعة للمستخدمين")
            elif var == "yes":
                sql.set_allow_connect_to_chat(chat.id, True)
                await update.effective_message.reply_text("تم تفعيل الاتصال بهذه المجموعة للمستخدمين")
            else:
                await update.effective_message.reply_text("الرجاء إدخال on/yes/off/no في المجموعة!")
        else:
            await update.effective_message.reply_text("الرجاء إدخال on/yes/off/no في المجموعة!")
    else:
        await update.effective_message.reply_text("الرجاء إدخال on/yes/off/no في المجموعة!")


async def connect_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    args = context.args

    if chat.type == 'private':
        if len(args) >= 1:
            try:
                connect_chat = int(args[0])
            except ValueError:
                await update.effective_message.reply_text("معرف المجموعة غير صالح!")
                return

            # التحقق من صلاحية الاتصال
            member = await context.bot.get_chat_member(connect_chat, update.effective_message.from_user.id)
            if (member.status in ('administrator', 'creator') or
                (sql.allow_connect_to_chat(connect_chat) and member.status == 'member') or
                user.id in SUDO_USERS):

                connection_status = sql.connect(update.effective_message.from_user.id, connect_chat)
                if connection_status:
                    chat_name = (await context.bot.get_chat(connect_chat)).title
                    await update.effective_message.reply_text(f"تم الاتصال بنجاح بـ *{chat_name}*", parse_mode=ParseMode.MARKDOWN)

                    # إضافة المجموعة إلى سجل الاتصالات
                    history = sql.get_history(user.id)
                    if history:
                        # المتغيرات
                        history1 = int(history.chat_id1) if history.chat_id1 else None
                        history2 = int(history.chat_id2) if history.chat_id2 else None
                        history3 = int(history.chat_id3) if history.chat_id3 else None
                        number = history.updated

                        if number == 1 and connect_chat != history2 and connect_chat != history3:
                            history1 = connect_chat
                            number = 2
                        elif number == 2 and connect_chat != history1 and connect_chat != history3:
                            history2 = connect_chat
                            number = 3
                        elif number >= 3 and connect_chat != history2 and connect_chat != history1:
                            history3 = connect_chat
                            number = 1
                        else:
                            pass

                        sql.add_history(user.id, history1, history2, history3, number)
                    else:
                        sql.add_history(user.id, connect_chat, 0, 0, 2)

                    # إعادة بناء لوحة مفاتيح المستخدم
                    await keyboard(update, context)
                else:
                    await update.effective_message.reply_text("فشل الاتصال!")
            else:
                await update.effective_message.reply_text("غير مسموح بالاتصال بهذه المجموعة!")
        else:
            await update.effective_message.reply_text("أدخل معرف المجموعة للاتصال!")
            history = sql.get_history(user.id)
            if history:
                LOGGER.debug(f"{history.user_id}, {history.chat_id1}, {history.chat_id2}, {history.chat_id3}, {history.updated}")
    else:
        await update.effective_message.reply_text("هذا الأمر متاح فقط في المحادثات الخاصة!")


async def disconnect_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        disconnection_status = sql.disconnect(update.effective_message.from_user.id)
        if disconnection_status:
            await update.effective_message.reply_text("تم قطع الاتصال بالمجموعة!")
            # إعادة بناء لوحة مفاتيح المستخدم
            await keyboard(update, context)
        else:
            await update.effective_message.reply_text("فشل قطع الاتصال!")
    else:
        await update.effective_message.reply_text("هذا الأمر متاح فقط في المحادثات الخاصة!")


async def connected(update: Update, context: ContextTypes.DEFAULT_TYPE, chat: Chat, user_id: int, need_admin: bool = True):
    """دالة مساعدة للتحقق من حالة الاتصال، تُستخدم في وحدات أخرى."""
    if chat.type == chat.PRIVATE and sql.get_connected_chat(user_id):
        conn_id = sql.get_connected_chat(user_id).chat_id
        member = await context.bot.get_chat_member(conn_id, user_id)
        if (member.status in ('administrator', 'creator') or
            (sql.allow_connect_to_chat(conn_id) and member.status == 'member') or
            user_id in SUDO_USERS):
            if need_admin:
                if member.status in ('administrator', 'creator') or user_id in SUDO_USERS:
                    return conn_id
                else:
                    await update.effective_message.reply_text("يجب أن تكون مشرفًا في المجموعة المتصلة!")
                    return False
            else:
                return conn_id
        else:
            await update.effective_message.reply_text("تغيرت صلاحيات المجموعة أو لم تعد مشرفًا. سأقطع الاتصال.")
            await disconnect_chat(update, context)
            return False
    else:
        return False


__help__ = """
الإجراءات المتاحة مع المجموعات المتصلة:
- عرض وتعديل الملاحظات
- عرض وتعديل الفلاتر
- المزيد في المستقبل!

- /connect <معرف المجموعة>: الاتصال بمجموعة عن بُعد
- /disconnect: قطع الاتصال بالمجموعة الحالية
- /allowconnect on/yes/off/no: السماح للمستخدمين بالاتصال بهذه المجموعة
"""

__mod_name__ = "الاتصالات"

CONNECT_CHAT_HANDLER = CommandHandler("connect", connect_chat, filters=filters.ChatType.PRIVATE)
DISCONNECT_CHAT_HANDLER = CommandHandler("disconnect", disconnect_chat, filters=filters.ChatType.PRIVATE)
ALLOW_CONNECTIONS_HANDLER = CommandHandler("allowconnect", allow_connections, filters=filters.ChatType.GROUPS)

dispatcher.add_handler(CONNECT_CHAT_HANDLER)
dispatcher.add_handler(DISCONNECT_CHAT_HANDLER)
dispatcher.add_handler(ALLOW_CONNECTIONS_HANDLER)
