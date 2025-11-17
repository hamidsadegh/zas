from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SystemSettings",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tacacs_enabled", models.BooleanField(default=False)),
                ("tacacs_server_ip", models.GenericIPAddressField(blank=True, null=True, protocol="IPv4")),
                ("tacacs_port", models.PositiveIntegerField(default=49)),
                ("tacacs_key", models.CharField(blank=True, max_length=255, null=True)),
                ("tacacs_authorization_service", models.CharField(blank=True, max_length=100, null=True)),
                ("tacacs_retries", models.PositiveSmallIntegerField(default=3)),
                ("tacacs_session_timeout", models.PositiveIntegerField(default=60)),
                ("tacacs_admin_group", models.CharField(blank=True, max_length=100, null=True)),
                ("tacacs_superuser_group", models.CharField(blank=True, max_length=100, null=True)),
                ("allow_local_superusers", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "System Settings",
                "verbose_name_plural": "System Settings",
            },
        ),
    ]
