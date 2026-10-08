import os
import sys
import asyncio
import logging
from datetime import datetime
from io import BytesIO
from html import escape
from dotenv import load_dotenv

# ==================================================
# ENV
# ==================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env",))

# ==================================================
# DJANGO
# ==================================================

BACKEND_DIR = os.path.join(BASE_DIR, "backend",)

if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

import django
django.setup()


# ==================================================
# IMPORTS
# ==================================================

from bot.services.db import db_task
from django.core.files.base import ContentFile
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import (State, StatesGroup,)
from birthdays.models import Birthday
from users.models import FamilyUser
from bot.services.users import get_or_create_user
from bot.services.birthday_notifications import (birthday_notification_loop, TASHKENT_TZ, birthday_on, next_birthday,)
from bot.keyboards.main import (user_menu, admin_menu, super_admin_menu, group_menu,)
from bot.keyboards.admin import (super_admin_panel, admin_panel, confirm_add_admin, birthday_admin_panel, cancel_birthday, confirm_delete_birthday, relation_keyboard,)

# ==================================================
# SETTINGS
# ==================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN .env faylida topilmadi.")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("family_bot")

try:
    SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))
except ValueError:
    raise RuntimeError("SUPER_ADMIN_ID .env faylida raqam bo‘lishi kerak.")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

# @username bo'lsa ham ishlaydi
BOT_USERNAME = (os.getenv("BOT_USERNAME") or "").lstrip("@").strip()

# ==================================================
# BOT
# ==================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==================================================
# STATES
# ==================================================

class AddAdminState(StatesGroup):
    waiting_telegram_id = State()

class AddBirthdayState(StatesGroup):
    waiting_full_name = State()
    waiting_birth_date = State()
    waiting_relation = State()
    waiting_photo = State()


# ==================================================
# PERMISSION
# ==================================================

@db_task
def get_user_role(telegram_id):
    user = FamilyUser.objects.filter(telegram_id=telegram_id, is_active=True,).first()
    if not user:
        return None
    return user.role

async def is_admin_or_super_admin(telegram_id,):
    role = await get_user_role(telegram_id)
    return role in (
        "ADMIN",
        "SUPER_ADMIN",
    )

async def is_super_admin(telegram_id,):
    role = await get_user_role(telegram_id)
    return role == "SUPER_ADMIN"

# ==================================================
# USER DATABASE
# ==================================================

@db_task
def find_user_by_telegram_id(telegram_id,):
    user = FamilyUser.objects.filter(telegram_id=telegram_id, is_active=True,).first()
    if not user:
        return None
    return {
        "id": user.id,
        "full_name": user.full_name,
        "telegram_id": user.telegram_id,
        "role": user.role,
    }

@db_task
def set_user_admin(user_id,):
    user = FamilyUser.objects.filter(id=user_id, is_active=True,).first()
    if not user:
        return None
    if user.role == "SUPER_ADMIN":
        return None
    user.role = "ADMIN"
    user.save(update_fields=["role"])
    return {"full_name": user.full_name, "telegram_id": user.telegram_id,}

@db_task
def remove_admin_by_id(user_id,):
    user = FamilyUser.objects.filter(id=user_id, is_active=True, role="ADMIN",).first()
    if not user:
        return None
    user.role = "USER"
    user.save(update_fields=["role"])
    return {"full_name": user.full_name, "telegram_id": user.telegram_id,}

@db_task
def get_all_users():
    users = FamilyUser.objects.filter(is_active=True).order_by("id")
    return list(
        users.values("id", "full_name", "telegram_id", "phone", "role", "created_at",))

@db_task
def get_admin_users():
    users = FamilyUser.objects.filter(is_active=True, role="ADMIN",).order_by("id")
    return list(
        users.values("id", "full_name", "telegram_id",))

# ==================================================
# STATISTICS
# ==================================================

@db_task
def get_statistics():
    total_users = FamilyUser.objects.filter(is_active=True).count()
    admins = FamilyUser.objects.filter(is_active=True, role="ADMIN",).count()
    super_admins = FamilyUser.objects.filter(is_active=True, role="SUPER_ADMIN",).count()
    normal_users = FamilyUser.objects.filter(is_active=True, role="USER",).count()
    total_birthdays = Birthday.objects.filter(is_active=True).count()
    today = datetime.now(TASHKENT_TZ).date()
    today_birthdays = Birthday.objects.filter(birthday_on(today), is_active=True,).count()
    month_birthdays = Birthday.objects.filter(is_active=True, birth_date__month=today.month,).count()
    return {
        "total_users": total_users,
        "admins": admins,
        "super_admins": super_admins,
        "normal_users": normal_users,
        "total_birthdays": total_birthdays,
        "today_birthdays": today_birthdays,
        "month_birthdays": month_birthdays,
    }

