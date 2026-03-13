from telegram import Update, Bot
from telegram.ext import run_async

from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot import dispatcher

from requests import get


@run_async
def ud(bot: Bot, update: Update):
    message = update.effective_message
    text = message.text[len('/ud '):]
    results = get(f'http://api.urbandictionary.com/v0/define?term={text}').json()
    try:
        reply_text = f'الكلمة: {text}\nالتعريف: {results["list"][0]["definition"]}'
    except:
        reply_text = "لم يتم العثور على تعريف."
    message.reply_text(reply_text)


# ================== المساعدة ==================
__help__ = """
- /ud <كلمة>: اكتب الكلمة أو التعبير الذي تريد البحث عنه. مثال: /ud telegram

*الأمر العربي (بدون /):*
قاموس <كلمة>: البحث عن تعريف لكلمة في قاموس Urban Dictionary.
"""

__mod_name__ = "قاموس Urban"

ud_handle = DisableAbleCommandHandler("ud", ud)

# معالج الأمر العربي
ud_ar_handle = DisableAbleCommandHandler("قاموس", ud)

dispatcher.add_handler(ud_handle)
dispatcher.add_handler(ud_ar_handle)
