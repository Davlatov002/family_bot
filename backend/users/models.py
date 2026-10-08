from django.db import models

class FamilyUser(models.Model):

    ROLE_CHOICES = [
        ("USER", "Oddiy foydalanuvchi"),
        ("ADMIN", "Admin"),
        ("SUPER_ADMIN", "Super admin"),
    ]

    telegram_id = models.BigIntegerField(unique=True)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="USER")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name