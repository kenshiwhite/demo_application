from django.db import models
from django.conf import settings

class Notification(models.Model):
    class Type(models.TextChoices):
        NEW_REQUEST = 'new_request', 'New Request'
        REQUEST_ACCEPTED = 'request_accepted', 'Request Accepted'
        REQUEST_DECLINED = 'request_declined', 'Request Declined'
        REQUEST_FULFILLED = 'request_fulfilled', 'Request Fulfilled'
        NEW_RESPONSE = 'new_response', 'New Response'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=30,
        choices=Type.choices
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username} — {self.title}"