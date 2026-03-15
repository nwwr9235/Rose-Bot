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
        DB_URI = "sqlite:///tg_bot.db"
        print("Warning: Using default sqlite database. Set DATABASE_URL environment variable for production.")

# إنشاء المحرك والجلسة
engine = create_engine(DB_URI, client_encoding="utf8")
BASE = declarative_base()
SESSION = scoped_session(sessionmaker(bind=engine, autoflush=False))

# استيراد جميع النماذج (models) لضمان تسجيلها في BASE.metadata
# هذا يتطلب استيراد جميع ملفات sql التي تحتوي على تعريفات الجداول
from tg_bot.modules.sql import (
    afk_sql,
    antiflood_sql,
    blacklist_sql,
    connection_sql,
    cust_filters_sql,
    disable_sql,
    global_bans_sql,
    locks_sql,
    log_channel_sql,
    notes_sql,
    reporting_sql,
    rss_sql,
    rules_sql,
    setlink_sql,
    userinfo_sql,
    users_sql,
    warns_sql,
    welcome_sql,
)

# إنشاء جميع الجداول
BASE.metadata.create_all(bind=engine)
