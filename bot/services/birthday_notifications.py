import os
import asyncio
import calendar
import logging
from datetime import datetime, date, timedelta
from html import escape
from zoneinfo import ZoneInfo
from aiogram.types import FSInputFile
from django.db.models import Q
from bot.services.db import db_task
from birthdays.models import Birthday

logger = logging.getLogger(__name__)

# ==========================================
# ENV
# ==========================================

GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
GREETING_TIME = os.getenv("GREETING_TIME", "09:00")
REMINDER_TIME = os.getenv("REMINDER_TIME", "20:00")
TASHKENT_TZ = ZoneInfo("Asia/Tashkent")

# ==========================================
# DATE HELPERS
# ==========================================

def birthday_on(day):
    """
    Shu kunga to‘g‘ri keladigan tug‘ilgan kunlar filtri.
    Kabisa bo‘lmagan yilda 29-fevral tug‘ilganlar 28-fevralda nishonlanadi.
    """
    q = Q(birth_date__month=day.month, birth_date__day=day.day)
    if day.month == 2 and day.day == 28 and not calendar.isleap(day.year):
        q |= Q(birth_date__month=2, birth_date__day=29)
    return q


def birthday_in_year(birth_date, year):
    try:
        return birth_date.replace(year=year)
    except ValueError:
        # 29-fevral, kabisa bo‘lmagan yil
        return date(year, 2, 28)


def next_birthday(birth_date, today):
    this_year = birthday_in_year(birth_date, today.year)
    if this_year < today:
        return birthday_in_year(birth_date, today.year + 1)
    return this_year

# ==========================================
# TODAY BIRTHDAYS
# ==========================================

@db_task
def get_today_birthdays_for_greeting():

    today = datetime.now(TASHKENT_TZ).date()
    birthdays = Birthday.objects.filter(birthday_on(today), is_active=True,)
    result = []
    for birthday in birthdays:
        if birthday.last_greeting_year == today.year:
            continue
        result.append(
            {
                "id": birthday.id,
                "full_name": birthday.full_name,
                "relation": birthday.relation,
                "photo": (
                    birthday.photo.path
                    if birthday.photo
                    else None
                ),
            }
        )
    return result

# ==========================================
# TOMORROW BIRTHDAYS
# ==========================================

@db_task
def get_tomorrow_birthdays():
    today = datetime.now(TASHKENT_TZ).date()
    tomorrow = today + timedelta(days=1)
    birthdays = Birthday.objects.filter(birthday_on(tomorrow), is_active=True,)
    result = []
    for birthday in birthdays:
        if birthday.last_reminder_year == tomorrow.year:
            continue
        result.append(
            {
                "id": birthday.id,
                "full_name": birthday.full_name,
                "relation": birthday.relation,
            }
        )
    return result


# ==========================================
# MARK GREETING
# ==========================================

@db_task
def mark_greeting_sent(birthday_id):
    today = datetime.now(TASHKENT_TZ).date()
    Birthday.objects.filter(id=birthday_id).update(last_greeting_year=today.year)


# ==========================================
# MARK REMINDER
# ==========================================

@db_task
def mark_reminder_sent(birthday_id):
    today = datetime.now(TASHKENT_TZ).date()
    tomorrow = today + timedelta(days=1)
    Birthday.objects.filter(id=birthday_id).update(last_reminder_year=tomorrow.year)

# ==========================================
# GROUP CHAT ID
# ==========================================

def get_group_chat_id():
    if not GROUP_CHAT_ID:
        logger.warning("⚠️ GROUP_CHAT_ID kiritilmagan.")
        return None
    try:
        return int(GROUP_CHAT_ID)
    except ValueError:
        logger.error("❌ GROUP_CHAT_ID noto‘g‘ri.")
        return None

# ==========================================
# SEND TODAY GREETINGS
# ==========================================

