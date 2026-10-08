from functools import wraps

from asgiref.sync import sync_to_async
from django.db import close_old_connections


def db_task(func):
    """
    sync_to_async + eskirgan/uzilgan DB ulanishlarini tozalash.

    Bot HTTP so'rovlarsiz ishlagani uchun Django ulanishlarni o'zi
    yopmaydi. PostgreSQL qayta ishga tushsa, bot "connection already
    closed" xatosida qolib ketmasligi uchun har so'rovdan oldin
    ulanish tekshiriladi.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        close_old_connections()
        return func(*args, **kwargs)

    return sync_to_async(wrapper)
