import json
from pprint import pprint

import requests
from telegram import Update, Bot
from telegram.ext import CommandHandler, MessageHandler, Filters

from tg_bot import dispatcher

# Open API key
API_KEY = "6ae0c3a0-afdc-4532-a810-82ded0054236"
URL = "http://services.gingersoftware.com/Ginger/correct/json/GingerTheText"


def translate(bot: Bot, update: Update):
    if update.effective_message.reply_to_message:
        msg = update.effective_message.reply_to_message

        params = dict(
            lang="US",
            clientVersion="2.0",
            apiKey=API_KEY,
            text=msg.text
        )

        res = requests.get(URL, params=params)
        changes = json.loads(res.text).get('LightGingerTheTextResult')
        curr_string = ""

        prev_end = 0

        for change in changes:
            start = change.get('From')
            end = change.get('To') + 1
            suggestions = change.get('Suggestions')
            if suggestions:
                sugg_str = suggestions[0].get('Text')
                curr_string += msg.text[prev_end:start] + sugg_str

                prev_end = end

        curr_string += msg.text[prev_end:]
        print(curr_string)
        update.effective_message.reply_text(curr_string)


# ================== المساعدة ==================
__help__ = """
- /t: بالرد على رسالة، سيرد بنسخة مصححة نحوياً.

*الأمر العربي (بدون /):*
تصحيح <بالرد>: تصحيح الأخطاء النحوية للرسالة التي تم الرد عليها.
"""

__mod_name__ = "مصحح لغوي"

TRANSLATE_HANDLER = CommandHandler('t', translate)

# معالج الأمر العربي
TRANSLATE_AR_HANDLER = CommandHandler('تصحيح', translate)

dispatcher.add_handler(TRANSLATE_HANDLER)
dispatcher.add_handler(TRANSLATE_AR_HANDLER)
