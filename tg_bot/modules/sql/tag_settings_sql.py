import threading
from sqlalchemy import Column, String, Integer, PickleType
from tg_bot.modules.sql import BASE, SESSION


class TagSetting(BASE):
    __tablename__ = "tag_settings"
    chat_id = Column(String(14), primary_key=True)
    # يمكن أن يكون 'all', 'disabled', أو قائمة رتب (مثل ['owner','creator','manager'])
    setting = Column(PickleType, default=['manager', 'creator', 'owner', 'ownerplus'])

    def __init__(self, chat_id):
        self.chat_id = str(chat_id)


TagSetting.__table__.args = ()
BASE.metadata.create_all(bind=SESSION.get_bind())
LOCK = threading.RLock()


def get_setting(chat_id):
    with LOCK:
        try:
            setting = SESSION.query(TagSetting).get(str(chat_id))
            return setting.setting if setting else ['manager', 'creator', 'owner', 'ownerplus']  # افتراضي
        finally:
            SESSION.close()


def set_setting(chat_id, setting):
    with LOCK:
        try:
            setting_row = SESSION.query(TagSetting).get(str(chat_id))
            if not setting_row:
                setting_row = TagSetting(chat_id)
            setting_row.setting = setting
            SESSION.add(setting_row)
            SESSION.commit()
        finally:
            SESSION.close()
