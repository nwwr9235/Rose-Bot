import json
from io import BytesIO
from typing import Optional

from telegram import Message, Chat, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, run_async

from tg_bot import dispatcher, LOGGER
from tg_bot.__main__ import DATA_IMPORT
from tg_bot.modules.helper_funcs.chat_status import user_admin


@run_async
@user_admin
def import_data(bot: Bot, update):
    msg = update.effective_message
    chat = update.effective_chat
    # نعمل فقط مع مستند
    if msg.reply_to_message and msg.reply_to_message.document:
        try:
            file_info = bot.get_file(msg.reply_to_message.document.file_id)
        except BadRequest:
            msg.reply_text("حاول تنزيل وإعادة رفع الملف بنفسك قبل الاستيراد - يبدو أن هذا الملف به مشكلة!")
            return

        with BytesIO() as file:
            file_info.download(out=file)
            file.seek(0)
            data = json.load(file)

        # استيراد مجموعة واحدة فقط
        if len(data) > 1 and str(chat.id) not in data:
            msg.reply_text("يوجد أكثر من مجموعة واحدة في هذا الملف، ولا يوجد أي منها بنفس معرف هذه المجموعة - كيف أختار ما أستورده؟")
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
            msg.reply_text("حدث استثناء أثناء استعادة بياناتك. قد لا تكون العملية مكتملة. إذا كنت تواجه مشاكل مع هذا، راسل @MarieSupport مع ملف النسخ الاحتياطي الخاص بك لتصحيح الخطأ. سيكون مالكي سعداء بالمساعدة، وكل خطأ يتم الإبلاغ عنه يجعلني أفضل! شكراً! :)")
            LOGGER.exception("فشل الاستيراد للدردشة %s بالاسم %s.", str(chat.id), str(chat.title))
            return

        # TODO: بعض منطق الروابط
        # ملاحظة: النظر في صلاحيات الافتراضية؟
        msg.reply_text("تم استيراد النسخ الاحتياطي بالكامل. مرحباً بعودتك! :D")


@run_async
@user_admin
def export_data(bot: Bot, update: Update):
    msg = update.effective_message
    msg.reply_text("هذا الأمر قيد التطوير حاليًا.")


# ================== المساعدة ==================
__mod_name__ = "النسخ الاحتياطي"

__help__ = """
*للمشرفين فقط:*
- /import: قم بالرد على ملف نسخ احتياطي من Group Butler لاستيراد أكبر قدر ممكن، مما يجعل النقل بسيطاً جداً! ملاحظة أن الملفات/الصور لا يمكن استيرادها بسبب قيود تليجرام.
- /export: !!! هذا ليس أمراً بعد، لكنه سيأتي قريباً!

*الأوامر العربية (بدون /):*
استيراد: استيراد بيانات النسخ الاحتياطي (بالرد على الملف)
تصدير: تصدير بيانات النسخ الاحتياطي (غير مفعل بعد)
"""

IMPORT_HANDLER = CommandHandler("import", import_data)
EXPORT_HANDLER = CommandHandler("export", export_data)

# معالجات الأوامر العربية
IMPORT_AR_HANDLER = CommandHandler("استيراد", import_data)
EXPORT_AR_HANDLER = CommandHandler("تصدير", export_data)

dispatcher.add_handler(IMPORT_HANDLER)
# dispatcher.add_handler(EXPORT_HANDLER) # معلق مؤقتاً لأن التصدير غير مفعل

dispatcher.add_handler(IMPORT_AR_HANDLER)
# dispatcher.add_handler(EXPORT_AR_HANDLER) # معلق مؤقتاً
