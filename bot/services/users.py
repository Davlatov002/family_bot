from asgiref.sync import sync_to_async
from users.models import FamilyUser


@sync_to_async
def get_or_create_user(telegram_id, full_name):
    user, created = FamilyUser.objects.get_or_create(telegram_id=telegram_id, defaults={"full_name": full_name,})

    if not created and user.full_name != full_name:
        user.full_name = full_name
        user.save(update_fields=["full_name"])

    return user