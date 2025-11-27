from django.db import migrations, models
import django.db.models.deletion


def clear_legacy_modules(apps, schema_editor):
    ModuleType = apps.get_model('devices', 'ModuleType')
    ModuleType.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(clear_legacy_modules, migrations.RunPython.noop),
        migrations.AddField(
            model_name='moduletype',
            name='device',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='modules', to='devices.device'),
        ),
        migrations.AddField(
            model_name='moduletype',
            name='serial_number',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='moduletype',
            name='vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='modules', to='devices.vendor'),
        ),
    ]
