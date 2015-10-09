from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os

class Command(BaseCommand):
    def handle(self, *args, **options):
        if not User.objects.filter(username="admin").exists():
            password = os.environ.get('DJANGO_ADMIN_PASSWORD')
            User.objects.create_superuser("admin", "admin@admin.com", password)
