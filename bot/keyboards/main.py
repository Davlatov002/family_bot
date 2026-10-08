from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


# ==================================================
# USER MENU
# ==================================================

def user_menu():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🎂 Shu oyda tug‘ilgan kunlar"
                )
            ],
            [
                KeyboardButton(
                    text="⏳ Yaqinlashayotgan tug‘ilgan kunlar"
                )
            ],
            [
                KeyboardButton(
                    text="👤 Mening profilim"
                )
            ],
        ],
        resize_keyboard=True,
    )


# ==================================================
# ADMIN MENU
# ==================================================

def admin_menu():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🎂 Shu oyda tug‘ilgan kunlar"
                )
            ],
            [
                KeyboardButton(
                    text="⏳ Yaqinlashayotgan tug‘ilgan kunlar"
                )
            ],
            [
                KeyboardButton(
                    text="👤 Mening profilim"
                )
            ],
            [
                KeyboardButton(
                    text="⚙️ Admin panel"
                )
            ],
        ],
        resize_keyboard=True,
    )


# ==================================================
# SUPER ADMIN MENU
# ==================================================

def super_admin_menu():

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🎂 Shu oyda tug‘ilgan kunlar"
                )
            ],
            [
                KeyboardButton(
                    text="⏳ Yaqinlashayotgan tug‘ilgan kunlar"
                )
            ],
            [
                KeyboardButton(
                    text="👤 Mening profilim"
                )
            ],
            [
                KeyboardButton(
                    text="👑 Boshqaruv"
                )
            ],
        ],
        resize_keyboard=True,
    )


# ==================================================
# GROUP MENU
# ==================================================

def group_menu(bot_username):

    if not bot_username:
        raise ValueError(
            "BOT_USERNAME .env faylida kiritilmagan."
        )

    bot_username = bot_username.lstrip("@").strip()

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎂 Shu oyda tug‘ilgan kunlar",
                    callback_data="group_month_birthdays",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏳ Yaqinlashayotgan tug‘ilgan kunlar",
                    callback_data="group_upcoming_birthdays",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎂 Hamma tug‘ilgan kunlar",
                    callback_data="group_all_birthdays"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Mening profilim",
                    url=(
                        f"https://t.me/"
                        f"{bot_username}"
                        f"?start=profile"
                    ),
                )
            ],
        ]
    )