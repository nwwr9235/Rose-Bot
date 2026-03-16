from tg_bot.modules.sql import ranks_sql
from tg_bot.modules.helper_funcs.chat_status import can_promote_to, can_demote, is_ownerplus, is_owner, is_creator

# ... (باقي الدوال)

# ================ أوامر الرفع والتنزيل العربية ================
@run_async
def arabic_promote(bot: Bot, update: Update):
    """معالج رفع: رفع @user رتبة"""
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    text = msg.text.strip()
    parts = text.split()
    if len(parts) < 3:
        msg.reply_text("استخدم: رفع @username الرتبة\nالرتب: مالك اساسي, مالك, منشئ, مدير, اداري, مميز")
        return

    username = parts[1]
    rank_ar = parts[2]
    # تحويل الرتبة العربية إلى إنجليزية
    rank_map = {
        'مالك اساسي': 'ownerplus',
        'مالك': 'owner',
        'منشئ': 'creator',
        'مدير': 'manager',
        'اداري': 'admin',
        'مميز': 'vip'
    }
    new_rank = rank_map.get(rank_ar)
    if not new_rank:
        msg.reply_text("رتبة غير معروفة. الرتب: مالك اساسي, مالك, منشئ, مدير, اداري, مميز")
        return

    # استخراج user_id من username
    target_user_id = extract_user(msg, [username])
    if not target_user_id:
        msg.reply_text("لم أتمكن من العثور على المستخدم.")
        return

    # التحقق من الصلاحية
    if not can_promote_to(chat.id, user.id, target_user_id, new_rank):
        msg.reply_text("ليس لديك صلاحية لرفع هذا المستخدم إلى هذه الرتبة.")
        return

    # تعيين الرتبة
    ranks_sql.set_rank(chat.id, target_user_id, new_rank)
    target_name = bot.get_chat(target_user_id).first_name
    msg.reply_text(f"تم رفع {target_name} إلى رتبة {rank_ar}.")


@run_async
def arabic_demote(bot: Bot, update: Update):
    """معالج تنزيل: تنزيل @user"""
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    text = msg.text.strip()
    parts = text.split()
    if len(parts) < 2:
        msg.reply_text("استخدم: تنزيل @username")
        return

    username = parts[1]
    target_user_id = extract_user(msg, [username])
    if not target_user_id:
        msg.reply_text("لم أتمكن من العثور على المستخدم.")
        return

    if not can_demote(chat.id, user.id, target_user_id):
        msg.reply_text("ليس لديك صلاحية لتنزيل هذا المستخدم.")
        return

    ranks_sql.remove_rank(chat.id, target_user_id)
    target_name = bot.get_chat(target_user_id).first_name
    msg.reply_text(f"تم تنزيل {target_name} (حذف الرتبة).")


@run_async
def arabic_show_rank(bot: Bot, update: Update):
    """عرض رتبة المستخدم: رتبتي أو رتبة @user"""
    msg = update.effective_message
    chat = update.effective_chat
    text = msg.text.strip()
    parts = text.split()
    if len(parts) >= 2 and parts[1].startswith('@'):
        username = parts[1]
        target_user_id = extract_user(msg, [username])
    else:
        target_user_id = msg.from_user.id

    if not target_user_id:
        msg.reply_text("لم أتمكن من العثور على المستخدم.")
        return

    rank = ranks_sql.get_rank(chat.id, target_user_id)
    target_name = bot.get_chat(target_user_id).first_name
    rank_map_rev = {
        'ownerplus': 'مالك اساسي',
        'owner': 'مالك',
        'creator': 'منشئ',
        'manager': 'مدير',
        'admin': 'اداري',
        'vip': 'مميز'
    }
    rank_ar = rank_map_rev.get(rank, 'بدون رتبة')
    msg.reply_text(f"رتبة {target_name}: {rank_ar}")

from telegram.ext import MessageHandler

# ... (بعد المعالجات الحالية)

# معالجات الأوامر العربية
ARABIC_PROMOTE_HANDLER = MessageHandler(
    Filters.regex(r'^\s*رفع\s+@\w+\s+(مالك اساسي|مالك|منشئ|مدير|اداري|مميز)\s*$'),
    arabic_promote,
    filters=Filters.group
)
ARABIC_DEMOTE_HANDLER = MessageHandler(
    Filters.regex(r'^\s*تنزيل\s+@\w+\s*$'),
    arabic_demote,
    filters=Filters.group
)
ARABIC_SHOW_RANK_HANDLER = MessageHandler(
    Filters.regex(r'^\s*(رتبتي|رتبة\s+@\w+)\s*$'),
    arabic_show_rank,
    filters=Filters.group
)

dispatcher.add_handler(ARABIC_PROMOTE_HANDLER)
dispatcher.add_handler(ARABIC_DEMOTE_HANDLER)
dispatcher.add_handler(ARABIC_SHOW_RANK_HANDLER)