# ==================================================
# BIRTHDAY DATABASE
# ==================================================

@db_task
def get_month_birthdays():
    today = datetime.now(TASHKENT_TZ).date()
    birthdays = Birthday.objects.filter(is_active=True, birth_date__month=today.month,).order_by("birth_date__day")
    result = []
    for birthday in birthdays:
        result.append({
                "id": birthday.id,
                "full_name": birthday.full_name,
                "date": birthday.birth_date.strftime("%d.%m"),
                "birth_date": birthday.birth_date,
                "relation": birthday.relation,
            })
    return result

@db_task
def get_upcoming_birthdays():
    today = datetime.now(TASHKENT_TZ).date()
    birthdays = Birthday.objects.filter(is_active=True)
    result = []
    for birthday in birthdays:
        birthday_this_year = next_birthday(birthday.birth_date, today)
        days_left = (birthday_this_year - today).days
        if 0 <= days_left <= 7:
            result.append({
                    "id": birthday.id,
                    "full_name": birthday.full_name,
                    "date": birthday_this_year.strftime("%d.%m"),
                    "days_left": days_left,
                    "relation": birthday.relation,
                })
    result.sort(key=lambda x: x["days_left"])
    return result

@db_task
def get_today_birthdays():
    today = datetime.now(TASHKENT_TZ).date()
    birthdays = Birthday.objects.filter(birthday_on(today), is_active=True,)
    return list(birthdays.values("id", "full_name", "birth_date", "relation",))

@db_task
def get_all_birthdays():
    birthdays = Birthday.objects.filter(is_active=True).order_by("birth_date__month", "birth_date__day",)
    return list(
        birthdays.values("id", "full_name", "birth_date", "relation",))

@db_task
def create_birthday(full_name, birth_date, relation, photo_data,):
    birthday = Birthday.objects.create(full_name=full_name, birth_date=birth_date, relation=relation,)
    birthday.photo.save("birthday.jpg", ContentFile(photo_data), save=True,)
    return birthday.id

@db_task
def delete_birthday(birthday_id,):
    birthday = Birthday.objects.filter(id=birthday_id, is_active=True,).first()
    if not birthday:
        return False
    birthday.is_active = False
    birthday.save(update_fields=["is_active"])
    return True

# ==================================================
# HELPERS
# ==================================================

TELEGRAM_TEXT_LIMIT = 4000

async def answer_long(message: Message, text, **kwargs):
    """Telegram 4096 belgidan uzun xabarni qabul qilmaydi — bo‘lib yuboramiz."""
    chunk = ""
    for block in text.split("\n\n"):
        part = block + "\n\n"
        if chunk and len(chunk) + len(part) > TELEGRAM_TEXT_LIMIT:
            await message.answer(chunk.rstrip(), **kwargs)
            chunk = ""
        chunk += part
    if chunk.strip():
        await message.answer(chunk.rstrip(), **kwargs)

# ==================================================
# START
# ==================================================

@dp.message(CommandStart())
async def start_handler(message: Message, command: CommandObject,):
    user = await get_or_create_user(telegram_id=message.from_user.id, full_name=message.from_user.full_name,)
    safe_name = escape(user.full_name)

    # ==================================================
    # GROUP
    # ==================================================

    if message.chat.type in ("group", "supergroup",):
        await message.answer(
            f"👋 Assalomu alaykum, "
            f"<b>{safe_name}</b>!\n\n"
            "Kerakli bo‘limni tanlang:",
            reply_markup=group_menu(BOT_USERNAME), parse_mode="HTML",)
        return

    # ==================================================
    # PRIVATE PROFILE DEEP LINK
    # ==================================================

    if command.args == "profile":
        # SUPER ADMIN
        if user.role == "SUPER_ADMIN":
            await message.answer(
                "👑 <b>BOSH ADMIN</b>\n\n"
                "Kerakli bo‘limni tanlang:",
                reply_markup=super_admin_panel(),
                parse_mode="HTML",
            )
            return
        # ADMIN
        if user.role == "ADMIN":
            await message.answer(
                "⚙️ <b>ADMIN PANEL</b>\n\n"
                "Kerakli bo‘limni tanlang:",
                reply_markup=admin_panel(),
                parse_mode="HTML",
            )
            return
        # USER
        phone = escape(user.phone or "Kiritilmagan")
        await message.answer(
            "👤 <b>MENING PROFILIM</b>\n\n"
            f"📝 Ism: <b>{safe_name}</b>\n"
            f"📱 Telefon: <b>{phone}</b>\n"
            f"🆔 Telegram ID: "
            f"<code>{user.telegram_id}</code>\n"
            "👤 Rol: <b>Oddiy foydalanuvchi</b>",
            parse_mode="HTML",
        )
        return

    # ==================================================
    # PRIVATE NORMAL START
    # ==================================================

    if user.role == "SUPER_ADMIN":
        await message.answer("👑 <b>BOSH ADMIN</b>\n\n"
            "Kerakli bo‘limni tanlang:", reply_markup=super_admin_menu(), parse_mode="HTML",)
        return
    if user.role == "ADMIN":
        await message.answer(
            "⚙️ <b>ADMIN PANEL</b>\n\n"
            "Kerakli bo‘limni tanlang:", reply_markup=admin_menu(), parse_mode="HTML",)
        return
    await message.answer(
        f"👋 Assalomu alaykum, "
        f"<b>{safe_name}</b>!\n\n"
        "Kerakli bo‘limni tanlang:", reply_markup=user_menu(), parse_mode="HTML",)

