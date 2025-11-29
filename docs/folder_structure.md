zas/
├── manage.py
├── zas/                      # Django project config
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── dev.py
│   │   ├── prod.py
│   │   └── secrets.py        # optional
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── middleware.py
│
├── core/                     # Home, dashboard, shared UI
│   ├── __init__.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── templates/
│   │   └── core/
│   │       ├── home.html
│   │       ├── dashboard.html
│   │       └── base.html     # global base template
│   └── static/core/          # (optional assets)
│
├── accounts/                 # Auth, users, system settings & credentials
│   ├── __init__.py
│   ├── models.py             # SystemSettings, SiteCredentials
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── services/             # settings-specific logic
│   │   └── settings_service.py
│   ├── templates/accounts/
│   │   ├── login.html
│   │   ├── system_settings.html
│   │   └── credentials_form.html
│   └── tests/
│
├── dcim/                     # Devices, racks, areas, interfaces, VLANs, modules
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── organization.py
│   │   ├── area.py
│   │   ├── rack.py
│   │   ├── device.py
│   │   ├── interface.py
│   │   ├── module.py
│   │   └── vlan.py
│   ├── views/
│   │   ├── device_views.py
│   │   ├── interface_views.py
│   │   ├── rack_views.py
│   │   ├── vlan_views.py
│   │   └── area_views.py
│   ├── forms/
│   │   ├── device_forms.py
│   │   ├── interface_forms.py
│   │   ├── vlan_forms.py
│   │   └── rack_forms.py
│   ├── admin.py
│   ├── urls.py
│   ├── serializers.py         # DRF
│   ├── filters.py             # DRF filters
│   ├── tables.py              # (optional, for django-tables2)
│   ├── templates/dcim/
│   │   ├── device_list.html
│   │   ├── device_detail.html
│   │   ├── interface_list.html
│   │   ├── rack_list.html
│   │   ├── vlan_list.html
│   │   └── forms/*.html
│   ├── management/
│   │   └── commands/
│   │       ├── import_vlans_from_excel.py
│   │       └── import_devices.py
│   └── tests/
│
├── ipam/                     # Future: Prefixes, IP addresses
│   ├── __init__.py
│   ├── models.py
│   ├── serializers.py
│   ├── admin.py
│   ├── urls.py
│   ├── views.py
│   ├── forms.py
│   ├── templates/ipam/
│   └── tests/
│
├── automation/               # Celery jobs, job tracking, backups, CLI, ZTP
│   ├── __init__.py
│   ├── models.py             # AutomationJob, JobRun
│   ├── views.py
│   ├── urls.py
│   ├── serializers.py
│   ├── forms.py
│   ├── admin.py
│   ├── tasks/
│   │   ├── reachability.py
│   │   ├── config_backup.py
│   │   ├── telemetry_polling.py
│   │   └── cli_commands.py
│   ├── services/
│   │   ├── job_runner.py
│   │   ├── ssh_service.py
│   │   ├── snmp_service.py
│   │   ├── netconf_service.py
│   │   └── telemetry_service.py
│   ├── templates/automation/
│   │   ├── job_list.html
│   │   ├── job_detail.html
│   │   └── job_run_detail.html
│   └── tests/
│
├── services/                # Core application services (not domain-specific)
│   ├── __init__.py
│   ├── device_service.py     # domain logic for device validation
│   ├── validation_service.py
│   ├── reachability_service.py
│   └── db_service.py
│
├── scripts/                 # One-off operational scripts
│   ├── import_devices.py
│   ├── sync_netbox.py       # future
│   └── export_inventory.py
│
├── static/                  # Collected static files (build output)
│
├── locale/                  # Translations
│
└── docs/                    # Docs & roadmap
    ├── ROADMAP.md
    ├── architecture.md
    ├── api_reference.md
    └── dcim_models_diagram.png
