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
        related_name='requests',
        null=True,
        blank=True
    )
    supplier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_requests',
        null=True,
        blank=True
    )
    sales_rep = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='created_requests',
        null=True,
        blank=True
    )
    business_client = models.ForeignKey(
        'users.BusinessClient', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='requests'
    )
    note = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    delivery_address = models.TextField(blank=True)
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    desired_delivery_date = models.DateField(null=True, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        client_name = self.client.username if self.client else self.business_client.name
        return f"{client_name} → {self.supplier} ({self.status})"


class RequestItem(models.Model):
    request = models.ForeignKey(
        ProductRequest,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='request_items'
    )
    quantity = models.PositiveIntegerField()
    price_at_request = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"


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
