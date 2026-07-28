from django.db import migrations


def backfill_request_city(apps, schema_editor):
    ProductRequest = apps.get_model('product_requests', 'ProductRequest')
    # Existing requests predate city-scoping — take the city straight off
    # whichever product the request's first item points to (every item on a
    # request already has to share one supplier, and now one city).
    for req in ProductRequest.objects.prefetch_related('items__product'):
        first_item = req.items.first()
        if first_item and first_item.product.city:
            req.city = first_item.product.city
            req.save(update_fields=['city'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('product_requests', '0006_city'),
        ('catalog', '0005_backfill_product_city'),
    ]

    operations = [
        migrations.RunPython(backfill_request_city, noop),
    ]