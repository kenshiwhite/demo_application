from django.db import migrations


def backfill_businessclient_city(apps, schema_editor):
    BusinessClient = apps.get_model('users', 'BusinessClient')
    User = apps.get_model('users', 'User')
    user_cities = dict(User.objects.exclude(city='').values_list('id', 'city'))
    # Existing CRM contacts predate city-scoping — assume they belong to
    # whichever city the sales rep who owns them is in, falling back to the
    # supplier's own city. Suppliers should review/reassign these once
    # multi-city clients are live.
    for contact in BusinessClient.objects.all():
        city = (user_cities.get(contact.sales_rep_id) if contact.sales_rep_id else None) \
            or user_cities.get(contact.supplier_id)
        if city:
            contact.city = city
            contact.save(update_fields=['city'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_businessclient_city'),
    ]

    operations = [
        migrations.RunPython(backfill_businessclient_city, noop),
    ]