from tg_bot.modules.sql import ranks_sql
from functools import wraps

# ... (باقي الدوال الموجودة)

# قائمة الرتب حسب القوة (للتحقق من التسلسل الهرمي)
RANK_ORDER = {
    "ownerplus": 6,
    "owner": 5,
    "creator": 4,
    "manager": 3,
    "admin": 2,
    "vip": 1,
    None: 0
}


def get_user_rank(chat_id, user_id):
    """إرجاع رتبة المستخدم، أو None إذا لم يكن لديه رتبة."""
    return ranks_sql.get_rank(chat_id, user_id)


def is_rank_at_least(chat_id, user_id, required_rank):
    """التحقق مما إذا كانت رتبة المستخدم تساوي أو أعلى من الرتبة المطلوبة."""
    user_rank = get_user_rank(chat_id, user_id)
    return RANK_ORDER.get(user_rank, 0) >= RANK_ORDER.get(required_rank, 0)


def is_ownerplus(chat_id, user_id):
    return get_user_rank(chat_id, user_id) == "ownerplus"


def is_owner(chat_id, user_id):
    return get_user_rank(chat_id, user_id) in ("ownerplus", "owner")


def is_creator(chat_id, user_id):
    return get_user_rank(chat_id, user_id) in ("ownerplus", "owner", "creator")


def is_manager(chat_id, user_id):
    return get_user_rank(chat_id, user_id) in ("ownerplus", "owner", "creator", "manager")


def is_admin_rank(chat_id, user_id):
    return get_user_rank(chat_id, user_id) in ("ownerplus", "owner", "creator", "manager", "admin")


def is_vip(chat_id, user_id):
    return get_user_rank(chat_id, user_id) is not None


def can_promote_to(chat_id, actor_id, target_id, new_rank):
    """التحقق مما إذا كان المستخدم (actor) يمكنه رفع المستخدم الآخر إلى رتبة معينة."""
    actor_rank = get_user_rank(chat_id, actor_id)
    target_rank = get_user_rank(chat_id, target_id)

    # المالك الأساسي يمكنه رفع أي شخص لأي رتبة
    if actor_rank == "ownerplus":
        return True

    # المالك يمكنه رفع إلى رتبة أقل منه (منشئ، مدير، إداري، مميز) ولا يمكنه رفع مالك أساسي
    if actor_rank == "owner":
        return new_rank in ("creator", "manager", "admin", "vip") and target_rank != "ownerplus"

    # المنشئ يمكنه رفع إلى رتبة أقل منه (مدير، إداري، مميز) ولا يمكنه رفع مالك أو مالك أساسي
    if actor_rank == "creator":
        return new_rank in ("manager", "admin", "vip") and target_rank not in ("ownerplus", "owner", "creator")

    # باقي الرتب لا يمكنها الرفع
    return False


def can_demote(chat_id, actor_id, target_id):
    """التحقق مما إذا كان المستخدم يمكنه تنزيل المستخدم الآخر."""
    actor_rank = get_user_rank(chat_id, actor_id)
    target_rank = get_user_rank(chat_id, target_id)

    # المالك الأساسي يمكنه تنزيل أي شخص
    if actor_rank == "ownerplus":
        return True

    # المالك يمكنه تنزيل من هم أقل منه (وليس مالك أساسي)
    if actor_rank == "owner":
        return target_rank not in ("ownerplus", "owner")

    # المنشئ يمكنه تنزيل من هم أقل منه (وليس مالك أو مالك أساسي)
    if actor_rank == "creator":
        return target_rank not in ("ownerplus", "owner", "creator")

    # باقي الرتب لا يمكنها التنزيل
    return False


def can_ban(chat_id, actor_id, target_id):
    """التحقق مما إذا كان المستخدم يمكنه حظر/طرد المستخدم الآخر."""
    actor_rank = get_user_rank(chat_id, actor_id)
    target_rank = get_user_rank(chat_id, target_id)

    # المالك الأساسي يمكنه حظر أي شخص
    if actor_rank == "ownerplus":
        return True

    # المالك يمكنه حظر من هم أقل منه (وليس مالك أساسي)
    if actor_rank == "owner":
        return target_rank not in ("ownerplus", "owner")

    # المنشئ يمكنه حظر الأعضاء بدون رتبة فقط
    if actor_rank == "creator":
        return target_rank is None

    # باقي الرتب لا يمكنها الحظر
    return False


def can_mute(chat_id, actor_id, target_id):
    """التحقق مما إذا كان المستخدم يمكنه كتم المستخدم الآخر."""
    # نفس منطق الحظر تقريباً
    return can_ban(chat_id, actor_id, target_id)


def can_use_tag(chat_id, user_id):
    """التحقق مما إذا كان المستخدم يمكنه استخدام أمر التاك (مثل @all) بناءً على إعدادات المجموعة."""
    from tg_bbort.modules.sql import tag_settings_sql
    setting = tag_settings_sql.get_setting(chat_id)
    # setting: 'all' (الكل مسموح), 'disabled' (مغلق), أو قائمة رتب مثل ['manager','admin']
    if setting == 'all':
        return True
    if setting == 'disabled':
        return False
    if isinstance(setting, list):
        user_rank = get_user_rank(chat_id, user_id)
        return user_rank in setting
    # افتراضياً: المدير فما فوق
    return is_manager(chat_id, user_id)
