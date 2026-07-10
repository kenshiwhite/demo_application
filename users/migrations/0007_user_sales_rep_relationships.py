from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_user_phone_verification'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='assigned_sales_rep',
            field=models.ForeignKey(blank=True, limit_choices_to={'role': 'sales_rep'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_clients', to='users.user'),
        ),
        migrations.AddField(
            model_name='user',
            name='business_supplier',
            field=models.ForeignKey(blank=True, limit_choices_to={'role': 'supplier'}, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='workers', to='users.user'),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('client', 'Client'), ('supplier', 'Supplier'), ('sales_rep', 'Sales representative'), ('admin', 'Admin')], max_length=20),
        ),
    ]
