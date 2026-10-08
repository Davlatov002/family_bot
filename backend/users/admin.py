from django.contrib import admin
from .models import FamilyUser

@admin.register(FamilyUser)
class FamilyUserAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "telegram_id", "phone", "role", "is_active",)
    search_fields = ("full_name", "telegram_id", "phone",)
    list_filter = ("role", "is_active",)