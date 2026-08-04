from django.db import models
from django.conf import settings
from catalog.models import Product
from users.models import KAZAKHSTAN_CITIES

class ProductRequest(models.Model):
    class Meta:
        ordering = ['-created_at']
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'
        FULFILLED = 'fulfilled', 'Fulfilled'
        CANCELLED = 'cancelled', 'Cancelled'

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
    # Which city this request's stock is being fulfilled from — derived from
    # the product(s) on the request at creation time (all items on one
    # request must share a single city, same as they must share one
    # supplier). Stored directly so requests can be filtered/scoped by city
    # without joining through items every time.
    city = models.CharField(max_length=50, choices=KAZAKHSTAN_CITIES, blank=True)
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
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='cancelled_requests',
        null=True,
        blank=True
    )
    cancel_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
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


class RequestPhotoReport(models.Model):
    """A delivery/fulfillment photo attached to a request by whoever
    handled it (the supplier or the sales rep who worked the order) —
    e.g. proof of delivery, loaded goods, a signed invoice. Shown on the
    request detail screen and rolled up per-client in the Clients screen."""
    request = models.ForeignKey(
        ProductRequest,
        on_delete=models.CASCADE,
        related_name='photo_reports'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_photo_reports'
    )
    image = models.ImageField(upload_to='photo_reports/')
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Photo report for request #{self.request_id}"