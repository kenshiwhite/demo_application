from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_user_service_cities'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='bonus',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='user',
            name='salary',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
