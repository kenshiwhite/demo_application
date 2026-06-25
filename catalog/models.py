from django.db import models
from django.conf import settings

CATEGORY_CHOICES = [
    ('food_beverages', 'Продукты и напитки'),
    ('electronics', 'Электроника'),
    ('clothing', 'Одежда и обувь'),
    ('construction', 'Строительные материалы'),
    ('chemicals', 'Химия и бытовая химия'),
    ('furniture', 'Мебель'),
    ('automotive', 'Автозапчасти'),
    ('office', 'Офисные товары'),
    ('medical', 'Медицинские товары'),
    ('agriculture', 'Сельское хозяйство'),
    ('packaging', 'Упаковка'),
    ('equipment', 'Оборудование и инструменты'),
    ('cosmetics', 'Косметика и гигиена'),
    ('textile', 'Ткани и текстиль'),
    ('other', 'Другое'),
]

class Product(models.Model):
    supplier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='products'
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='other',
        blank=True,
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name