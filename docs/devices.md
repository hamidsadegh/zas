# Devices App Documentation

The `devices` app manages network devices, their configurations, and interfaces.

## Models

### Organization
- Represents an organization that owns sites and devices
- Fields: `name`, `description`

### Area
- Hierarchical physical location: Global → Region → Country → Building → Rack
- Fields: `name`, `parent`, `description`

### Site
- Represents a specific site within an organization
- Fields: `name`, `parent`, `organization`, `description`

### Rack
- Represents a rack inside a site
- Fields: `name`, `site`, `height`, `description`

### DeviceRole
- Device role (e.g., Access Switch, Core Switch, Router)

### Vendor
- Device vendor (e.g., Cisco, Juniper)

### Platform
- Device platform linked to a vendor (e.g., IOS-XE, NX-OS)

### DeviceType
- Vendor-specific model of a device (e.g., C9300-48P)

### Device
- Represents a network device
- Fields: `name`, `management_ip`, `mac_address`, `serial_number`, `inventory_number`
- Relations: `organization`, `area`, `vendor`, `device_type`, `platform`, `role`
- Software / Operational: `image_version`, `status`, `uptime`
- Configuration: `configuration` text

### DeviceConfiguration
- Stores full running configuration of a device

### Interface
- Represents a network interface on a device
- Fields: `name`, `description`, `mac_address`, `ip_address`, `status`, `endpoint`, `speed`

## Views

### HTML Views
- `DeviceListView`: Displays paginated devices with search and sort
- `DeviceDetailView`: Shows device details, configuration, and interfaces

### REST API Endpoints
- `/api/devices/`: List & create devices
- `/api/devices/<id>/`: Retrieve, update, delete a device
- `/api/interfaces/`: List & create interfaces
- `/api/interfaces/<id>/`: Retrieve, update, delete an interface

## Templates
- `device_list.html`: Device table with search, sort, pagination
- `device_detail.html`: Device details, configuration, interfaces

