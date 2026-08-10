# users/models.py
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from datetime import timedelta
import random
import string
KAZAKHSTAN_CITIES = [
    ('almaty', 'Алматы'),
    ('astana', 'Астана'),
    ('shymkent', 'Шымкент'),
    ('karaganda', 'Қарағанды'),
    ('aktobe', 'Ақтөбе'),
    ('taraz', 'Тараз'),
    ('pavlodar', 'Павлодар'),
    ('ust_kamenogorsk', 'Өскемен'),
    ('semey', 'Семей'),
    ('atyrau', 'Атырау'),
    ('kostanay', 'Қостанай'),
    ('kyzylorda', 'Қызылорда'),
    ('uralsk', 'Орал'),
    ('petropavlovsk', 'Петропавл'),
    ('aktau', 'Ақтау'),
    ('temirtau', 'Теміртау'),
    ('turkestan', 'Түркістан'),
    ('taldykorgan', 'Талдықорған'),
    ('ekibastuz', 'Екібастұз'),
    ('rudny', 'Рудный'),
]

VALID_CITY_CODES = {code for code, _ in KAZAKHSTAN_CITIES}


def validate_city_codes(value):
    """Ensures every entry in a city-code list is a recognised Kazakhstan city."""
    invalid = [code for code in value if code not in VALID_CITY_CODES]
    if invalid:
        raise ValidationError(f'Unknown city code(s): {", ".join(invalid)}')

class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = 'client', 'Client'
        SUPPLIER = 'supplier', 'Supplier'
        SALES_REP = 'sales_rep', 'Sales representative'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(max_length=20, choices=Role.choices)
    phone = models.CharField(max_length=20, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)
    email_verification_code = models.CharField(max_length=6, blank=True)
    is_phone_verified = models.BooleanField(default=False)
    phone_verification_code = models.CharField(max_length=6, blank=True)
    phone_verification_expires_at = models.DateTimeField(null=True, blank=True)
    phone_verification_attempts = models.PositiveSmallIntegerField(default=0)
    expo_push_token = models.CharField(max_length=200, blank=True)
    city = models.CharField(
        max_length=50,
        choices=KAZAKHSTAN_CITIES,
        blank=True,
        default=''
    )
    # Cities a supplier delivers to / covers. Only meaningful for role=supplier;
    # `city` above remains the supplier's primary/HQ city for display purposes.
    service_cities = ArrayField(
        models.CharField(max_length=50, choices=KAZAKHSTAN_CITIES),
        default=list,
        blank=True,
        validators=[validate_city_codes],
        help_text='Cities this supplier covers/delivers to.'
    )
    # A sales representative belongs to exactly one supplier business.
    business_supplier = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='workers', limit_choices_to={'role': 'supplier'}
    )
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # A client created by a sales representative remains assigned to them.
    assigned_sales_rep = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_clients', limit_choices_to={'role': 'sales_rep'}
    )

    def generate_verification_code(self):
        import random, string
        code = ''.join(random.choices(string.digits, k=6))
        self.email_verification_code = code
        self.save()
        return code

    def generate_phone_verification_code(self):
        code = ''.join(random.choices(string.digits, k=6))
        self.phone_verification_code = code
        self.phone_verification_expires_at = timezone.now() + timedelta(minutes=10)
        self.phone_verification_attempts = 0
        self.save(update_fields=[
            'phone_verification_code',
            'phone_verification_expires_at',
            'phone_verification_attempts',
        ])
        return code

    def clear_phone_verification_code(self):
        self.phone_verification_code = ''
        self.phone_verification_expires_at = None
        self.phone_verification_attempts = 0
        self.save(update_fields=[
            'phone_verification_code',
            'phone_verification_expires_at',
            'phone_verification_attempts',
        ])


class BusinessClient(models.Model):
    """A supplier CRM contact; it intentionally has no login credentials."""
    supplier = models.ForeignKey(User, on_delete=models.CASCADE, related_name='business_clients')
    sales_rep = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='crm_clients')
    # Which of the supplier's service cities this client belongs to.
    city = models.CharField(max_length=50, choices=KAZAKHSTAN_CITIES)
    name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name} ({self.supplier})'
