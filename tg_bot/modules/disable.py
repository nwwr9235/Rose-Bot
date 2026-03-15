from typing import Union, List, Optional

from future.utils import string_types
from telegram import Update, Chat, User
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, MessageHandler, filters
from telegram.helpers import escape_markdown

from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.handlers import CMD_STARTERS
from tg_bot.modules.helper_funcs.misc import is_module_loaded

FILENAME = __name__.rsplit(".", 1)[-1]

if is_module_loaded(FILENAME):
    from tg_bot.modules.helper_funcs.chat_status import is_user_admin
    from tg_bot.modules.sql import disable_sql as sql

    DISABLE_CMDS = []
    DISABLE_OTHER = []
    ADMIN_CMDS = []

    class DisableAbleCommandHandler(CommandHandler):
        def __init__(self, command, callback, admin_ok=False, **kwargs):
            super().__init__(command, callback, **kwargs)
            self.admin_ok = admin_ok
            if isinstance(command, string_types):
                DISABLE_CMDS.append(command)
                if admin_ok:
                    ADMIN_CMDS.append(command)
            else:
                DISABLE_CMDS.extend(command)
                if admin_ok:
                    ADMIN_CMDS.extend(command)

        async def check_update(self, update: Update) -> Optional[Union[bool, object]]:
            chat = update.effective_chat
            user = update.effective_user

            # أولاً، تحقق من المطابقة باستخدام طريقة الفئة الأساسية
            if not await super().check_update(update):
                return False

            # يجب أن يكون آمناً لأن check_update مرت
            command = update.effective_message.text.split(None, 1)[0][1:].split('@')[0]

            # تحقق إذا كان الأمر معطلاً
            if sql.is_command_disabled(chat.id, command):
                # إذا كان الأمر معطلاً، اسمح فقط إذا كان الأمر من ADMIN_CMDS والمستخدم مشرف
                if command in ADMIN_CMDS and await is_user_admin(chat, user.id):
                    return True
                return False

            # الأمر غير معطل
            return True


    class DisableAbleRegexHandler(MessageHandler):
        def __init__(self, pattern, callback, friendly="", **kwargs):
            super().__init__(filters.Regex(pattern), callback, **kwargs)
            DISABLE_OTHER.append(friendly or pattern)
            self.friendly = friendly or pattern

        async def check_update(self, update: Update) -> Optional[Union[bool, object]]:
            chat = update.effective_chat
            return await super().check_update(update) and not sql.is_command_disabled(chat.id, self.friendly)


    async def disable(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        args = context.args
        if len(args) >= 1:
            disable_cmd = args[0]
            if disable_cmd.startswith(CMD_STARTERS):
                disable_cmd = disable_cmd[1:]

            if disable_cmd in set(DISABLE_CMDS + DISABLE_OTHER):
                sql.disable_command(chat.id, disable_cmd)
                await update.effective_message.reply_text(f"تم تعطيل استخدام `{disable_cmd}`", parse_mode=ParseMode.MARKDOWN)
            else:
                await update.effective_message.reply_text("لا يمكن تعطيل هذا الأمر")
        else:
            await update.effective_message.reply_text("ماذا تريد تعطيل؟")


    async def enable(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        args = context.args
        if len(args) >= 1:
            enable_cmd = args[0]
            if enable_cmd.startswith(CMD_STARTERS):
                enable_cmd = enable_cmd[1:]

            if sql.enable_command(chat.id, enable_cmd):
                await update.effective_message.reply_text(f"تم تفعيل استخدام `{enable_cmd}`", parse_mode=ParseMode.MARKDOWN)
            else:
                await update.effective_message.reply_text("هل هذا الأمر معطل أصلاً؟")
        else:
            await update.effective_message.reply_text("ماذا تريد تفعيل؟")


    async def list_cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if DISABLE_CMDS + DISABLE_OTHER:
            result = ""
            for cmd in set(DISABLE_CMDS + DISABLE_OTHER):
                result += f" - `{escape_markdown(cmd)}`\n"
            await update.effective_message.reply_text(f"الأوامر التالية قابلة للتبديل:\n{result}", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.effective_message.reply_text("لا توجد أوامر يمكن تعطيلها.")


    def build_curr_disabled(chat_id: Union[str, int]) -> str:
        disabled = sql.get_all_disabled(chat_id)
        if not disabled:
            return "لا توجد أوامر معطلة!"
        result = ""
        for cmd in disabled:
            result += f" - `{escape_markdown(cmd)}`\n"
        return f"الأوامر التالية مقيدة حاليًا:\n{result}"


    async def commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        await update.effective_message.reply_text(build_curr_disabled(chat.id), parse_mode=ParseMode.MARKDOWN)


    def __stats__():
        return f"{sql.num_disabled()} عنصر معطل، عبر {sql.num_chats()} مجموعة."


    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)


    async def __chat_settings__(chat_id: int, user_id: int) -> str:
        return build_curr_disabled(chat_id)


    __mod_name__ = "التعطيل"

    __help__ = """
- /cmds: عرض حالة الأوامر المعطلة حاليًا

*للمشرفين فقط:*
- /enable <اسم الأمر>: تفعيل ذلك الأمر
- /disable <اسم الأمر>: تعطيل ذلك الأمر
- /listcmds: عرض جميع الأوامر القابلة للتبديل
    """

    DISABLE_HANDLER = CommandHandler("disable", disable, filters=filters.ChatType.GROUPS)
    ENABLE_HANDLER = CommandHandler("enable", enable, filters=filters.ChatType.GROUPS)
    COMMANDS_HANDLER = CommandHandler(["cmds", "disabled"], commands, filters=filters.ChatType.GROUPS)
    TOGGLE_HANDLER = CommandHandler("listcmds", list_cmds, filters=filters.ChatType.GROUPS)

    dispatcher.add_handler(DISABLE_HANDLER)
    dispatcher.add_handler(ENABLE_HANDLER)
    dispatcher.add_handler(COMMANDS_HANDLER)
    dispatcher.add_handler(TOGGLE_HANDLER)

else:
    DisableAbleCommandHandler = CommandHandler
    DisableAbleRegexHandler = MessageHandler
