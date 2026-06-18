from django.db import models
from django.conf import settings
from catalog.models import Product

class ProductRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'
        FULFILLED = 'fulfilled', 'Fulfilled'

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='requests'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='requests'
    )
    quantity = models.PositiveIntegerField()
    note = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.client.username} → {self.product.name} ({self.status})"

class SupplierResponse(models.Model):
    request = models.OneToOneField(
        ProductRequest,
        on_delete=models.CASCADE,
        related_name='response'
    )
    supplier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    message = models.TextField()
    offered_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response to request #{self.request.id}"