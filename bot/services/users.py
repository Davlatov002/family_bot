import os

from users.models import FamilyUser
from bot.services.db import db_task


def _get_super_admin_id():
    try:
        return int(os.getenv("SUPER_ADMIN_ID", "0"))
    except ValueError:
        return 0


@db_task
def get_or_create_user(telegram_id, full_name):
    user, created = FamilyUser.objects.get_or_create(telegram_id=telegram_id, defaults={"full_name": full_name,})

    update_fields = []

    if not created and user.full_name != full_name:
        user.full_name = full_name
        update_fields.append("full_name")

    # .env dagi SUPER_ADMIN_ID egasi avtomatik SUPER ADMIN bo'ladi
    super_admin_id = _get_super_admin_id()
    if super_admin_id and telegram_id == super_admin_id and user.role != "SUPER_ADMIN":
        user.role = "SUPER_ADMIN"
        update_fields.append("role")

    if update_fields:
        user.save(update_fields=update_fields)

    return user
