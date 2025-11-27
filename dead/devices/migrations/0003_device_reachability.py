from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0002_device_modules'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='reachable_ssh',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='device',
            name='reachable_telemetry',
            field=models.BooleanField(default=False),
        ),
    ]
