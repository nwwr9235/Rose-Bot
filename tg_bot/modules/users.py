import html
import json
import random
from datetime import datetime
from typing import Optional, List

import requests
from telegram import Message, Chat, Update, Bot, MessageEntity
from telegram import ParseMode
from telegram.ext import CommandHandler, run_async, Filters, MessageHandler
from telegram.utils.helpers import escape_markdown, mention_html

from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS, BAN_STICKER
from tg_bot.__main__ import GDPR
from tg_bot.__main__ import STATS, USER_INFO
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.helper_funcs.filters import CustomFilters

# ... (ثوابت RUN_STRINGS, SLAP_TEMPLATES, ITEMS, THROW, HIT كما هي) ...


@run_async
def runs(bot: Bot, update: Update):
    update.effective_message.reply_text(random.choice(RUN_STRINGS))


@run_async
def slap(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message
    reply_text = msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text

    if msg.from_user.username:
        curr_user = "@" + escape_markdown(msg.from_user.username)
    else:
        curr_user = "[{}](tg://user?id={})".format(msg.from_user.first_name, msg.from_user.id)

    user_id = extract_user(update.effective_message, args)
    if user_id:
        slapped_user = bot.get_chat(user_id)
        user1 = curr_user
        if slapped_user.username:
            user2 = "@" + escape_markdown(slapped_user.username)
        else:
            user2 = "[{}](tg://user?id={})".format(slapped_user.first_name, slapped_user.id)
    else:
        user1 = "[{}](tg://user?id={})".format(bot.first_name, bot.id)
        user2 = curr_user

    temp = random.choice(SLAP_TEMPLATES)
    item = random.choice(ITEMS)
    hit = random.choice(HIT)
    throw = random.choice(THROW)

    repl = temp.format(user1=user1, user2=user2, item=item, hits=hit, throws=throw)
    reply_text(repl, parse_mode=ParseMode.MARKDOWN)


@run_async
def get_bot_ip(bot: Bot, update: Update):
    """يرسل عنوان IP الخاص بالبوت (للمالك فقط)."""
    res = requests.get("http://ipinfo.io/ip")
    update.message.reply_text(res.text)


@run_async
def get_id(bot: Bot, update: Update, args: List[str]):
    user_id = extract_user(update.effective_message, args)
    if user_id:
        if update.effective_message.reply_to_message and update.effective_message.reply_to_message.forward_from:
            user1 = update.effective_message.reply_to_message.from_user
            user2 = update.effective_message.reply_to_message.forward_from
            update.effective_message.reply_text(
                f"المرسل الأصلي {escape_markdown(user2.first_name)} معرفه `{user2.id}`.\n"
                f"المُعيد {escape_markdown(user1.first_name)} معرفه `{user1.id}`.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            user = bot.get_chat(user_id)
            update.effective_message.reply_text(
                f"معرف {escape_markdown(user.first_name)} هو `{user.id}`.",
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        chat = update.effective_chat
        if chat.type == "private":
            update.effective_message.reply_text(f"معرفك هو `{chat.id}`.", parse_mode=ParseMode.MARKDOWN)
        else:
            update.effective_message.reply_text(f"معرف هذه المجموعة هو `{chat.id}`.", parse_mode=ParseMode.MARKDOWN)


@run_async
def get_id_arabic_single(bot: Bot, update: Update):
    """الأمر العربي 'ا' - يعرض معرف المستخدم (مثل /id)."""
    get_id(bot, update, args=[])


@run_async
def get_user_photo(bot: Bot, update: Update):
    """الأمر العربي 'اا' - يعرض أحدث صورة للمستخدم (بالرد أو بذكره)."""
    message = update.effective_message
    user_id = extract_user(message, [])
    if not user_id:
        user_id = message.from_user.id

    # جلب آخر صورة بروفايل
    photos = bot.get_user_profile_photos(user_id, limit=1)
    if photos.total_count > 0:
        file_id = photos.photos[0][-1].file_id  # آخر صورة (أعلى دقة)
        message.reply_photo(photo=file_id, caption="أحدث صورة للمستخدم")
    else:
        message.reply_text("المستخدم ليس لديه صورة شخصية.")


@run_async
def info(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message
    user_id = extract_user(msg, args)

    if user_id:
        user = bot.get_chat(user_id)
    elif not msg.reply_to_message and not args:
        user = msg.from_user
    else:
        msg.reply_text("لا يمكنني استخراج المستخدم من هذا.")
        return

    text = "<b>معلومات المستخدم</b>:" \
           "\nالمعرف: <code>{}</code>" \
           "\nالاسم الأول: {}".format(user.id, html.escape(user.first_name))

    if user.last_name:
        text += "\nالاسم الأخير: {}".format(html.escape(user.last_name))

    if user.username:
        text += "\nاسم المستخدم: @{}".format(html.escape(user.username))

    text += "\nرابط دائم للمستخدم: {}".format(mention_html(user.id, "رابط"))

    if user.id == OWNER_ID:
        text += "\n\nهذا الشخص هو مالكي – لن أفعل أي شيء ضده!"
    else:
        if user.id in SUDO_USERS:
            text += "\nهذا الشخص هو أحد مستخدمي sudo! تقريبًا بنفس قوة المالك – فاحذر."
        else:
            if user.id in SUPPORT_USERS:
                text += "\nهذا الشخص هو أحد مستخدمي الدعم! ليس مثل sudo، لكن يمكنه حظرك."
            if user.id in WHITELIST_USERS:
                text += "\nهذا الشخص مدرج في القائمة البيضاء! لا يمكنني حظره أو طرده."

    for mod in USER_INFO:
        mod_info = mod.__user_info__(user.id).strip()
        if mod_info:
            text += "\n\n" + mod_info

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
def get_time(bot: Bot, update: Update, args: List[str]):
    location = " ".join(args)
    if location.lower() == bot.first_name.lower():
        update.effective_message.reply_text("دائمًا وقت المطرقة بالنسبة لي!")
        bot.send_sticker(update.effective_chat.id, BAN_STICKER)
        return

    res = requests.get(GMAPS_LOC, params=dict(address=location))
    if res.status_code == 200:
        loc = json.loads(res.text)
        if loc.get('status') == 'OK':
            lat = loc['results'][0]['geometry']['location']['lat']
            long = loc['results'][0]['geometry']['location']['lng']

            country = None
            city = None

            address_parts = loc['results'][0]['address_components']
            for part in address_parts:
                if 'country' in part['types']:
                    country = part.get('long_name')
                if 'administrative_area_level_1' in part['types'] and not city:
                    city = part.get('long_name')
                if 'locality' in part['types']:
                    city = part.get('long_name')

            if city and country:
                location = "{}, {}".format(city, country)
            elif country:
                location = country

            timenow = int(datetime.utcnow().timestamp())
            res = requests.get(GMAPS_TIME, params=dict(location="{},{}".format(lat, long), timestamp=timenow))
            if res.status_code == 200:
                offset = json.loads(res.text)['dstOffset']
                timestamp = json.loads(res.text)['rawOffset']
                time_there = datetime.fromtimestamp(timenow + timestamp + offset).strftime("%H:%M:%S يوم %A %d %B")
                update.message.reply_text(f"الوقت في {location} هو {time_there}")


@run_async
def echo(bot: Bot, update: Update):
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message
    if message.reply_to_message:
        message.reply_to_message.reply_text(args[1])
    else:
        message.reply_text(args[1], quote=False)
    message.delete()


@run_async
def gdpr(bot: Bot, update: Update):
    update.effective_message.reply_text("جاري حذف البيانات الشخصية...")
    for mod in GDPR:
        mod.__gdpr__(update.effective_user.id)

    update.effective_message.reply_text(
        "تم حذف بياناتك الشخصية.\n\n"
        "لاحظ أن هذا لن يلغي حظرك من أي محادثة، فهذه بيانات تليجرام وليست بيانات البوت. "
        "الفيضانات والتحذيرات والحظر العام محفوظة أيضًا، وفقًا لـ "
        "[هذا](https://ico.org.uk/for-organisations/guide-to-the-general-data-protection-regulation-gdpr/individual-rights/right-to-erasure/)، "
        "الذي ينص بوضوح على أن حق المحو لا ينطبق على \"أداء مهمة تُنفذ في المصلحة العامة\"، كما هو الحال مع البيانات المذكورة.",
        parse_mode=ParseMode.MARKDOWN
    )


MARKDOWN_HELP = """
ماركداون هي أداة تنسيق قوية يدعمها تليجرام. {} قام بتحسينات للتأكد من تحليل الرسائل المحفوظة بشكل صحيح، وللسماح لك بإنشاء أزرار.

- <code>_نص مائل_</code>: وضع النص بين '_' ينتج نصًا مائلاً.
- <code>*نص عريض*</code>: وضع النص بين '*' ينتج نصًا عريضًا.
- <code>`كود`</code>: وضع النص بين '`' ينتج نصًا أحادي المسافة، يُعرف أيضًا بالـ 'كود'.
- <code>[نص ما](رابط ما)</code>: ينشئ رابطًا – ستظهر الرسالة <code>نص ما</code>، وعند النقر عليها ستفتح الصفحة في <code>رابط ما</code>.
مثال: <code>[اختبار](example.com)</code>

- <code>[نص زر](buttonurl:رابط ما)</code>: هذا تحسين خاص يسمح للمستخدمين بوجود أزرار تليجرام في نص الماركداون. <code>نص زر</code> هو ما سيظهر على الزر، و<code>رابط ما</code> هو الرابط الذي سيُفتح.
مثال: <code>[هذا زر](buttonurl:example.com)</code>

إذا أردت عدة أزرار في نفس السطر، استخدم :same، كما يلي:
<code>[واحد](buttonurl://example.com)
[اثنان](buttonurl://google.com:same)</code>
سينشئ هذا زرين في سطر واحد، بدلاً من زر لكل سطر.

تذكر أن رسالتك <b>يجب</b> أن تحتوي على نص آخر غير الأزرار فقط!
""".format(dispatcher.bot.first_name)


@run_async
def markdown_help(bot: Bot, update: Update):
    update.effective_message.reply_text(MARKDOWN_HELP, parse_mode=ParseMode.HTML)
    update.effective_message.reply_text("جرب إعادة توجيه الرسالة التالية إلي، وسترى النتيجة!")
    update.effective_message.reply_text(
        "/save test هذا اختبار ماركداون. _مائل_, *عريض*, `كود`, "
        "[رابط](example.com) [زر](buttonurl:github.com) "
        "[زر2](buttonurl://google.com:same)"
    )


@run_async
def stats(bot: Bot, update: Update):
    update.effective_message.reply_text("الإحصائيات الحالية:\n" + "\n".join([mod.__stats__() for mod in STATS]))


@run_async
def stickerid(bot: Bot, update: Update):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.sticker:
        update.effective_message.reply_text(
            f"مرحبًا [](tg://user?id={msg.from_user.id})، معرّف الملصق الذي ترد عليه هو:\n```{escape_markdown(msg.reply_to_message.sticker.file_id)}```",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        update.effective_message.reply_text(
            f"مرحبًا [](tg://user?id={msg.from_user.id})، يرجى الرد على رسالة ملصق للحصول على معرف الملصق.",
            parse_mode=ParseMode.MARKDOWN
        )


@run_async
def getsticker(bot: Bot, update: Update):
    msg = update.effective_message
    chat_id = update.effective_chat.id
    if msg.reply_to_message and msg.reply_to_message.sticker:
        bot.sendChatAction(chat_id, "typing")
        update.effective_message.reply_text(
            f"مرحبًا [](tg://user?id={msg.from_user.id})، يرجى التحقق من الملف المطلوب أدناه.\nاستخدم هذه الميزة بحكمة!",
            parse_mode=ParseMode.MARKDOWN
        )
        bot.sendChatAction(chat_id, "upload_document")
        file_id = msg.reply_to_message.sticker.file_id
        newFile = bot.get_file(file_id)
        newFile.download('sticker.png')
        bot.sendDocument(chat_id, document=open('sticker.png', 'rb'))
        bot.sendChatAction(chat_id, "upload_photo")
        bot.send_photo(chat_id, photo=open('sticker.png', 'rb'))
    else:
        bot.sendChatAction(chat_id, "typing")
        update.effective_message.reply_text(
            f"مرحبًا [](tg://user?id={msg.from_user.id})، يرجى الرد على رسالة ملصق للحصول على صورة الملصق.",
            parse_mode=ParseMode.MARKDOWN
        )


# ================== المساعدة ==================
__help__ = """
/id: الحصول على معرف المجموعة الحالية. إذا استخدمت بالرد على رسالة، تحصل على معرف ذلك المستخدم.
/ا: نفس الأمر لكن بحرف عربي واحد.
/اا: الحصول على أحدث صورة شخصية للمستخدم (بالرد أو بذكره).
/runs: الرد بسلسلة عشوائية من مجموعة ردود.
/slap: صفع مستخدم، أو التعرض للصفع إذا لم يكن رد.
/time <مكان>: يعطي الوقت المحلي في المكان المحدد.
/info: الحصول على معلومات عن مستخدم.
/gdpr: حذف معلوماتك من قاعدة بيانات البوت (محادثات خاصة فقط).
/markdownhelp: ملخص سريع لكيفية عمل الماركداون في تليجرام – يمكن استدعاؤه فقط في المحادثات الخاصة.
/stickerid: الرد على ملصق للحصول على معرفه.
/getsticker: الرد على ملصق للحصول عليه كصورة .png وصورة عادية.
"""

__mod_name__ = "متنوع"

ID_HANDLER = DisableAbleCommandHandler("id", get_id, pass_args=True)
ID_AR_SINGLE_HANDLER = MessageHandler(Filters.regex(r'^ا(@\w+)?$'), get_id_arabic_single)  # الأمر "ا"
ID_AR_DOUBLE_HANDLER = MessageHandler(Filters.regex(r'^اا(@\w+)?$'), get_user_photo)       # الأمر "اا"

IP_HANDLER = CommandHandler("ip", get_bot_ip, filters=Filters.chat(OWNER_ID))
TIME_HANDLER = CommandHandler("time", get_time, pass_args=True)
RUNS_HANDLER = DisableAbleCommandHandler("runs", runs)
SLAP_HANDLER = DisableAbleCommandHandler("slap", slap, pass_args=True)
INFO_HANDLER = DisableAbleCommandHandler("info", info, pass_args=True)
ECHO_HANDLER = CommandHandler("echo", echo, filters=Filters.user(OWNER_ID))
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help, filters=Filters.private)
STATS_HANDLER = CommandHandler("stats", stats, filters=CustomFilters.sudo_filter)
GDPR_HANDLER = CommandHandler("gdpr", gdpr, filters=Filters.private)
STICKERID_HANDLER = DisableAbleCommandHandler("stickerid", stickerid)
GETSTICKER_HANDLER = DisableAbleCommandHandler("getsticker", getsticker)

dispatcher.add_handler(ID_HANDLER)
dispatcher.add_handler(ID_AR_SINGLE_HANDLER)
dispatcher.add_handler(ID_AR_DOUBLE_HANDLER)
dispatcher.add_handler(IP_HANDLER)
dispatcher.add_handler(TIME_HANDLER)
dispatcher.add_handler(RUNS_HANDLER)
dispatcher.add_handler(SLAP_HANDLER)
dispatcher.add_handler(INFO_HANDLER)
dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)
dispatcher.add_handler(STATS_HANDLER)
dispatcher.add_handler(GDPR_HANDLER)
dispatcher.add_handler(STICKERID_HANDLER)
dispatcher.add_handler(GETSTICKER_HANDLER)