async def send_today_greetings(bot):
    chat_id = get_group_chat_id()
    if chat_id is None:
        return
    birthdays = (await get_today_birthdays_for_greeting())
    if not birthdays:
        logger.info("🎂 Bugun tug‘ilgan kun yo‘q.")
        return
    for birthday in birthdays:
        text = (
            "🎉🎂 <b>TUG‘ILGAN KUN!</b> 🎂🎉\n\n"
            f"🥳 Bugun "
            f"<b>{escape(birthday['full_name'])}</b>"
            "ning tug‘ilgan kuni!\n\n"
        )
        if birthday["relation"]:
            text += f"👨‍👩‍👦 {escape(birthday['relation'])}\n\n"
        text += (
            "💐 Tug‘ilgan kuningiz muborak "
            "bo‘lsin!\n"
            "🎁 Uzoq umr, sog‘lik, baxt va "
            "oilaviy xotirjamlik tilaymiz! ❤️"
        )
        try:
            if (birthday["photo"] and os.path.exists(birthday["photo"])):
                photo = FSInputFile(birthday["photo"])
                await bot.send_photo(chat_id=chat_id, photo=photo, caption=text, parse_mode="HTML",)
            else:
                await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML",)
            await mark_greeting_sent(birthday["id"])
            logger.info("✅ Tabrik yuborildi: %s", birthday["full_name"])
        except Exception:
            logger.exception("❌ Tabrik yuborishda xato: %s", birthday["full_name"])

# ==========================================
# SEND TOMORROW REMINDERS
# ==========================================

async def send_tomorrow_reminders(bot):
    chat_id = get_group_chat_id()
    if chat_id is None:
        return
    birthdays = (await get_tomorrow_birthdays())
    if not birthdays:
        logger.info("🔔 Ertaga tug‘ilgan kun yo‘q.")
        return
    for birthday in birthdays:
        text = (
            "🔔 <b>ERTAGA TUG‘ILGAN KUN!</b>\n\n"
            f"🎂 Ertaga "
            f"<b>{escape(birthday['full_name'])}</b>"
            "ning tug‘ilgan kuni!\n\n"
        )
        if birthday["relation"]:
            text += f"👨‍👩‍👦 {escape(birthday['relation'])}\n\n"
        text += "🎁 Tabriklashni unutmang! ❤️"
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML",)
            await mark_reminder_sent(birthday["id"])
            logger.info("🔔 Eslatma yuborildi: %s", birthday["full_name"])
        except Exception:
            logger.exception("❌ Eslatma yuborishda xato: %s", birthday["full_name"])

# ==========================================
# PARSE TIME
# ==========================================

def parse_time(value, default):
    try:
        hour, minute = map(int, value.strip().split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        return hour, minute
    except Exception:
        logger.warning("⚠️ Vaqt noto‘g‘ri: %s. Default vaqt ishlatiladi: %s", value, default)
        return parse_time(default, default)

# ==========================================
# MAIN SCHEDULER
# ==========================================

async def birthday_notification_loop(bot):
    greeting_hour, greeting_minute = (parse_time(GREETING_TIME,"09:00"))
    reminder_hour, reminder_minute = (parse_time( REMINDER_TIME,"20:00"))
    logger.info("🎂 Birthday scheduler ishlayapti...")
    logger.info("🎉 Tabrik vaqti: %02d:%02d", greeting_hour, greeting_minute)
    logger.info("🔔 Eslatma vaqti: %02d:%02d", reminder_hour, reminder_minute)
    logger.info("🇺🇿 Timezone: Asia/Tashkent")
    last_greeting_date = None
    last_reminder_date = None
    while True:
        try:
            now = datetime.now(TASHKENT_TZ)
            today = now.date()
            current = (now.hour, now.minute)

            # ==================================
            # TODAY GREETING
            # ==================================
            # Belgilangan vaqtdan keyin (masalan, bot qayta ishga tushsa ham)
            # yuboriladi. Takrorlanish bazadagi last_greeting_year bilan oldi olinadi.

            if (current >= (greeting_hour, greeting_minute) and last_greeting_date != today):
                logger.info("🎉 %s — bugungi tabriklar yuborilmoqda...", now.strftime('%d.%m.%Y %H:%M'))
                await send_today_greetings(bot)
                last_greeting_date = today

            # ==================================
            # TOMORROW REMINDER
            # ==================================

            if (current >= (reminder_hour, reminder_minute) and last_reminder_date != today):
                logger.info("🔔 %s — ertangi eslatmalar yuborilmoqda...", now.strftime('%d.%m.%Y %H:%M'))
                await send_tomorrow_reminders(bot)
                last_reminder_date = today
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("❌ Scheduler xatosi")
        await asyncio.sleep(20)
