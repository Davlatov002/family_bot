import os
import asyncio
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from asgiref.sync import sync_to_async
from dotenv import load_dotenv
from birthdays.models import Birthday

# ==========================================
# ENV
# ==========================================

load_dotenv()
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
GREETING_TIME = os.getenv("GREETING_TIME", "09:00")
REMINDER_TIME = os.getenv("REMINDER_TIME", "20:00")
TASHKENT_TZ = ZoneInfo("Asia/Tashkent")

# ==========================================
# TODAY BIRTHDAYS
# ==========================================

@sync_to_async
def get_today_birthdays_for_greeting():

    today = datetime.now(TASHKENT_TZ).date()
    birthdays = Birthday.objects.filter(is_active=True, birth_date__month=today.month, birth_date__day=today.day,)
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

@sync_to_async
def get_tomorrow_birthdays():
    today = datetime.now(TASHKENT_TZ).date()
    tomorrow = today + timedelta(days=1)
    birthdays = Birthday.objects.filter(is_active=True, birth_date__month=tomorrow.month, birth_date__day=tomorrow.day,)
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

@sync_to_async
def mark_greeting_sent(birthday_id):
    today = datetime.now(TASHKENT_TZ).date()
    birthday = Birthday.objects.get(id=birthday_id)
    birthday.last_greeting_year = (today.year)
    birthday.save(update_fields=["last_greeting_year"])


# ==========================================
# MARK REMINDER
# ==========================================

@sync_to_async
def mark_reminder_sent(birthday_id):
    today = datetime.now(TASHKENT_TZ).date()
    tomorrow = today + timedelta(days=1)
    birthday = Birthday.objects.get(id=birthday_id)
    birthday.last_reminder_year = (tomorrow.year)
    birthday.save(update_fields=["last_reminder_year"])

# ==========================================
# SEND TODAY GREETINGS
# ==========================================

async def send_today_greetings(bot):
    if not GROUP_CHAT_ID:
        print("⚠️ GROUP_CHAT_ID kiritilmagan.")
        return
    try:
        chat_id = int(GROUP_CHAT_ID)
    except ValueError:
        print("❌ GROUP_CHAT_ID noto‘g‘ri.")
        return
    birthdays = (await get_today_birthdays_for_greeting())
    if not birthdays:
        print("🎂 Bugun tug‘ilgan kun yo‘q.")
        return
    for birthday in birthdays:
        text = (
            "🎉🎂 <b>TUG‘ILGAN KUN!</b> 🎂🎉\n\n"
            f"🥳 Bugun "
            f"<b>{birthday['full_name']}</b>"
            "ning tug‘ilgan kuni!\n\n"
            f"👨‍👩‍👦 "
            f"{birthday['relation']}\n\n"
            "💐 Tug‘ilgan kuningiz muborak "
            "bo‘lsin!\n"
            "🎁 Uzoq umr, sog‘lik, baxt va "
            "oilaviy xotirjamlik tilaymiz! ❤️"
        )
        try:
            if (birthday["photo"] and os.path.exists(birthday["photo"])):
                from aiogram.types import FSInputFile
                photo = FSInputFile(birthday["photo"])
                await bot.send_photo(chat_id=chat_id, photo=photo, caption=text, parse_mode="HTML",)
            else:
                await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML",)
            await mark_greeting_sent(birthday["id"])
            print("✅ Tabrik yuborildi: " f"{birthday['full_name']}")
        except Exception as e:
            print("❌ Tabrik yuborishda xato: " f"{e}")

# ==========================================
# SEND TOMORROW REMINDERS
# ==========================================

async def send_tomorrow_reminders(bot):
    if not GROUP_CHAT_ID:
        print("⚠️ GROUP_CHAT_ID kiritilmagan.")
        return
    try:
        chat_id = int(GROUP_CHAT_ID)
    except ValueError:
        print("❌ GROUP_CHAT_ID noto‘g‘ri.")
        return
    birthdays = (await get_tomorrow_birthdays())
    if not birthdays:
        print("🔔 Ertaga tug‘ilgan kun yo‘q.")
        return
    for birthday in birthdays:
        text = (
            "🔔 <b>ERTAGA TUG‘ILGAN KUN!</b>\n\n"
            f"🎂 Ertaga "
            f"<b>{birthday['full_name']}</b>"
            "ning tug‘ilgan kuni!\n\n"
            f"👨‍👩‍👦 "
            f"{birthday['relation']}\n\n"
            "🎁 Tabriklashni unutmang! ❤️"
        )
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML",)
            await mark_reminder_sent(birthday["id"])
            print("🔔 Eslatma yuborildi: " f"{birthday['full_name']}")
        except Exception as e:
            print("❌ Eslatma yuborishda xato: " f"{e}")


# ==========================================
# CHECK TIME
# ==========================================

def is_time(current_time, target_time):
    return (current_time.hour == target_time.hour and current_time.minute == target_time.minute)

# ==========================================
# PARSE TIME
# ==========================================

def parse_time(value,  default):
    try:
        hour, minute = map(int, value.split(":"))
        return hour, minute
    except Exception:
        print(f"⚠️ Vaqt noto‘g‘ri: {value}")
        print(f"ℹ️ Default vaqt ishlatiladi: " f"{default}")
        return parse_time(default, default)

# ==========================================
# MAIN SCHEDULER
# ==========================================

async def birthday_notification_loop(bot):
    greeting_hour, greeting_minute = (parse_time(GREETING_TIME,"09:00"))
    reminder_hour, reminder_minute = (parse_time( REMINDER_TIME,"20:00"))
    print("🎂 Birthday scheduler ishlayapti...")
    print(f"🎉 Tabrik vaqti: " f"{greeting_hour:02d}:{greeting_minute:02d}")
    print(f"🔔 Eslatma vaqti: " f"{reminder_hour:02d}:{reminder_minute:02d}")
    print("🇺🇿 Timezone: Asia/Tashkent")
    last_greeting_date = None
    last_reminder_date = None
    while True:
        try:
            now = datetime.now(TASHKENT_TZ)
            today = now.date()
            current_hour = now.hour
            current_minute = now.minute

            # ==================================
            # TODAY GREETING
            # ==================================

            if (current_hour == greeting_hour and current_minute == greeting_minute and last_greeting_date != today):
                print(f"🎉 {now.strftime('%d.%m.%Y %H:%M')} — bugungi tabriklar yuborilmoqda...")
                await send_today_greetings(bot)
                last_greeting_date = today

            # ==================================
            # TOMORROW REMINDER
            # ==================================

            if (current_hour == reminder_hour and current_minute == reminder_minute and last_reminder_date != today):
                print(f"🔔 {now.strftime('%d.%m.%Y %H:%M')} — ertangi eslatmalar yuborilmoqda...")
                await send_tomorrow_reminders(bot)
                last_reminder_date = today
        except Exception as e:
            print("❌ Scheduler xatosi:", e)
        await asyncio.sleep(20)