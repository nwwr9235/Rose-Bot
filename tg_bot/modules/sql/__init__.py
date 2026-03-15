import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

# الحصول على رابط قاعدة البيانات من متغير البيئة
DB_URI = os.environ.get("DATABASE_URL")

if not DB_URI:
    # محاولة قراءة من config.py إذا كان متاحاً (للتشغيل المحلي)
    try:
        from tg_bot.config import Development as Config
        DB_URI = Config.SQLALCHEMY_DATABASE_URI
    except ImportError:
        DB_URI = "sqlite:///tg_bot.db"  # قيمة افتراضية للتجربة المحلية
        print("Warning: Using default sqlite database. Set DATABASE_URL environment variable for production.")

def start() -> scoped_session:
    engine = create_engine(DB_URI, client_encoding="utf8")
    BASE.metadata.bind = engine
    BASE.metadata.create_all(engine)
    return scoped_session(sessionmaker(bind=engine, autoflush=False))

BASE = declarative_base()
SESSION = start()
