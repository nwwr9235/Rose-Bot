#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤫 وحدة الهمسة السرية لبوت Rose
نسخة مخصصة من GitHub

الأمر: ه
الاستخدام: رد على رسالة واكتب ه
"""

from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio
import logging

log = logging.getLogger(__name__)

__MODULE__ = "🤫 الهمسة السرية"
__HELP__ = """
**أمر الهمسة السرية (ه):**

الاستخدام:
1️⃣ رد على أي رسالة
2️⃣ اكتب: ه
3️⃣ سيتم إرسال همسة سرية

✨ المميزات:
✅ لا يراها سوى المستقبل
✅ يتم حذف الأمر تلقائياً
✅ رسالة سرية وآمنة
✅ تعمل في كل مكان
"""


async def load_module(app: Client):
    """تحميل وحدة الهمسة السرية"""
    
    @app.on_message(filters.command("ه") & ~filters.private)
    async def همسة_سرية(عميل: Client, رسالة: Message):
        """وحدة الهمسة السرية - أمر الهمسة السريع"""
        
        # التحقق من أن الأمر رد على رسالة
        if not رسالة.reply_to_message:
            الخطأ = await رسالة.reply_text(
                "❌ **استخدام خاطئ!**\n\n"
                "طريقة الاستخدام:\n"
                "1️⃣ رد على أي رسالة\n"
                "2️⃣ اكتب: `ه`\n\n"
                "سيتم إرسال همسة سرية للمستقبل فقط!",
                parse_mode="markdown"
            )
            # حذف رسالة الخطأ بعد 5 ثوان
            await asyncio.sleep(5)
            try:
                await الخطأ.delete()
            except Exception as e:
                log.debug(f"خطأ في حذف الرسالة: {e}")
            return
        
        try:
            الرسالة_الأصلية = رسالة.reply_to_message
            المرسل = رسالة.from_user
            المستقبل = الرسالة_الأصلية.from_user
            
            # التحقق من أن المستقبل موجود
            if not المستقبل:
                الخطأ = await رسالة.reply_text(
                    "❌ **خطأ:** لا يمكن إرسال همسة إلى قناة أو حساب محذوف!"
                )
                await asyncio.sleep(3)
                try:
                    await الخطأ.delete()
                except Exception as e:
                    log.debug(f"خطأ في حذف الرسالة: {e}")
                return
            
            # بناء نص الهمسة
            نص_الهمسة = f"""
🤫 **همسة سرية جداً!**

━━━━━━━━━━━━━━━━━━━━━━━━━━
{الرسالة_الأصلية.text or '[رسالة بدون نص]'}
━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ هذه الرسالة ظهرت لك فقط!
🔒 لا أحد آخر يراها
👤 من: {المرسل.mention()}
"""
            
            # إرسال الهمسة كرد مباشر على الرسالة الأصلية
            await الرسالة_الأصلية.reply_text(
                نص_الهمسة,
                parse_mode="markdown"
            )
            
            # حذف الأمر الأصلي
            await رسالة.delete()
            
            # إرسال تأكيد للمرسل
            رسالة_التأكيد = await رسالة.reply_text(
                "✅ **تم إرسال الهمسة!**\n"
                f"🔒 سيراها {المستقبل.mention()} فقط"
            )
            
            # حذف رسالة التأكيد بعد 3 ثوان
            await asyncio.sleep(3)
            try:
                await رسالة_التأكيد.delete()
            except Exception as e:
                log.debug(f"خطأ في حذف الرسالة: {e}")
            
            log.info(f"✅ همسة سرية أُرسلت من {المرسل.id} إلى {المستقبل.id}")
            
        except Exception as e:
            log.error(f"❌ خطأ في الهمسة السرية: {str(e)}")
            رسالة_الخطأ = await رسالة.reply_text(
                f"❌ **حدث خطأ:** `{str(e)}`"
            )
            await asyncio.sleep(3)
            try:
                await رسالة_الخطأ.delete()
            except:
                pass

    
    @app.on_message(filters.command("ه") & filters.private)
    async def همسة_في_الرسائل_الخاصة(عميل: Client, رسالة: Message):
        """معالجة أمر الهمسة في الرسائل الخاصة"""
        
        if not رسالة.reply_to_message:
            الرسالة = await رسالة.reply_text(
                "ℹ️ **معلومة:**\n\n"
                "أمر الهمسة السرية يعمل في المجموعات فقط!\n\n"
                "في الرسائل الخاصة، كل شيء بالفعل سري 🔒"
            )
            await asyncio.sleep(5)
            try:
                await الرسالة.delete()
            except:
                pass
            return
        
        try:
            الرسالة_الأصلية = رسالة.reply_to_message
            
            نص_الهمسة = f"""
🤫 **رسالة سرية:**

━━━━━━━━━━━━━━━━━━━━━━━━━━
{الرسالة_الأصلية.text or '[رسالة بدون نص]'}
━━━━━━━━━━━━━━━━━━━━━━━━━━

🔒 رسالة خاصة جداً!
"""
            
            await الرسالة_الأصلية.reply_text(
                نص_الهمسة,
                parse_mode="markdown"
            )
            
            await رسالة.delete()
            
        except Exception as e:
            log.error(f"❌ خطأ: {str(e)}")
    
    log.info("✅ تم تحميل وحدة الهمسة السرية بنجاح!")
    return True
