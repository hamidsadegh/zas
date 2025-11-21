from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_systemsettings_singleton"),
    ]

    operations = [
        migrations.AddField(
            model_name="systemsettings",
            name="snmp_auth_key",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="snmp_auth_protocol",
            field=models.CharField(
                blank=True,
                choices=[("md5", "MD5"), ("sha", "SHA")],
                default="sha",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="snmp_community",
            field=models.CharField(blank=True, default="public", max_length=128),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="snmp_port",
            field=models.PositiveIntegerField(default=161),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="snmp_priv_key",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="snmp_priv_protocol",
            field=models.CharField(
                blank=True,
                choices=[("des", "DES"), ("aes128", "AES-128")],
                default="aes128",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="snmp_security_level",
            field=models.CharField(
                choices=[
                    ("noAuthNoPriv", "noAuthNoPriv"),
                    ("authNoPriv", "authNoPriv"),
                    ("authPriv", "authPriv"),
                ],
                default="noAuthNoPriv",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="snmp_username",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="systemsettings",
            name="snmp_version",
            field=models.CharField(
                choices=[("v2c", "SNMPv2c"), ("v3", "SNMPv3")],
                default="v2c",
                max_length=5,
            ),
        ),
    ]
