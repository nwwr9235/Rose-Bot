import threading
from sqlalchemy import Column, String, Integer, UniqueConstraint
from tg_bot.modules.sql import BASE, SESSION


class Rank(BASE):
    __tablename__ = "ranks"
    chat_id = Column(String(14), primary_key=True)
    user_id = Column(Integer, primary_key=True)
    rank = Column(String(20))  # ownerplus, owner, creator, manager, admin, vip

    def __init__(self, chat_id, user_id, rank):
        self.chat_id = str(chat_id)
        self.user_id = user_id
        self.rank = rank


Rank.__table__.args = (UniqueConstraint('chat_id', 'user_id', name='_chat_user_uc'),)
BASE.metadata.create_all(bind=SESSION.get_bind())
LOCK = threading.RLock()


def get_rank(chat_id, user_id):
    with LOCK:
        try:
            rank_row = SESSION.query(Rank).get((str(chat_id), user_id))
            return rank_row.rank if rank_row else None
        finally:
            SESSION.close()


def set_rank(chat_id, user_id, rank):
    with LOCK:
        try:
            rank_row = SESSION.query(Rank).get((str(chat_id), user_id))
            if rank_row:
                rank_row.rank = rank
            else:
                rank_row = Rank(str(chat_id), user_id, rank)
                SESSION.add(rank_row)
            SESSION.commit()
        finally:
            SESSION.close()


def remove_rank(chat_id, user_id):
    with LOCK:
        try:
            rank_row = SESSION.query(Rank).get((str(chat_id), user_id))
            if rank_row:
                SESSION.delete(rank_row)
                SESSION.commit()
        finally:
            SESSION.close()


def get_all_ranks(chat_id):
    with LOCK:
        try:
            return {row.user_id: row.rank for row in SESSION.query(Rank).filter(Rank.chat_id == str(chat_id)).all()}
        finally:
            SESSION.close()
