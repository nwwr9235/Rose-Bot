import html
import json
import random
from datetime import datetime
from typing import Optional, List

import requests
from telegram import Update, Message, Chat, User, MessageEntity
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler, filters
from telegram.helpers import escape_markdown, mention_html

from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS, BAN_STICKER
from tg_bot.__main__ import GDPR
from tg_bot.__main__ import STATS, USER_INFO
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.helper_funcs.filters import CustomFilters

# =================== نصوص عربية للردود العشوائية ===================
RUN_STRINGS = (
    "إلى أين تظن أنك ذاهب؟",
    "هاه؟ ماذا؟ هل هربوا؟",
    "وززززز... هاه؟ ماذا؟ آه، فقط هم مرة أخرى، لا بأس.",
    "ارجع إلى هنا!",
    "ليس بهذه السرعة...",
    "انتبه للحائط!",
    "لا تتركني وحدي معهم!!",
    "أنت تركض، أنت تموت.",
    "المزاح عليك، أنا في كل مكان",
    "ستندم على ذلك...",
    "يمكنك أيضًا تجربة /kickme، سمعت أنها ممتعة.",
    "اذهب أزعج شخصًا آخر، لا أحد هنا يهتم.",
    "يمكنك الركض، لكن لا يمكنك الاختباء.",
    "هل هذا كل ما لديك؟",
    "أنا خلفك...",
    "لقد جاءك رفقة!",
    "يمكننا فعل ذلك بالطريقة السهلة، أو بالطريقة الصعبة.",
    "أنت فقط لا تفهم، أليس كذلك؟",
    "نعم، الأفضل أن تركض!",
    "رجاءً، ذكرني كم أنا مهتم؟",
    "كنت سأركض أسرع لو كنت مكانك.",
    "هذا بالتأكيد هو الروبوت الذي نبحث عنه.",
    "لتكن الاحتمالات في صالحك دائمًا.",
    "كلمات أخيرة مشهورة.",
    "واختفوا إلى الأبد، لم يُروا مرة أخرى.",
    "\"أوه، انظر إلي! أنا رائع جدًا، أستطيع الهرب من البوت!\" - هذا الشخص",
    "أجل أجل، فقط اضغط /kickme بالفعل.",
    "تفضل، خذ هذا الخاتم واتجه إلى موردور بينما أنت في ذلك.",
    "تقول الأسطورة أنهم ما زالوا يركضون...",
    "على عكس هاري بوتر، والديك لا يستطيعان حمايتك مني.",
    "الخوف يؤدي إلى الغضب. الغضب يؤدي إلى الكراهية. الكراهية تؤدي إلى المعاناة. إذا استمررت في الركض خوفًا، فقد تكون فادير القادم.",
    "بعد عدة حسابات، قررت أن اهتمامي بمغامراتك هو بالضبط 0.",
    "تقول الأسطورة أنهم ما زالوا يركضون.",
    "استمر، لسنا متأكدين أننا نريدك هنا على أي حال.",
    "أنت ساحر- أوه. انتظر. أنت لست هاري، استمر في الحركة.",
    "ممنوع الركض في الممرات!",
    "أراك لاحقًا، حبيبي.",
    "من أطلق الكلاب؟",
    "إنه مضحك، لأن لا أحد يهتم.",
    "آه، يا للهدر. لقد أحببت ذلك.",
    "بصراحة، عزيزتي، أنا لا أهتم.",
    "الميلك شيك الخاص بي يجذب كل الأولاد إلى الفناء... لذا اركض أسرع!",
    "لا تتحمل الحقيقة!",
    "منذ زمن بعيد، في مجرة بعيدة بعيدة... كان أحدهم ليهتم بذلك. لكن ليس بعد الآن.",
    "مرحبًا، انظر إليهم! إنهم يهربون من مطرقة الحظر الحتمية... لطيف.",
    "هان أطلق النار أولاً. وكذلك سأفعل.",
    "وراء ماذا تركض، أرنب أبيض؟",
    "كما يقول الطبيب... اركض!",
)

# قوالب الصفع (مترجمة)
SLAP_TEMPLATES = (
    "{user1} {hits} {user2} بـ {item}.",
    "{user1} {hits} {user2} على وجهه بـ {item}.",
    "{user1} {hits} {user2} قليلاً بـ {item}.",
    "{user1} {throws} {item} على {user2}.",
    "{user1} يمسك {item} و {throws} على وجه {user2}.",
    "{user1} يطلق {item} في اتجاه {user2}.",
    "{user1} يبدأ بصفع {user2} بـ {item}.",
    "{user1} يثبت {user2} أرضًا ويكرر {hits} بـ {item}.",
    "{user1} يمسك {item} و {hits} {user2} به.",
    "{user1} يربط {user2} على كرسي و {throws} {item} عليه.",
    "{user1} دفع دفعًا ودودًا لمساعدة {user2} على تعلم السباحة في الحمم.",
)

