from django.db import migrations


def backfill_product_city(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    User = apps.get_model('users', 'User')
    # Existing products predate per-city stock — assume they belong to
    # whatever city the supplier's account itself is set to. Suppliers
    # should review/reassign these once multi-city stock is live.
    supplier_cities = dict(User.objects.exclude(city='').values_list('id', 'city'))
    for product in Product.objects.all():
        city = supplier_cities.get(product.supplier_id)
        if city:
            product.city = city
            product.save(update_fields=['city'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0004_product_city'),
        ('users', '0011_businessclient_city'),
    ]

    operations = [
        migrations.RunPython(backfill_product_city, noop),
    ]