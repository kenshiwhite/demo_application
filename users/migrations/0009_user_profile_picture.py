from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_businessclient'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='profile_picture',
            field=models.ImageField(blank=True, null=True, upload_to='profile_pictures/'),
        ),
    ]
