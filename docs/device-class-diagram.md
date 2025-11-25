# Device Class Diagram

This diagram highlights the `Device` model and its surrounding entities inside the `devices` Django app. It focuses on the key fields and relationships that drive how devices are organized and configured in the system.

```mermaid
classDiagram
    class Organization {
        +name
        +description
    }
    class Area {
        +name
        +parent
        +organization
    }
    class Rack {
        +name
        +area
        +height
    }
    class Vendor {
        +name
        +website
    }
    class DeviceType {
        +vendor
        +model
        +category
    }
    class DeviceRole {
        +name
        +description
    }
    class Device {
        +name
        +management_ip
        +mac_address
        +serial_number
        +inventory_number
        +site
        +image_version
        +status
        +reachable_ping/snmp/ssh/telemetry
        +uptime
        +created_at
        +updated_at
    }
    class DeviceConfiguration {
        +config_text
        +last_updated
    }
    class Interface {
        +name
        +description
        +mac_address
        +ip_address
        +status
        +speed
    }
    class ModuleType {
        +name
        +vendor
        +serial_number
    }

    Device --> Organization : organization
    Device --> Area : area
    Device --> Rack : rack
    Device --> Vendor : vendor
    Device --> DeviceType : device_type
    Device --> DeviceRole : role
    Device --> DeviceConfiguration : configuration (1:1)
    Device --> Interface : interfaces (1:N)
    Device --> ModuleType : modules (1:N)
```

Use the relationships as a quick reference when extending the device domain, adding new fields, or integrating with other apps.
