import threading
from typing import Dict, List, Any, Optional
from sqlalchemy import Column, String, Integer, Boolean, LargeBinary, Text, BigInteger, and_, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import PickleType

from tg_bot.modules.sql import BASE, SESSION


class Notes(BASE):
    __tablename__ = "notes"
    chat_id = Column(String(14), primary_key=True)
    name = Column(String(150), primary_key=True)
    # تخزين قائمة الردود كـ PickleType (للبساطة)
    replies = Column(PickleType, default=list)  # قائمة من القواميس، كل قاموس يمثل رداً

    def __init__(self, chat_id, name, replies=None):
        self.chat_id = str(chat_id)
        self.name = name
        self.replies = replies or []

    def __repr__(self):
        return f"<Note {self.name} in {self.chat_id} ({len(self.replies)} replies)>"


Notes.__table__.create(checkfirst=True)

INSERTION_LOCK = threading.RLock()


# =================== دوال التعامل مع الردود المتعددة ===================

def add_note_replies(chat_id: int, note_name: str, replies: List[Dict[str, Any]]):
    """إضافة أو تحديث ملاحظة بقائمة ردود."""
    with INSERTION_LOCK:
        prev = SESSION.query(Notes).get((str(chat_id), note_name))
        if prev:
            prev.replies = replies
            SESSION.add(prev)
        else:
            new_note = Notes(chat_id, note_name, replies)
            SESSION.add(new_note)
        SESSION.commit()


def get_note(chat_id: int, note_name: str) -> Optional[Dict[str, Any]]:
    """الحصول على بيانات ملاحظة (قائمة الردود)."""
    try:
        note = SESSION.query(Notes).get((str(chat_id), note_name))
        if note:
            return {"name": note.name, "replies": note.replies}
        return None
    finally:
        SESSION.close()


def rm_note(chat_id: int, note_name: str) -> bool:
    """حذف ملاحظة."""
    with INSERTION_LOCK:
        note = SESSION.query(Notes).get((str(chat_id), note_name))
        if note:
            SESSION.delete(note)
            SESSION.commit()
            return True
        return False


def get_all_chat_notes(chat_id: int) -> List[Dict[str, Any]]:
    """الحصول على قائمة بجميع الملاحظات في محادثة معينة."""
    try:
        return [{"name": x.name, "replies": x.replies} for x in
                SESSION.query(Notes).filter(Notes.chat_id == str(chat_id)).all()]
    finally:
        SESSION.close()


def num_notes() -> int:
    """إجمالي عدد الملاحظات في جميع المحادثات."""
    try:
        return SESSION.query(Notes).count()
    finally:
        SESSION.close()


def num_chats() -> int:
    """عدد المحادثات التي تحتوي على ملاحظات."""
    try:
        return SESSION.query(Notes.chat_id).distinct().count()
    finally:
        SESSION.close()


def migrate_chat(old_chat_id: int, new_chat_id: int):
    """ترحيل بيانات مجموعة عند الترقية إلى supergroup."""
    with INSERTION_LOCK:
        notes = SESSION.query(Notes).filter(Notes.chat_id == str(old_chat_id)).all()
        for note in notes:
            note.chat_id = str(new_chat_id)
            SESSION.add(note)
        SESSION.commit()


# =================== دوال التوافق مع الإصدارات القديمة (اختياري) ===================

def add_note_to_db(chat_id: int, note_name: str, reply_text: str, msgtype: int, buttons=None, file=None) -> None:
    """
    دالة توافقية للإصدار القديم.
    تُستخدم بواسطة أمر /save لإنشاء ملاحظة برد واحد.
    """
    reply_data = {
        "msgtype": msgtype,
        "text": reply_text,
        "file": file,
        "buttons": buttons or [],
        "has_markdown": True,
    }
    add_note_replies(chat_id, note_name, [reply_data])


def get_buttons(chat_id: int, note_name: str) -> List:
    """دالة توافقية (قديمة) - تستخرج الأزرار من أول رد."""
    note = get_note(chat_id, note_name)
    if note and note["replies"]:
        return note["replies"][0].get("buttons", [])
    return []_HANDLER)
