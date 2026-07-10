from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('product_requests', '0002_productrequest_sales_rep'), ('users', '0008_businessclient')]
    operations = [
        migrations.AlterField(model_name='productrequest', name='client', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='requests', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='productrequest', name='business_client', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='requests', to='users.businessclient')),
        migrations.AddField(model_name='productrequest', name='delivery_latitude', field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name='productrequest', name='delivery_longitude', field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
    ]
