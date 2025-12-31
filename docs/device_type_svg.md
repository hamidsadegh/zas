# Device Type Front SVGs

We now auto-generate flat, front-only SVG panels for every `DeviceType`.

## Generate
```
python manage.py generate_device_type_svgs
python manage.py generate_device_type_svgs --force   # overwrite existing
python manage.py generate_device_type_svgs --only <device_type_id>
python manage.py generate_device_type_svgs --dry-run
```

SVGs are stored under `MEDIA_ROOT/device-type-svg/<vendor-model>.svg` and referenced by the `DeviceType.front_svg` field.

## Renderer
- Lives in `dcim/svg/front_panel.py`
- Flat orthographic SVG (no 3D)
- If port metadata is missing, emits a placeholder with the warning “NEEDS PORT METADATA”.

## Admin
- DeviceType admin shows a preview and has an action “Regenerate front SVG” to force regeneration for selected types.

## UI
- Rack visualization uses the generated SVG when available (falls back to existing front image otherwise).