# ==================================================
# CHAT ID
# ==================================================

@dp.message(Command("chatid"))
async def chat_id_handler(message: Message,):
    await message.answer(
        "🆔 <b>Chat ID:</b>\n\n"
        f"<code>{message.chat.id}</code>", parse_mode="HTML",)

# ==================================================
# ADMIN PANEL BUTTON
# ==================================================

@dp.message(F.text == "⚙️ Admin panel")
async def admin_panel_handler(message: Message,):
    if not await is_admin_or_super_admin(message.from_user.id):
        return
    await message.answer(
        "⚙️ <b>ADMIN PANEL</b>\n\n"
        "Kerakli bo‘limni tanlang:", reply_markup=admin_panel(), parse_mode="HTML",)

# ==================================================
# SUPER ADMIN BUTTON
# ==================================================

@dp.message(F.text == "👑 Boshqaruv")
async def management_handler(message: Message,):
    if not await is_super_admin(message.from_user.id):
        return
    await message.answer(
        "👑 <b>BOSH ADMIN PANEL</b>\n\n"
        "Kerakli bo‘limni tanlang:", reply_markup=super_admin_panel(), parse_mode="HTML",)

# ==================================================
# USERS
# ==================================================

@dp.callback_query(F.data == "users")
async def users_callback(callback: CallbackQuery,):
    if not await is_admin_or_super_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo‘q.", show_alert=True,)
        return
    users = await get_all_users()
    if not users:
        await callback.message.answer("👥 Hozircha foydalanuvchilar yo‘q.")
        await callback.answer()
        return
    text = "👥 <b>FOYDALANUVCHILAR</b>\n\n"
    for user in users:
        safe_full_name = escape(user["full_name"])
        if user["role"] == "SUPER_ADMIN":
            role_text = "👑 SUPER ADMIN"
        elif user["role"] == "ADMIN":
            role_text = "⚙️ ADMIN"
        else:
            role_text = "👤 USER"
        text += (
            f"🆔 <code>{user['telegram_id']}</code>\n"
            f"📝 {safe_full_name}\n"
            f"👤 {role_text}\n"
        )
        if user["phone"]:
            text += (f"📱 {escape(user['phone'])}\n")
        text += "\n"
    await answer_long(callback.message, text, parse_mode="HTML")
    await callback.answer()

# ==================================================
# ADD ADMIN
# ==================================================

@dp.callback_query(F.data == "add_admin")
async def add_admin_callback(callback: CallbackQuery, state: FSMContext,):
    if not await is_super_admin(callback.from_user.id):
        await callback.answer("❌ Faqat SUPER ADMIN.", show_alert=True,)
        return
    await state.set_state(AddAdminState.waiting_telegram_id)
    await callback.message.answer(
        "➕ <b>ADMIN QO‘SHISH</b>\n\n"
        "Admin qilmoqchi bo‘lgan "
        "odamning Telegram ID sini yuboring.\n\n"
        "Masalan:\n"
        "<code>123456789</code>", parse_mode="HTML",)
    await callback.answer()

# ==================================================
# PROCESS ADMIN ID
# ==================================================

