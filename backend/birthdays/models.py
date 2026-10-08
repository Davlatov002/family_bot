from django.db import models

class Birthday(models.Model):
    full_name = models.CharField(max_length=150)
    birth_date = models.DateField()
    relation = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to="birthdays/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_greeting_year = models.PositiveIntegerField(null=True, blank=True)
    last_reminder_year = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.birth_date}"