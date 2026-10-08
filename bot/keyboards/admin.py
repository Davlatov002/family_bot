from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton,)

# ==================================================
# SUPER ADMIN PANEL
# ==================================================

def super_admin_panel():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Foydalanuvchilar",
                    callback_data="users",
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ Admin qo‘shish",
                    callback_data="add_admin",
                ),
                InlineKeyboardButton(
                    text="➖ Adminni olib tashlash",
                    callback_data="remove_admin",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎂 Tug‘ilgan kunlar",
                    callback_data="admin_birthdays",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Statistika",
                    callback_data="statistics",
                )
            ],
        ]
    )


# ==================================================
# ADMIN PANEL
# ==================================================

def admin_panel():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Foydalanuvchilar",
                    callback_data="users",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎂 Tug‘ilgan kunlar",
                    callback_data="admin_birthdays",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Statistika",
                    callback_data="statistics",
                )
            ],
        ]
    )


# ==================================================
# ADD ADMIN CONFIRM
# ==================================================

def confirm_add_admin():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Ha, admin qilish",
                    callback_data="confirm_add_admin",
                ),
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="cancel_add_admin",
                ),
            ]
        ]
    )


# ==================================================
# BIRTHDAY ADMIN PANEL
# ==================================================

def birthday_admin_panel():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Tug‘ilgan kun qo‘shish",
                    callback_data="add_birthday",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Tug‘ilgan kunlar",
                    callback_data="birthday_list",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎉 Bugungi tug‘ilgan kun",
                    callback_data="today_birthdays",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Shu oy",
                    callback_data="month_birthdays",
                )
            ],
        ]
    )


# ==================================================
# CANCEL BIRTHDAY
# ==================================================

def cancel_birthday():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="cancel_birthday",
                )
            ]
        ]
    )


# ==================================================
# DELETE BIRTHDAY
# ==================================================

def confirm_delete_birthday(birthday_id,):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Ha, o‘chirish",
                    callback_data=(
                        f"delete_birthday_{birthday_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="❌ Yo‘q",
                    callback_data="birthday_list",
                ),
            ]
        ]
    )


def relation_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👨 Tog‘amning o‘g‘li",
                    callback_data="relation_togam_ogli",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👨 Tog'amni qizi",
                    callback_data="relation_togam_qizi",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👦 Jiyanim",
                    callback_data="relation_jiyan",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👩 Kelinoyim",
                    callback_data="relation_kelinoyi",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👨 Akam",
                    callback_data="relation_aka",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👨 Tog‘am",
                    callback_data="relation_togam",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👩 Xolam",
                    callback_data="relation_xola",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👩 Xolamni o'g'li",
                    callback_data="relation_xolam_ogli",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👩 Xolamni qizi",
                    callback_data="relation_xolam_qizi",
                )
            ],
        ]
    )