@dp.message(AddAdminState.waiting_telegram_id)
async def process_admin_telegram_id(message: Message, state: FSMContext,):
    if not await is_super_admin(message.from_user.id):
        await state.clear()
        return
    if not message.text:
        return
    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ Telegram ID faqat raqamlardan "
            "iborat bo‘lishi kerak.\n\n"
            "Masalan:\n"
            "<code>123456789</code>", parse_mode="HTML",)
        return
    if telegram_id == SUPER_ADMIN_ID:
        await message.answer("👑 Bu allaqachon SUPER ADMIN.")
        return
    user = await find_user_by_telegram_id(telegram_id)
    if not user:
        await message.answer(
            "❌ Bu Telegram ID bazadan topilmadi.\n\n"
            "U odam avval botga "
            "<code>/start</code> yuborishi kerak.", parse_mode="HTML",)
        return
    if user["role"] == "ADMIN":
        await message.answer(f"⚙️ <b>{escape(user['full_name'])}</b> allaqachon ADMIN.", parse_mode="HTML",)
        await state.clear()
        return
    await state.update_data(user_id=user["id"], full_name=user["full_name"], telegram_id=user["telegram_id"],)
    await message.answer(
        "👑 <b>ADMIN QILISH</b>\n\n"
        f"Ism: <b>{escape(user['full_name'])}</b>\n"
        f"Telegram ID: "
        f"<code>{user['telegram_id']}</code>\n\n"
        "Shu foydalanuvchini ADMIN qilamizmi?", reply_markup=confirm_add_admin(), parse_mode="HTML",)

# ==================================================
# CONFIRM ADD ADMIN
# ==================================================

@dp.callback_query(F.data == "confirm_add_admin")
async def confirm_add_admin_callback(callback: CallbackQuery, state: FSMContext,):
    if not await is_super_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo‘q.", show_alert=True,)
        return
    data = await state.get_data()
    user_id = data.get("user_id")
    if not user_id:
        await state.clear()
        await callback.answer("❌ Ma’lumot topilmadi.", show_alert=True,)
        return
    result = await set_user_admin(user_id)
    if not result:
        await state.clear()
        await callback.answer("❌ Admin qilib bo‘lmaydi.", show_alert=True,)
        return
    await callback.message.edit_text(
        "✅ <b>ADMIN MUVAFFAQIYATLI QO‘SHILDI!</b>\n\n"
        f"📝 Ism: <b>{escape(result['full_name'])}</b>\n"
        f"🆔 Telegram ID: "
        f"<code>{result['telegram_id']}</code>\n"
        "👤 Rol: <b>ADMIN</b>", parse_mode="HTML",)
    await state.clear()
    await callback.answer("Admin qo‘shildi ✅")

# ==================================================
# CANCEL ADD ADMIN
# ==================================================

@dp.callback_query(F.data == "cancel_add_admin")
async def cancel_add_admin_callback(callback: CallbackQuery, state: FSMContext,):
    if not await is_super_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo‘q.", show_alert=True,)
        return
    await state.clear()
    await callback.message.edit_text("❌ <b>Admin qo‘shish bekor qilindi.</b>", parse_mode="HTML",)
    await callback.answer()

# ==================================================
# REMOVE ADMIN
# ==================================================

@dp.callback_query(F.data == "remove_admin")
async def remove_admin_callback(callback: CallbackQuery,):
    if not await is_super_admin(callback.from_user.id):
        await callback.answer("❌ Faqat SUPER ADMIN.", show_alert=True,)
        return
    admins = await get_admin_users()
    if not admins:
        await callback.message.answer("👤 Hozircha boshqa adminlar yo‘q.")
        await callback.answer()
        return
    buttons = []
    for admin in admins:
        safe_name = escape(admin["full_name"])
        buttons.append([InlineKeyboardButton(text=f"➖ {safe_name}", callback_data=(f"remove_admin_{admin['id']}"),)])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(
        "➖ <b>ADMINNI OLIB TASHLASH</b>\n\n"
        "Qaysi adminni oddiy foydalanuvchiga "
        "o‘tkazishni tanlang:", reply_markup=keyboard, parse_mode="HTML",)
    await callback.answer()

# ==================================================
# REMOVE ADMIN CONFIRM
# ==================================================

@dp.callback_query(F.data.startswith("remove_admin_"))
async def remove_admin_confirm_callback(callback: CallbackQuery,):
    if not await is_super_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo‘q.", show_alert=True,)
        return
    try:
        user_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer("❌ ID noto‘g‘ri.", show_alert=True,)
        return
    result = await remove_admin_by_id(user_id)
    if not result:
        await callback.answer("❌ Admin topilmadi.", show_alert=True,)
        return
    await callback.message.edit_text(
        "✅ <b>ADMIN OLIB TASHLANDI</b>\n\n"
        f"📝 {escape(result['full_name'])}\n"
        f"🆔 <code>{result['telegram_id']}</code>\n"
        "👤 Yangi rol: <b>USER</b>", parse_mode="HTML",)
    await callback.answer("Admin olib tashlandi ✅")

