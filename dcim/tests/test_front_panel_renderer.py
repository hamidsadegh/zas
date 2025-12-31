import pytest

from dcim.svg.front_panel import FrontPanelRenderer


class DummyVendor:
    def __init__(self, name):
        self.name = name


class DummyDeviceType:
    def __init__(self, vendor="Vendor", model="Model", u_height=1):
        self.vendor = DummyVendor(vendor)
        self.model = model
        self.u_height = u_height


def test_renderer_returns_svg_root():
    renderer = FrontPanelRenderer()
    dt = DummyDeviceType()
    result = renderer.render(dt)
    assert result.svg.startswith("<svg")
    assert "NEEDS PORT METADATA" in result.svg
    assert result.placeholder is True


def test_renderer_height_scales_with_u_height():
    renderer = FrontPanelRenderer()
    dt = DummyDeviceType(u_height=3)
    result = renderer.render(dt)
    assert f"height=\"{renderer.HEIGHT_PER_U * 3 + renderer.PADDING * 2}\"" in result.svg