# الأدوات المستخدمة في الصفع
ITEMS = (
    "مقلاة من حديد زهر",
    "تروتة كبيرة",
    "مضرب بيسبول",
    "مضرب كريكيت",
    "عصا خشبية",
    "مسمار",
    "طابعة",
    "مجرفة",
    "شاشة CRT",
    "كتاب فيزياء",
    "محمصة خبز",
    "صورة ريتشارد ستالمان",
    "تلفاز",
    "شاحنة خمسة أطنان",
    "لفة شريط لاصق",
    "كتاب",
    "لابتوب",
    "تلفاز قديم",
    "كيس صخور",
    "تروتة قوس قزح",
    "دجاجة مطاطية",
    "مضرب مسامير",
    "طفاية حريق",
    "صخرة ثقيلة",
    "كتلة تراب",
    "خلية نحل",
    "قطعة لحم فاسد",
    "دب",
    "طن من الطوب",
)

THROW = (
    "يرمي",
    "يقذف",
    "يلقي",
    "يقذف بقوة",
)

HIT = (
    "يضرب",
    "يلكم",
    "يصفع",
    "يصفع بقوة",
    "يهشم",
)

GMAPS_LOC = "https://maps.googleapis.com/maps/api/geocode/json"
GMAPS_TIME = "https://maps.googleapis.com/maps/api/timezone/json"


# =================== دوال الأوامر العربية (غير متزامنة) ===================
async def runs_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر ركض (عربي)"""
    await update.effective_message.reply_text(random.choice(RUN_STRINGS))


async def slap_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر صفع (عربي)"""
    await slap(update, context)


async def id_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر ايدي (عربي)"""
    await get_id(update, context)


async def info_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر معلومات (عربي)"""
    await info(update, context)


async def time_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر وقت (عربي)"""
    await get_time(update, context)


async def stickerid_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر ستكر (عربي)"""
    await stickerid(update, context)


async def getsticker_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر صوره ستكر (عربي)"""
    await getsticker(update, context)


async def gdpr_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر gdpr (عربي)"""
    await gdpr(update, context)


async def markdownhelp_arabic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر مارك داون (عربي)"""
    await markdown_help(update, context)


# =================== الدوال الأصلية (محدثة وغير متزامنة) ===================
async def runs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر runs (إنجليزي)"""
    await update.effective_message.reply_text(random.choice(RUN_STRINGS))