# ==================================================
# STATISTICS
# ==================================================

@dp.callback_query(F.data == "statistics")
async def statistics_callback(callback: CallbackQuery,):
    if not await is_admin_or_super_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo‘q.", show_alert=True,)
        return
    stats = await get_statistics()
    text = (
        "📊 <b>STATISTIKA</b>\n\n"
        "👥 <b>Foydalanuvchilar</b>\n"
        f"👤 Jami: <b>{stats['total_users']}</b>\n"
        f"👤 Oddiy user: <b>{stats['normal_users']}</b>\n"
        f"⚙️ Admin: <b>{stats['admins']}</b>\n"
        f"👑 Super admin: <b>{stats['super_admins']}</b>\n\n"
        "🎂 <b>Tug‘ilgan kunlar</b>\n"
        f"🎂 Jami: <b>{stats['total_birthdays']}</b>\n"
        f"🎉 Bugun: <b>{stats['today_birthdays']}</b>\n"
        f"📅 Shu oy: <b>{stats['month_birthdays']}</b>")
    await answer_long(callback.message, text, parse_mode="HTML")
    await callback.answer()

# ==================================================
# BIRTHDAY PANEL
# ==================================================

@dp.callback_query(F.data == "admin_birthdays")
async def admin_birthdays_callback(callback: CallbackQuery,):
    if not await is_admin_or_super_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo‘q.", show_alert=True,)
        return
    await callback.message.answer(
        "🎂 <b>TUG‘ILGAN KUNLAR</b>\n\n"
        "Kerakli amalni tanlang:", reply_markup=birthday_admin_panel(), parse_mode="HTML",)
    await callback.answer()

# ==================================================
# ADD BIRTHDAY
# ==================================================

@dp.callback_query(F.data == "add_birthday")
async def add_birthday_callback(callback: CallbackQuery, state: FSMContext,):
    if not await is_admin_or_super_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo‘q.", show_alert=True,)
        return
    await state.set_state(AddBirthdayState.waiting_full_name)
    await callback.message.answer(
        "➕ <b>TUG‘ILGAN KUN QO‘SHISH</b>\n\n"
        "1️⃣ Tug‘ilgan kun egasining "
        "<b>to‘liq ismini</b> yuboring.\n\n"
        "Masalan:\n"
        "<b>Muhammadali Karimov</b>", reply_markup=cancel_birthday(), parse_mode="HTML",)
    await callback.answer()

# ==================================================
# BIRTHDAY NAME
# ==================================================

@dp.message(AddBirthdayState.waiting_full_name)
async def birthday_full_name(message: Message, state: FSMContext,):
    if not message.text:
        await message.answer("❌ Iltimos, ismni matn ko‘rinishida yuboring.")
        return
    full_name = message.text.strip()
    if len(full_name) < 2:
        await message.answer("❌ Ism juda qisqa.")
        return
    await state.update_data(full_name=full_name)
    await state.set_state(AddBirthdayState.waiting_birth_date)
    await message.answer(
        "2️⃣ <b>Tug‘ilgan sanani kiriting.</b>\n\n"
        "Format:\n"
        "<code>15.10.2018</code>", reply_markup=cancel_birthday(), parse_mode="HTML",)

# ==================================================
# BIRTHDAY DATE
# ==================================================

@dp.message(AddBirthdayState.waiting_birth_date)
async def birthday_birth_date(message: Message, state: FSMContext,):
    if not message.text:
        await message.answer("❌ Sanani matn ko‘rinishida yuboring.")
        return
    try:
        birth_date = datetime.strptime(message.text.strip(),"%d.%m.%Y",).date()
    except ValueError:
        await message.answer(
            "❌ Sana noto‘g‘ri.\n\n"
            "To‘g‘ri format:\n"
            "<code>15.10.2018</code>", parse_mode="HTML",)
        return
    await state.update_data(birth_date=birth_date.isoformat())
    await state.set_state(AddBirthdayState.waiting_relation)
    await message.answer(
        "3️⃣ <b>Qarindoshligini tanlang:</b>",
        reply_markup=relation_keyboard(),
        parse_mode="HTML",
    )

