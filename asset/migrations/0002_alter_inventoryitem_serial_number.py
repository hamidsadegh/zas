from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("asset", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inventoryitem",
            name="serial_number",
            field=models.CharField(
                blank=True,
                help_text="Serial number assigned by the vendor.",
                max_length=100,
                null=True,
                unique=True,
            ),
        ),
    ]
