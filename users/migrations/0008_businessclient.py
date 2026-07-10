from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('users', '0007_user_sales_rep_relationships')]

    operations = [
        migrations.CreateModel(
            name='BusinessClient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)), ('company_name', models.CharField(blank=True, max_length=200)),
                ('phone', models.CharField(blank=True, max_length=20)), ('email', models.EmailField(blank=True, max_length=254)),
                ('address', models.TextField()), ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)), ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
                ('sales_rep', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='crm_clients', to='users.user')),
                ('supplier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='business_clients', to='users.user')),
            ],
        ),
    ]