# ==================================================
# BIRTHDAY RELATION
# ==================================================

@dp.callback_query(AddBirthdayState.waiting_relation, F.data.startswith("relation_"))
async def birthday_relation(callback: CallbackQuery, state: FSMContext):
    relations = {
        "relation_togam_ogli": "Tog‘amning o‘g‘li",
        "relation_togam_qizi": "Tog'amni qizi",
        "relation_jiyan": "Jiyanim",
        "relation_kelinoyi": "Kelinoyim",
        "relation_aka": "Akam",
        "relation_togam": "Tog‘am",
        "relation_xola": "Xolam",
        "relation_xolam_ogli": "Xolamni o'g'li",
        "relation_xolam_qizi": "Xolamni qizi",
    }

    relation = relations.get(callback.data)
    if not relation:
        await callback.answer("❌ Qarindoshlik topilmadi.", show_alert=True,)
        return
    await state.update_data(relation=relation)
    await state.set_state(AddBirthdayState.waiting_photo)
    await callback.message.edit_text(
        "4️⃣ <b>RASMINI YUBORING</b> 📷\n\n"
        "Tug‘ilgan kun egasining rasmini "
        "Telegram orqali yuboring.",
        reply_markup=cancel_birthday(), parse_mode="HTML",)
    await callback.answer()

# ==================================================
# BIRTHDAY PHOTO
# ==================================================

@dp.message(AddBirthdayState.waiting_photo, F.photo,)
async def birthday_photo(message: Message, state: FSMContext,):
    data = await state.get_data()
    full_name = data.get("full_name")
    birth_date_raw = data.get("birth_date")
    relation = data.get("relation")
    if not full_name or not birth_date_raw or not relation:
        await state.clear()
        await message.answer("❌ Ma’lumotlar to‘liq emas. Qaytadan boshlang.")
        return
    birth_date = datetime.fromisoformat(birth_date_raw).date()
    photo = message.photo[-1]
    try:
        telegram_file = await bot.get_file(photo.file_id)
        photo_bytes = BytesIO()
        await bot.download_file(telegram_file.file_path, destination=photo_bytes,)
        photo_bytes.seek(0)
        birthday_id = await create_birthday(full_name=full_name, birth_date=birth_date, relation=relation, photo_data=photo_bytes.read(),)
    except Exception:
        logger.exception("❌ Tug‘ilgan kun saqlash xatosi")
        await message.answer("❌ Rasmni saqlashda xatolik yuz berdi. Qaytadan urinib ko‘ring.")
        return
    await state.clear()
    await message.answer(
        "✅ <b>TUG‘ILGAN KUN SAQLANDI!</b>\n\n"
        f"📝 Ism: <b>{escape(full_name)}</b>\n"
        f"📅 Sana: "
        f"<b>{birth_date.strftime('%d.%m.%Y')}</b>\n"
        f"👨‍👩‍👦 Qarindoshligi: "
        f"<b>{escape(relation)}</b>\n"
        "📷 Rasm: <b>saqlandi</b>\n"
        f"🆔 ID: <code>{birthday_id}</code>", parse_mode="HTML",)

@dp.message(AddBirthdayState.waiting_photo)
async def birthday_photo_invalid(message: Message,):
    await message.answer("❌ Iltimos, <b>rasm</b> yuboring. 📷", parse_mode="HTML",)

# ==================================================
# CANCEL BIRTHDAY
# ==================================================

@dp.callback_query(F.data == "cancel_birthday")
async def cancel_birthday_callback( callback: CallbackQuery, state: FSMContext,):
    await state.clear()
    await callback.message.edit_text("❌ <b>Tug‘ilgan kun qo‘shish bekor qilindi.</b>", parse_mode="HTML",)
    await callback.answer()

# ==================================================
# BIRTHDAY LIST
# ==================================================

@dp.callback_query(F.data == "birthday_list")
async def birthday_list_callback(callback: CallbackQuery,):
    if not await is_admin_or_super_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo‘q.", show_alert=True,)
        return
    birthdays = await get_all_birthdays()
    if not birthdays:
        await callback.message.answer("🎂 Hozircha tug‘ilgan kunlar yo‘q.")
        await callback.answer()
        return
    await callback.message.answer("🎂 <b>TUG‘ILGAN KUNLAR RO‘YXATI</b>", parse_mode="HTML",)
    for birthday in birthdays:
        safe_name = escape(birthday["full_name"])
        text = (
            f"🎂 <b>{safe_name}</b>\n"
            f"📅 "
            f"{birthday['birth_date'].strftime('%d.%m.%Y')}\n"
            f"🆔 ID: <code>{birthday['id']}</code>")
        await callback.message.answer(text, reply_markup=confirm_delete_birthday(birthday["id"]), parse_mode="HTML",)
    await callback.answer()

