from django.contrib.auth.models import AbstractUser
from django.db import models
import random
import string

class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = 'client', 'Client'
        SUPPLIER = 'supplier', 'Supplier'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(max_length=20, choices=Role.choices)
    phone = models.CharField(max_length=20, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    is_email_verified = models.BooleanField(default=False)
    email_verification_code = models.CharField(max_length=6, blank=True)
    expo_push_token = models.CharField(max_length=200, blank=True)

    def generate_verification_code(self):
        import random, string
        code = ''.join(random.choices(string.digits, k=6))
        self.email_verification_code = code
        self.save()
        return code