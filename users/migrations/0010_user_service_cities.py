# users/migrations/0010_user_service_cities.py
import django.contrib.postgres.fields
from django.db import migrations, models

import users.models


def backfill_service_cities(apps, schema_editor):
    """For existing suppliers with a single `city` set, seed service_cities
    with that one city so nothing regresses to 'covers nowhere'."""
    User = apps.get_model('users', 'User')
    suppliers = User.objects.filter(role='supplier').exclude(city='')
    for supplier in suppliers.iterator():
        if not supplier.service_cities:
            supplier.service_cities = [supplier.city]
            supplier.save(update_fields=['service_cities'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_user_profile_picture'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='service_cities',
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
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
                    ],
                    max_length=50,
                ),
                blank=True,
                default=list,
                size=None,
                validators=[users.models.validate_city_codes],
                help_text='Cities this supplier covers/delivers to.',
            ),
        ),
        migrations.RunPython(backfill_service_cities, noop_reverse),
    ]