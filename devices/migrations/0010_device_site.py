from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0009_delete_systemsettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="site",
            field=models.CharField(
                choices=[("Berlin", "Berlin"), ("Bonn", "Bonn"), ("Gemeinsam", "Gemeinsam")],
                default="Gemeinsam",
                max_length=50,
            ),
        ),
    ]
