from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_alter_sshcredential_ssh_password"),
    ]

    operations = [
        migrations.AddField(
            model_name="systemsettings",
            name="auto_logout_idle_minutes",
            field=models.PositiveSmallIntegerField(
                default=15,
                help_text="Automatically log out inactive users after 5 to 60 minutes.",
                validators=[
                    django.core.validators.MinValueValidator(5),
                    django.core.validators.MaxValueValidator(60),
                ],
            ),
        ),
    ]
