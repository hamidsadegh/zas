from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('automation', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='automationjob',
            name='job_type',
            field=models.CharField(choices=[('backup', 'Configuration Backup'), ('ztp', 'Zero Touch Provisioning'), ('cli', 'CLI Command Execution'), ('telemetry', 'Telemetry Polling'), ('reachability', 'Reachability Check')], max_length=30),
        ),
    ]
