from django.db import models
from django.conf import settings


EXPENSE_CATEGORY_CHOICES = [
    ('rent', 'Аренда'),
    ('logistics', 'Логистика и доставка'),
    ('utilities', 'Коммунальные услуги'),
    ('marketing', 'Реклама и маркетинг'),
    ('equipment', 'Оборудование'),
    ('taxes', 'Налоги и сборы'),
    ('other', 'Прочее'),
]


class Expense(models.Model):
    """A manually-entered business expense — rent, logistics, one-off
    purchases, anything that isn't cost-of-goods or a worker salary.
    Scoped to a supplier business; any staff member (supplier or their
    sales reps) can log one, but it always counts against the business
    as a whole in the finance summary, not against an individual rep."""
    supplier = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='expenses', limit_choices_to={'role': 'supplier'}
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='logged_expenses'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=20, choices=EXPENSE_CATEGORY_CHOICES, default='other')
    description = models.CharField(max_length=255, blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [models.Index(fields=['supplier', 'date'])]

    def __str__(self):
        return f'{self.get_category_display()} — {self.amount} ({self.date})'


class WorkerBonus(models.Model):
    """An ad-hoc bonus/commission paid to a specific sales rep — separate
    from their base_salary so the finance summary can optionally include
    or exclude bonuses from the salary-expense calculation."""
    supplier = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='worker_bonuses', limit_choices_to={'role': 'supplier'}
    )
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='bonuses', limit_choices_to={'role': 'sales_rep'}
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='granted_bonuses'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [models.Index(fields=['supplier', 'date'])]

    def __str__(self):
        return f'Bonus for {self.worker_id} — {self.amount} ({self.date})'