async def slap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر slap (إنجليزي)"""
    msg = update.effective_message
    args = context.args

    reply_text = msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text

    # تحديد اسم المرسل
    if msg.from_user.username:
        curr_user = "@" + escape_markdown(msg.from_user.username)
    else:
        curr_user = f"[{escape_markdown(msg.from_user.first_name)}](tg://user?id={msg.from_user.id})"

    user_id = extract_user(update.effective_message, args)
    if user_id:
        slapped_user = await context.bot.get_chat(user_id)
        user1 = curr_user
        if slapped_user.username:
            user2 = "@" + escape_markdown(slapped_user.username)
        else:
            user2 = f"[{escape_markdown(slapped_user.first_name)}](tg://user?id={slapped_user.id})"
    else:
        # إذا لم يتم تحديد هدف، يستهدف البوت المرسل
        user1 = f"[{escape_markdown(context.bot.first_name)}](tg://user?id={context.bot.id})"
        user2 = curr_user

    temp = random.choice(SLAP_TEMPLATES)
    item = random.choice(ITEMS)
    hit = random.choice(HIT)
    throw = random.choice(THROW)

    repl = temp.format(user1=user1, user2=user2, item=item, hits=hit, throws=throw)

    await reply_text(repl, parse_mode=ParseMode.MARKDOWN)


async def get_bot_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال عنوان IP الخاص بالبوت (للمالك فقط)"""
    res = requests.get("http://ipinfo.io/ip")
    await update.message.reply_text(res.text)


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر id / ايدي"""
    user_id = extract_user(update.effective_message, context.args)
    if user_id:
        if (update.effective_message.reply_to_message and 
            update.effective_message.reply_to_message.forward_from):
            user1 = update.effective_message.reply_to_message.from_user
            user2 = update.effective_message.reply_to_message.forward_from
            await update.effective_message.reply_text(
                f"المرسل الأصلي، {escape_markdown(user2.first_name)}، معرفه `{user2.id}`.\n"
                f"المُرسِل، {escape_markdown(user1.first_name)}، معرفه `{user1.id}`.",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            user = await context.bot.get_chat(user_id)
            await update.effective_message.reply_text(
                f"معرف {escape_markdown(user.first_name)} هو `{user.id}`.",
                parse_mode=ParseMode.MARKDOWN,
            )
    else:
        chat = update.effective_chat
        if chat.type == "private":
            await update.effective_message.reply_text(
                f"معرفك هو `{chat.id}`.", parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.effective_message.reply_text(
                f"معرف هذه المجموعة هو `{chat.id}`.", parse_mode=ParseMode.MARKDOWN
            )


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر info / معلومات"""
    msg = update.effective_message
    user_id = extract_user(update.effective_message, context.args)

    if user_id:
        user = await context.bot.get_chat(user_id)

    elif not msg.reply_to_message and not context.args:
        user = msg.from_user

    elif not msg.reply_to_message and (
        not context.args
        or (
            len(context.args) >= 1
            and not context.args[0].startswith("@")
            and not context.args[0].isdigit()
            and not msg.parse_entities([MessageEntity.TEXT_MENTION])
        )
    ):
        await msg.reply_text("لا أستطيع استخراج مستخدم من هذا.")
        return

    else:
        return

    text = f"<b>معلومات المستخدم</b>:\n" \
           f"المعرف: <code>{user.id}</code>\n" \
           f"الاسم الأول: {html.escape(user.first_name)}"

    if user.last_name:
        text += f"\nالاسم الأخير: {html.escape(user.last_name)}"

    if user.username:
        text += f"\nاسم المستخدم: @{html.escape(user.username)}"

    text += f"\nرابط المستخدم الدائم: {mention_html(user.id, 'رابط')}"

    if user.id == OWNER_ID:
        text += "\n\nهذا الشخص هو مالكي - لن أفعل أي شيء ضده!"
    else:
        if user.id in SUDO_USERS:
            text += "\nهذا الشخص هو أحد مستخدمي sudo! " \
                    "تقريبًا بنفس قوة المالك - لذا انتبه."
        else:
            if user.id in SUPPORT_USERS:
                text += "\nهذا الشخص هو أحد مستخدمي الدعم! " \
                        "ليس مثل sudo، لكن يمكنه حظرك من الخريطة."

            if user.id in WHITELIST_USERS:
                text += "\nهذا الشخص مدرج في القائمة البيضاء! " \
                        "هذا يعني أنه لا يُسمح لي بحظرهم / طردهم."

    for mod in USER_INFO:
        mod_info = mod.__user_info__(user.id).strip()
        if mod_info:
            text += "\n\n" + mod_info

    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر time / وقت"""
    location = " ".join(context.args)
    if location.lower() == context.bot.first_name.lower():
        await update.effective_message.reply_text("إنه دائمًا وقت المطرقة بالنسبة لي!")
        await context.bot.send_sticker(update.effective_chat.id, BAN_STICKER)
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
                location = f"{city}, {country}"
            elif country:
                location = country

            timenow = int(datetime.utcnow().timestamp())
            res = requests.get(
                GMAPS_TIME,
                params=dict(location=f"{lat},{long}", timestamp=timenow)
            )
            if res.status_code == 200:
                offset = json.loads(res.text)['dstOffset']
                timestamp = json.loads(res.text)['rawOffset']
                time_there = datetime.fromtimestamp(
                    timenow + timestamp + offset
                ).strftime("%H:%M:%S يوم %A %d %B")
                await update.message.reply_text(f"الوقت في {location} هو {time_there}")
            else:
                await update.message.reply_text("تعذر الحصول على معلومات المنطقة الزمنية.")
        else:
            await update.message.reply_text("تعذر العثور على الموقع.")
    else:
        await update.message.reply_text("تعذر الاتصال بخدمة الخرائط.")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر echo (للمالك فقط)"""
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message
    if len(args) >= 2:
        if message.reply_to_message:
            await message.reply_to_message.reply_text(args[1])
        else:
            await message.reply_text(args[1], quote=False)
        await message.delete()


