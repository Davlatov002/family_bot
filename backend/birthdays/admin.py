from django.contrib import admin
from .models import Birthday

@admin.register(Birthday)
class BirthdayAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'birth_date', 'relation', 'is_active')
    search_fields = ('full_name', 'relation',)
    list_filter = ('is_active',)
