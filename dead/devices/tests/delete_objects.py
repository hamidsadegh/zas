from devices.models import (
    Device, DeviceConfiguration, Interface, DeviceType, DeviceModule,
    Vendor, DeviceRole, Rack, Area, Organization
)

# Delete in order to respect ForeignKey dependencies
DeviceConfiguration.objects.all().delete()  # must delete configs before devices
Interface.objects.all().delete()             # delete interfaces before devices
Device.objects.all().delete()                # delete devices

DeviceModule.objects.all().delete()
DeviceType.objects.all().delete()
DeviceRole.objects.all().delete()
Rack.objects.all().delete()
Area.objects.all().delete()
Vendor.objects.all().delete()
Organization.objects.all().delete()