# ==================================================
# TODAY BIRTHDAYS
# ==================================================

@dp.callback_query(F.data == "today_birthdays")
async def today_birthdays_callback(callback: CallbackQuery,):
    if not await is_admin_or_super_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo‘q.", show_alert=True,)
        return
    birthdays = await get_today_birthdays()
    if not birthdays:
        await callback.message.answer("🎂 Bugun tug‘ilgan kun egasi yo‘q.")
        await callback.answer()
        return
    text = ("🎉 <b>BUGUN TUG‘ILGAN KUN!</b>\n\n")
    for birthday in birthdays:
        safe_name = escape(birthday["full_name"])
        safe_relation = escape(birthday["relation"] or "Kiritilmagan")
        text += (
            f"🎂 <b>{safe_name}</b>\n"
            f"👨‍👩‍👦 {safe_relation}\n\n")
    await answer_long(callback.message, text, parse_mode="HTML")
    await callback.answer()

# ==================================================
# MONTH BIRTHDAYS
# ==================================================

@dp.callback_query(F.data == "month_birthdays")
async def month_birthdays_callback(callback: CallbackQuery,):
    if not await is_admin_or_super_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo‘q.", show_alert=True,)
        return
    birthdays = await get_month_birthdays()
    if not birthdays:
        await callback.message.answer("🎂 Bu oyda tug‘ilgan kunlar yo‘q.")
        await callback.answer()
        return

    text = ("📅 <b>SHU OY TUG‘ILGAN KUNLAR</b>\n\n")
    for birthday in birthdays:
        safe_name = escape(birthday["full_name"])
        safe_relation = escape(birthday["relation"] or "Kiritilmagan")
        text += (
            f"🎂 <b>{safe_name}</b>\n"
            f"📅 {birthday['date']}\n"
            f"👨‍👩‍👦 {safe_relation}\n\n")
    await answer_long(callback.message, text, parse_mode="HTML")
    await callback.answer()

# ==================================================
# DELETE BIRTHDAY
# ==================================================

@dp.callback_query(F.data.startswith("delete_birthday_"))
async def delete_birthday_callback(callback: CallbackQuery,):
    if not await is_admin_or_super_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo‘q.", show_alert=True,)
        return
    try:
        birthday_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer("❌ ID noto‘g‘ri.", show_alert=True,)
        return
    result = await delete_birthday(birthday_id)
    if result:
        await callback.message.edit_text("✅ <b>Tug‘ilgan kun o‘chirildi.</b>", parse_mode="HTML",)
        await callback.answer("O‘chirildi ✅")
    else:
        await callback.answer("❌ Tug‘ilgan kun topilmadi.", show_alert=True,)


@dp.callback_query(F.data == "cancel_delete_birthday")
async def cancel_delete_birthday_callback(callback: CallbackQuery,):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Bekor qilindi")

# ==================================================
# GROUP - THIS MONTH
# ==================================================

@dp.callback_query(F.data == "group_month_birthdays")
async def group_month_birthdays(callback: CallbackQuery,):
    await callback.answer()
    birthdays = await get_month_birthdays()
    if not birthdays:
        await callback.message.answer("🎂 Bu oyda tug‘ilgan kunlar yo‘q.")
        return
    text = ("📅 <b>SHU OYDA TUG‘ILGAN KUNLAR</b>\n\n")

    for birthday in birthdays:
        safe_name = escape(birthday["full_name"])
        text += (
            f"🎂 <b>{safe_name}</b>\n"
            f"📅 {birthday['date']}\n\n")
    await answer_long(callback.message, text, parse_mode="HTML")

# ==================================================
# GROUP - UPCOMING
# ==================================================

@dp.callback_query(F.data == "group_upcoming_birthdays")
async def group_upcoming_birthdays(callback: CallbackQuery,):
    await callback.answer()
    birthdays = await get_upcoming_birthdays()
    if not birthdays:
        await callback.message.answer("⏳ Keyingi 7 kun ichida tug‘ilgan kun yo‘q.")
        return
    text = ("⏳ <b>YAQINLASHAYOTGAN TUG‘ILGAN KUNLAR</b>\n\n")
    for birthday in birthdays:
        if birthday["days_left"] == 0:
            left = "🎉 BUGUN!"
        elif birthday["days_left"] == 1:
            left = "🔔 Ertaga"
        else:
            left = (f"⏳ {birthday['days_left']} kun qoldi")
        safe_name = escape(birthday["full_name"])
        text += (
            f"🎂 <b>{safe_name}</b>\n"
            f"📅 {birthday['date']}\n"
            f"{left}\n\n")
    await answer_long(callback.message, text, parse_mode="HTML")


