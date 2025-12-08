# ZAS Architecture Overview

## Overview

ZAS is built using Django with REST API endpoints and web templates. It connects to a MySQL database
and can be deployed using Docker.

+-----------------+ +-----------------+ +-----------------+
| Web Client | <----> | Django App | <----> | MySQL |
| (HTML/JS/REST) | | devices/automation| | Database |
+-----------------+ +-----------------+ +-----------------+


## Key Components

### Apps
- `dcim`: Core app managing devices, racks, areas, configurations, and interfaces
- `automation`: Background tasks, device provisioning, backups
      

### Models
- `Organization` → `Sites` → `Areas` → `Racks` → `Devices` → `Interfaces` & `Configurations`
Organization
   └── Site
         └── Area (Building/Floor/Room)
               └── Rack
                     └── Device
                           ├── Interfaces
                           ├── Modules
                           └── Configurations
### REST API
- Built with Django REST Framework
- Provides JSON endpoints for devices and interfaces
- Search, filter, sort supported
