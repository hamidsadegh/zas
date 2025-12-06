# ZAS Architecture Overview

## Overview

ZAS is built using Django with REST API endpoints and web templates. It connects to a MariaDB database
and can be deployed using Docker.

+-----------------+ +-----------------+ +-----------------+
| Web Client | <----> | Django App | <----> | MariaDB |
| (HTML/JS/REST) | | devices/automation| | Database |
+-----------------+ +-----------------+ +-----------------+


## Key Components

### Apps
- `devices`: Core app managing devices, racks, areas, configurations, and interfaces
- `automation`: Background tasks, device provisioning, backups

### Models
- `Organization` → `Sites` → `Areas` → `Racks` → `Devices` → `Interfaces` & `Configurations`
Organization
   └── Site
         └── Area
               └── Rack
                     └── Device
                           ├── Interfaces
                           └── Configurations
### REST API
- Built with Django REST Framework
- Provides JSON endpoints for devices and interfaces
- Search, filter, sort supported