async def gdpr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر gdpr - حذف البيانات الشخصية"""
    await update.effective_message.reply_text("جارٍ حذف البيانات القابلة للتحديد...")
    for mod in GDPR:
        mod.__gdpr__(update.effective_user.id)

    await update.effective_message.reply_text(
        "تم حذف بياناتك الشخصية.\n\n"
        "لاحظ أن هذا لن يلغي حظرك من أي محادثات، فهذه بيانات تيليجرام وليست بيانات ماري. "
        "الفيضانات والتحذيرات والحظر العام محفوظة أيضًا، وفقًا "
        "[لهذا](https://ico.org.uk/for-organisations/guide-to-the-general-data-protection-regulation-gdpr/individual-rights/right-to-erasure/)، "
        "الذي ينص بوضوح على أن الحق في المحو لا ينطبق "
        "\"لأداء مهمة تنفذ في المصلحة العامة\"، كما هو الحال مع البيانات المذكورة.",
        parse_mode=ParseMode.MARKDOWN,
    )


MARKDOWN_HELP = """
الماركداون أداة تنسيق قوية جدًا يدعمها تيليجرام. {} لديه بعض التحسينات، لضمان تحليل الرسائل المحفوظة بشكل صحيح، والسماح لك بإنشاء أزرار.

- <code>_مائل_</code>: وضع النص بين '_' ينتج نصًا مائلًا
- <code>*عريض*</code>: وضع النص بين '*' ينتج نصًا عريضًا
- <code>`كود`</code>: وضع النص بين '`' ينتج نصًا أحادي المسافة، يُعرف أيضًا باسم 'كود'
- <code>[نص](رابط)</code>: هذا ينشئ رابطًا - ستظهر الرسالة <code>نص</code> فقط، والنقر عليها يفتح الرابط.
  مثال: <code>[اختبار](example.com)</code>

- <code>[نص زر](buttonurl:رابط)</code>: هذا تحسين خاص يسمح للمستخدمين بالحصول على أزرار تيليجرام في الماركداون الخاص بهم. <code>نص زر</code> هو ما سيظهر على الزر، و <code>رابط</code> هو الرابط الذي سيتم فتحه.
  مثال: <code>[هذا زر](buttonurl:example.com)</code>

