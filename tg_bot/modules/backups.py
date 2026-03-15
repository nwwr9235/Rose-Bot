import json
from io import BytesIO
from typing import Optional

from telegram import Update, Message, Chat
from telegram.error import BadRequest
from telegram.ext import ContextTypes, CommandHandler, filters

from tg_bot import dispatcher, LOGGER
from tg_bot.__main__ import DATA_IMPORT
from tg_bot.modules.helper_funcs.chat_status import user_admin


@user_admin
async def import_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat

    # نعمل فقط مع ملف مرفق كرد
    if msg.reply_to_message and msg.reply_to_message.document:
        try:
            file_info = await context.bot.get_file(msg.reply_to_message.document.file_id)
        except BadRequest:
            await msg.reply_text("حاول تنزيل الملف وإعادة رفعه بنفسك قبل الاستيراد - يبدو أن هناك مشكلة في هذا الملف!")
            return

        with BytesIO() as file:
            await file_info.download_to_drive(out=file)
            file.seek(0)
            data = json.load(file)

        # نستورد لمجموعة واحدة فقط
        if len(data) > 1 and str(chat.id) not in data:
            await msg.reply_text("يوجد أكثر من مجموعة في هذا الملف، ولا يوجد مجموعة بنفس معرف هذه المجموعة - كيف أختار ما أستورده؟")
            return

        # اختيار مصدر البيانات
        if str(chat.id) in data:
            data = data[str(chat.id)]['hashes']
        else:
            data = data[list(data.keys())[0]]['hashes']

        try:
            for mod in DATA_IMPORT:
                mod.__import_data__(str(chat.id), data)
        except Exception:
            await msg.reply_text("حدث استثناء أثناء استعادة بياناتك. قد لا تكون العملية كاملة. إذا كنت تواجه مشاكل في هذا، راسل @MarieSupport مع ملف النسخة الاحتياطية حتى يمكن تصحيح المشكلة. المالكون سيسعدون بمساعدتك، وكل خطأ يتم الإبلاغ عنه يجعلني أفضل! شكرًا! :)")
            LOGGER.exception("Import for chatid %s with name %s failed.", str(chat.id), str(chat.title))
            return

        await msg.reply_text("تم استيراد النسخة الاحتياطية بالكامل. مرحبا بعودتك! :D")


@user_admin
async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    await msg.reply_text("هذا الأمر ليس جاهزًا بعد، لكنه سيكون متاحًا قريبًا!")


__mod_name__ = "النسخ الاحتياطي"

__help__ = """
*للمشرفين فقط:*
- /import: قم بالرد على ملف نسخة احتياطية من Group Butler لاستيراد أكبر قدر ممكن، مما يجعل النقل بسيطًا للغاية! ملاحظة: لا يمكن استيراد الملفات/الصور بسبب قيود تيليجرام.
- /export: !!! هذا الأمر ليس جاهزًا بعد، لكنه سيأتي قريبًا!
"""

IMPORT_HANDLER = CommandHandler("import", import_data, filters=filters.ChatType.GROUPS)
EXPORT_HANDLER = CommandHandler("export", export_data, filters=filters.ChatType.GROUPS)

dispatcher.add_handler(IMPORT_HANDLER)
# dispatcher.add_handler(EXPORT_HANDLER)  # معطل حتى يكتمل
