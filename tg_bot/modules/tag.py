import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, ParseMode
from telegram.ext import run_async, Filters, MessageHandler, CommandHandler
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher
from tg_bot.modules.helper_funcs.chat_status import can_use_tag, is_ownerplus
from tg_bot.modules.sql import tag_settings_sql as tag_sql
from tg_bot.modules.helper_funcs.extraction import extract_user


# ================ أمر التاك ================
@run_async
def tag_all(bot: Bot, update: Update):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    # التحقق من الصلاحية
    if not can_use_tag(chat.id, user.id):
        msg.reply_text("ليس لديك صلاحية استخدام هذا الأمر.")
        return

    # جلب جميع أعضاء المجموعة
    members = chat.get_administrators()

    if not members:
        msg.reply_text("لا يوجد أعضاء.")
        return

    mentions = " ".join([mention_html(m.user.id, m.user.first_name) for m in members])
    msg.reply_text(f"تنبيه للجميع:\n{mentions}", parse_mode=ParseMode.HTML)


# ================ التحكم في إعدادات التاك ================
@run_async
def tag_settings(bot: Bot, update: Update, args: List[str]):
    """تغيير إعدادات التاك (للمالك الأساسي فقط)"""
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not is_ownerplus(chat.id, user.id):
        msg.reply_text("هذا الأمر للمالك الأساسي فقط.")
        return

    if len(args) == 0:
        current = tag_sql.get_setting(chat.id)
        if current == 'all':
            text = "الكل مسموح لهم باستخدام التاك."
        elif current == 'disabled':
            text = "التاك معطل."
        elif isinstance(current, list):
            ranks = {'ownerplus': 'مالك أساسي', 'owner': 'مالك', 'creator': 'منشئ', 'manager': 'مدير', 'admin': 'إداري', 'vip': 'مميز'}
            allowed = ', '.join([ranks.get(r, r) for r in current])
            text = f"التاك مسموح للرتب: {allowed}."
        else:
            text = "إعدادات غير معروفة."
        msg.reply_text(text)
        return

    setting = args[0].lower()
    if setting == 'all':
        tag_sql.set_setting(chat.id, 'all')
        msg.reply_text("تم فتح التاك للجميع.")
    elif setting == 'off':
        tag_sql.set_setting(chat.id, 'disabled')
        msg.reply_text("تم قفل التاك.")
    elif setting.startswith('ranks:'):
        ranks_part = setting.split(':')[1]
        rank_list = [r.strip() for r in ranks_part.split(',') if r.strip() in ('ownerplus', 'owner', 'creator', 'manager', 'admin', 'vip')]
        if rank_list:
            tag_sql.set_setting(chat.id, rank_list)
            msg.reply_text(f"تم تعيين الرتب المسموح لها: {', '.join(rank_list)}.")
        else:
            msg.reply_text("الرجاء إدخال رتب صحيحة: ownerplus, owner, creator, manager, admin, vip")
    else:
        msg.reply_text("الأمر غير معروف. استخدم: /tagsettings all | off | ranks:owner,creator")


# ================ أوامر عربية ================
@run_async
def arabic_tag_all(bot: Bot, update: Update):
    """معالج للأمر العربي 'تاك'"""
    tag_all(bot, update)


@run_async
def arabic_tag_settings(bot: Bot, update: Update):
    """معالج للأمر العربي 'تاك_اعدادات' (يحتاج إلى معاملات)"""
    msg = update.effective_message
    text = msg.text.strip()
    args = text.split()[1:] if len(text.split()) > 1 else []
    
    if not args:
        # عرض الإعدادات الحالية
        tag_settings(bot, update, [])
        return

    cmd = args[0]
    if cmd == 'فتح':
        tag_settings(bot, update, ['all'])
    elif cmd == 'قفل':
        tag_settings(bot, update, ['off'])
    elif cmd.startswith('رتب:'):
        # تحويل الرتب العربية إلى إنجليزية
        rank_map = {'مالك اساسي': 'ownerplus', 'مالك': 'owner', 'منشئ': 'creator', 'مدير': 'manager', 'اداري': 'admin', 'مميز': 'vip'}
        ranks_ar = cmd[4:].split(',')
        ranks_en = []
        for r_ar in ranks_ar:
            r_ar = r_ar.strip()
            if r_ar in rank_map:
                ranks_en.append(rank_map[r_ar])
        if ranks_en:
            tag_settings(bot, update, ['ranks:' + ','.join(ranks_en)])
        else:
            msg.reply_text("الرجاء إدخال رتب صحيحة: مالك اساسي, مالك, منشئ, مدير, اداري, مميز")
    else:
        msg.reply_text("الأمر غير معروف. استخدم: تاك_اعدادات فتح | قفل | رتب:رتبة1,رتبة2")


# ================ تسجيل المعالجات ================
TAG_HANDLER = CommandHandler("tag", tag_all, filters=Filters.group)
TAG_SETTINGS_HANDLER = CommandHandler("tagsettings", tag_settings, pass_args=True, filters=Filters.group)

# تم دمج فلتر regex مع فلتر المجموعة باستخدام &
ARABIC_TAG_HANDLER = MessageHandler(
    Filters.regex(r'^\s*تاك\s*$') & Filters.group,
    arabic_tag_all
)
ARABIC_TAG_SETTINGS_HANDLER = MessageHandler(
    Filters.regex(r'^\s*تاك_اعدادات(\s+.*)?$') & Filters.group,
    arabic_tag_settings
)

dispatcher.add_handler(TAG_HANDLER)
dispatcher.add_handler(TAG_SETTINGS_HANDLER)
dispatcher.add_handler(ARABIC_TAG_HANDLER)
dispatcher.add_handler(ARABIC_TAG_SETTINGS_HANDLER)

__mod_name__ = "Tag"
__help__ = """
- /tag: منشن جميع الأعضاء (حسب الصلاحية)
- /tagsettings: عرض/تغيير إعدادات التاك (للمالك الأساسي)

الأوامر العربية:
- تاك: نفس /tag
- تاك_اعدادات: عرض الإعدادات
- تاك_اعدادات فتح: فتح التاك للجميع
- تاك_اعدادات قفل: قفل التاك
- تاك_اعدادات رتب:رتبة1,رتبة2: تحديد الرتب المسموح لها (مثلاً: تاك_اعدادات رتب:مدير,منشئ)
"""
