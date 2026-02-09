from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dcim", "0018_devicestackmember"),
    ]

    operations = [
        migrations.AddField(
            model_name="site",
            name="domain",
            field=models.CharField(
                blank=True,
                help_text="Default DNS domain for this site (e.g. dwelle.de).",
                max_length=255,
            ),
        ),
    ]