إذا أردت أزرارًا متعددة في نفس السطر، استخدم :same، مثل:
<code>[واحد](buttonurl://example.com)
[اثنان](buttonurl://google.com:same)</code>
هذا ينشئ زرين في سطر واحد، بدلاً من زر لكل سطر.

ضع في اعتبارك أن رسالتك <b>يجب</b> أن تحتوي على نص آخر غير الأزرار فقط!
""".format(context.bot.first_name)  # سيتم تعيين context لاحقًا


async def markdown_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر markdownhelp / مارك داون"""
    # تحديث اسم البوت في النص
    help_text = MARKDOWN_HELP.replace("{}", context.bot.first_name)
    await update.effective_message.reply_text(help_text, parse_mode=ParseMode.HTML)
    await update.effective_message.reply_text(
        "جرّب إعادة توجيه الرسالة التالية إليّ، وسترى!"
    )
    await update.effective_message.reply_text(
        "/save test هذه رسالة اختبار ماركداون. _مائل_, *عريض*, `كود`, "
        "[رابط](example.com) [زر](buttonurl:github.com) "
        "[زر2](buttonurl://google.com:same)"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات البوت (للمالك)"""
    stats_text = "الإحصائيات الحالية:\n" + "\n".join([mod.__stats__() for mod in STATS])
    await update.effective_message.reply_text(stats_text)


async def stickerid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الحصول على معرف الملصق"""
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.sticker:
        sticker = msg.reply_to_message.sticker
        await update.effective_message.reply_text(
            f"مرحباً [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})، "
            f"معرف الملصق الذي ترد عليه هو:\n```{escape_markdown(sticker.file_id)}```",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await update.effective_message.reply_text(
            f"مرحباً [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})، "
            f"الرجاء الرد على رسالة ملصق للحصول على معرف الملصق.",
            parse_mode=ParseMode.MARKDOWN,
        )


async def getsticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الحصول على صورة الملصق"""
    msg = update.effective_message
    chat_id = update.effective_chat.id

    if msg.reply_to_message and msg.reply_to_message.sticker:
        await context.bot.send_chat_action(chat_id, "typing")
        await update.effective_message.reply_text(
            f"مرحباً [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})، "
            f"الملف الذي طلبته موجود أدناه.\nالرجاء استخدام هذه الميزة بحكمة!",
            parse_mode=ParseMode.MARKDOWN,
        )

        await context.bot.send_chat_action(chat_id, "upload_document")
        file_id = msg.reply_to_message.sticker.file_id
        new_file = await context.bot.get_file(file_id)
        await new_file.download_to_drive("sticker.png")
        await context.bot.send_document(chat_id, document=open("sticker.png", "rb"))

        await context.bot.send_chat_action(chat_id, "upload_photo")
        await context.bot.send_photo(chat_id, photo=open("sticker.png", "rb"))

    else:
        await context.bot.send_chat_action(chat_id, "typing")
        await update.effective_message.reply_text(
            f"مرحباً [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})، "
            f"الرجاء الرد على رسالة ملصق للحصول على صورة الملصق.",
            parse_mode=ParseMode.MARKDOWN,
        )


# =================== نص المساعدة ===================
__help__ = """
- /id: الحصول على معرف المجموعة الحالية. إذا تم استخدامه بالرد على رسالة، يحصل على معرف ذلك المستخدم.
- /runs: رد عشوائي من مجموعة ردود.
- /slap: صفع مستخدم، أو يتعرض للصفع إذا لم يكن ردًا.
- /time <مكان>: يعطي الوقت المحلي في المكان المحدد.
- /info: الحصول على معلومات عن مستخدم.
- /gdpr: حذف معلوماتك من قاعدة بيانات البوت. فقط في المحادثات الخاصة.
- /markdownhelp: ملخص سريع لكيفية عمل الماركداون في تيليجرام - يمكن استدعاؤه فقط في المحادثات الخاصة.
- /stickerid: الرد على ملصق للحصول على معرف ذلك الملصق.
- /getsticker: الرد على ملصق للحصول على ذلك الملصق كصورة .png وصورة.

**الأوامر العربية (بدون شرطة):**
- `ايدي`: نفس /id.
- `معلومات`: نفس /info.
- `ركض`: نفس /runs.
- `صفع`: نفس /slap.
- `وقت`: نفس /time.
- `gdpr`: نفس /gdpr.
- `مارك داون`: نفس /markdownhelp.
- `ستكر`: نفس /stickerid.
- `صوره ستكر`: نفس /getsticker.
"""

__mod_name__ = "متنوع"


# =================== تسجيل المعالجات ===================
ID_HANDLER = DisableAbleCommandHandler("id", get_id)
IP_HANDLER = CommandHandler("ip", get_bot_ip, filters=filters.Chat(OWNER_ID))
TIME_HANDLER = CommandHandler("time", get_time)
RUNS_HANDLER = DisableAbleCommandHandler("runs", runs)
SLAP_HANDLER = DisableAbleCommandHandler("slap", slap)
INFO_HANDLER = DisableAbleCommandHandler("info", info)
ECHO_HANDLER = CommandHandler("echo", echo, filters=filters.User(OWNER_ID))
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help, filters=filters.ChatType.PRIVATE)
STATS_HANDLER = CommandHandler("stats", stats, filters=CustomFilters.sudo_filter)
GDPR_HANDLER = CommandHandler("gdpr", gdpr, filters=filters.ChatType.PRIVATE)
STICKERID_HANDLER = DisableAbleCommandHandler("stickerid", stickerid)
GETSTICKER_HANDLER = DisableAbleCommandHandler("getsticker", getsticker)

# المعالجات العربية
ID_ARABIC_HANDLER = DisableAbleCommandHandler("ايدي", id_arabic)
INFO_ARABIC_HANDLER = DisableAbleCommandHandler("معلومات", info_arabic)
RUNS_ARABIC_HANDLER = DisableAbleCommandHandler("ركض", runs_arabic)
SLAP_ARABIC_HANDLER = DisableAbleCommandHandler("صفع", slap_arabic)
TIME_ARABIC_HANDLER = DisableAbleCommandHandler("وقت", time_arabic)
GDPR_ARABIC_HANDLER = CommandHandler("gdpr", gdpr_arabic, filters=filters.ChatType.PRIVATE)
MD_ARABIC_HANDLER = CommandHandler("مارك داون", markdownhelp_arabic, filters=filters.ChatType.PRIVATE)
STICKERID_ARABIC_HANDLER = DisableAbleCommandHandler("ستكر", stickerid_arabic)
GETSTICKER_ARABIC_HANDLER = DisableAbleCommandHandler("صوره ستكر", getsticker_arabic)

# إضافة المعالجات إلى dispatcher
dispatcher.add_handler(ID_HANDLER)
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

dispatcher.add_handler(ID_ARABIC_HANDLER)
dispatcher.add_handler(INFO_ARABIC_HANDLER)
dispatcher.add_handler(RUNS_ARABIC_HANDLER)
dispatcher.add_handler(SLAP_ARABIC_HANDLER)
dispatcher.add_handler(TIME_ARABIC_HANDLER)
dispatcher.add_handler(GDPR_ARABIC_HANDLER)
dispatcher.add_handler(MD_ARABIC_HANDLER)
dispatcher.add_handler(STICKERID_ARABIC_HANDLER)
dispatcher.add_handler(GETSTICKER_ARABIC_HANDLER)
