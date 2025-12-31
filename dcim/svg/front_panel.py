"""
Deterministic front-panel SVG renderer for DeviceType.

Rules:
- Flat, front-only orthographic SVG.
- Uses DeviceType metadata only; no external fetches.
- If port metadata is missing, renders a generic placeholder with warnings.
"""
from dataclasses import dataclass
from typing import Optional

from django.utils.text import slugify


@dataclass
class RenderResult:
    svg: str
    placeholder: bool


class FrontPanelRenderer:
    WIDTH = 400
    HEIGHT_PER_U = 28
    PADDING = 12

    def render(self, device_type) -> RenderResult:
        u_height = int(getattr(device_type, "u_height", 1) or 1)
        height = self.HEIGHT_PER_U * max(u_height, 1)
        vendor = getattr(device_type, "vendor", None)
        vendor_name = getattr(vendor, "name", "") if vendor else ""
        model = getattr(device_type, "model", "") or str(device_type)

        ports = self._get_port_metadata(device_type)
        placeholder = not ports

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.WIDTH}" height="{height + self.PADDING * 2}" viewBox="0 0 {self.WIDTH} {height + self.PADDING * 2}">',
            '<style>',
            ".chassis{fill:#f8fafc;stroke:#cbd5e1;stroke-width:1.5;}",
            ".text-title{font-family:'Inter',sans-serif;font-size:14px;font-weight:700;fill:#0f172a;}",
            ".text-sub{font-family:'Inter',sans-serif;font-size:12px;fill:#475569;}",
            ".port-rj45{fill:#dbeafe;stroke:#94a3b8;stroke-width:1;}",
            ".port-sfp{fill:#e2e8f0;stroke:#94a3b8;stroke-width:1;}",
            ".port-qsfp{fill:#e0f2fe;stroke:#0284c7;stroke-width:1;}",
            ".warning{fill:#f97316;font-weight:700;font-size:14px;font-family:'Inter',sans-serif;}",
            '</style>',
            f'<rect class="chassis" rx="8" ry="8" x="{self.PADDING}" y="{self.PADDING}" width="{self.WIDTH - 2*self.PADDING}" height="{height}"/>',
            f'<text class="text-title" x="{self.PADDING + 10}" y="{self.PADDING + 18}">{self._escape(vendor_name) or "Unknown Vendor"}</text>',
            f'<text class="text-sub" x="{self.PADDING + 10}" y="{self.PADDING + 36}">{self._escape(model)}</text>',
        ]

        if placeholder:
            svg_parts.append(
                f'<text class="warning" x="{self.WIDTH/2}" y="{height/2 + self.PADDING}" text-anchor="middle">NEEDS PORT METADATA</text>'
            )
        else:
            svg_parts.extend(self._render_ports(ports, height))

        svg_parts.append("</svg>")
        return RenderResult(svg="".join(svg_parts), placeholder=placeholder)

    def _get_port_metadata(self, device_type):
        """Stub: gather port metadata if available."""
        # In current models we have no templates; return empty to trigger placeholder.
        return []

    def _render_ports(self, ports, height):
        parts = []
        rows = max(1, len(ports) // 24 + 1)
        port_w = 16
        port_h = 10
        gap = 6
        x_start = self.PADDING + 12
        y_start = self.PADDING + 50
        per_row = 24
        for idx, port in enumerate(ports):
            row = idx // per_row
            col = idx % per_row
            x = x_start + col * (port_w + gap)
            y = y_start + row * (port_h + gap)
            if y + port_h > height + self.PADDING:
                break
            cls = "port-rj45"
            if port.get("type") == "sfp":
                cls = "port-sfp"
            elif port.get("type") == "qsfp":
                cls = "port-qsfp"
            parts.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{port_w}" height="{port_h}" rx="1.5" ry="1.5"/>')
        return parts

    def _escape(self, text: Optional[str]) -> str:
        return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_front_svg_filename(device_type):
    base = slugify(f"{getattr(device_type, 'vendor', '')}-{getattr(device_type, 'model', '')}") or str(device_type.id)
    return f"{base or device_type.id}.svg"
