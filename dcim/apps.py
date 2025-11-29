from django.apps import AppConfig


class DcimConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dcim"

# class DevicesConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'devices'

# class VlansConfig(AppConfig):
#     default_auto_field = "django.db.models.BigAutoField"
#     name = "vlans"
#     verbose_name = "VLAN Management"
