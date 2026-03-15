import threading
from sqlalchemy import Column, String
from tg_bot.modules.sql import BASE, SESSION


class Links(BASE):
    __tablename__ = "links"
    chat_id = Column(String(14), primary_key=True)
    link = Column(String(100))

    def __init__(self, chat_id, link):
        self.chat_id = str(chat_id)
        self.link = link


# الجدول سيتم إنشاؤه تلقائياً من __init__.py

# باقي الدوال (get_link, set_link, clear_link, ...) كما هي