# ==================================================
# PRIVATE USER - THIS MONTH
# ==================================================

@dp.message(F.text == "🎂 Shu oyda tug‘ilgan kunlar")
async def month_birthdays_handler(message: Message,):
    birthdays = await get_month_birthdays()
    if not birthdays:
        await message.answer("🎂 Bu oyda tug‘ilgan kunlar yo‘q.")
        return
    text = ("📅 <b>SHU OYDA TUG‘ILGAN KUNLAR</b>\n\n")
    for birthday in birthdays:
        safe_name = escape(birthday["full_name"])
        text += (f"🎂 <b>{safe_name}</b> — {birthday['date']}\n\n")
    await answer_long(message, text, parse_mode="HTML")


# ==================================================
# PRIVATE USER - UPCOMING
# ==================================================

@dp.message(F.text == "⏳ Yaqinlashayotgan tug‘ilgan kunlar")
async def upcoming_birthdays_handler(message: Message,):
    birthdays = await get_upcoming_birthdays()
    if not birthdays:
        await message.answer("⏳ Keyingi 7 kun ichida tug‘ilgan kun yo‘q.")
        return
    text = ("⏳ <b>YAQINLASHAYOTGAN TUG‘ILGAN KUNLAR</b>\n\n")
    for birthday in birthdays:
        if birthday["days_left"] == 0:
            left = "🎉 BUGUN!"
        elif birthday["days_left"] == 1:
            left = "🔔 Ertaga"
        else:
            left = (f"⏳ {birthday['days_left']} kun qoldi")
        safe_name = escape(birthday["full_name"])
        text += (
            f"🎂 <b>{safe_name}</b>\n"
            f"📅 {birthday['date']}\n"
            f"{left}\n\n")
    await answer_long(message, text, parse_mode="HTML")


# ==================================================
# USER PROFILE BUTTON
# ==================================================

@dp.message(F.text == "👤 Mening profilim")
async def my_profile_handler(message: Message,):

    # Foydalanuvchi mavjud bo‘lmasa, avtomatik yaratiladi.
    user = await get_or_create_user(telegram_id=message.from_user.id, full_name=message.from_user.full_name,)
    role_names = {
        "USER": "Oddiy foydalanuvchi",
        "ADMIN": "Admin",
        "SUPER_ADMIN": "Super admin",
    }

    safe_name = escape(user.full_name)
    safe_phone = escape(user.phone or "Kiritilmagan")
    role_name = role_names.get(user.role, user.role,)

    text = (
        "👤 <b>MENING PROFILIM</b>\n\n"
        f"📝 Ism: <b>{safe_name}</b>\n"
        f"📱 Telefon: <b>{safe_phone}</b>\n"
        f"🆔 Telegram ID: "
        f"<code>{user.telegram_id}</code>\n"
        f"👤 Rol: <b>{role_name}</b>"
    )
    await message.answer(text, parse_mode="HTML",)


@dp.callback_query(F.data == "group_all_birthdays")
async def group_all_birthdays(callback: CallbackQuery):
    await callback.answer()
    birthdays = await get_all_birthdays()
    if not birthdays:
        await callback.message.answer("🎂 Hozircha tug‘ilgan kunlar yo‘q.")
        return
    text = "🎂 <b>HAMMA TUG‘ILGAN KUNLAR</b>\n\n"
    for birthday in birthdays:
        safe_name = escape(birthday["full_name"])
        text += (
            f"🎂 <b>{safe_name}</b>\n"
            f"📅 {birthday['birth_date'].strftime('%d.%m.%Y')}\n\n"
        )
    await answer_long(callback.message, text, parse_mode="HTML")

# ==================================================
# MAIN
# ==================================================

async def main():
    global BOT_USERNAME
    logger.info("🤖 Bot ishga tushmoqda...")
    if not BOT_USERNAME:
        me = await bot.get_me()
        BOT_USERNAME = me.username
    logger.info("🤖 Bot: @%s", BOT_USERNAME)
    logger.info("🎂 Birthday scheduler ishga tushmoqda...")
    scheduler_task = asyncio.create_task(birthday_notification_loop(bot))
    try:
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()

# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":
    asyncio.run(main())