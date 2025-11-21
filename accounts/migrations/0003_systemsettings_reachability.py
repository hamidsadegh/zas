from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_systemsettings_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='reachability_interval_minutes',
            field=models.PositiveIntegerField(default=10),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='reachability_last_run',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='reachability_ping_enabled',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='reachability_snmp_enabled',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='reachability_ssh_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='reachability_telemetry_enabled',
            field=models.BooleanField(default=False),
        ),
    ]
