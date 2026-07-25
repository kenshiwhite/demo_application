from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('product_requests', '0004_request_cancellation'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='productrequest',
            options={'ordering': ['-created_at']},
        ),
    ]