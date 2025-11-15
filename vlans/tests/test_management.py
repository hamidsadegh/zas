from io import StringIO
from unittest.mock import patch

import pandas as pd
import pytest
from django.core.management import call_command

from vlans.models import VLAN


def _build_dataframe(vlan_id, name, subnet, gateway, usage_area, description):
    return pd.DataFrame(
        [
            {
                "VLAN ID": vlan_id,
                "Name": name,
                "Subnet": subnet,
                "Gateway": gateway,
                "Usage Area": usage_area,
                "Description": description,
            }
        ]
    )


@pytest.mark.django_db
def test_import_vlans_command_creates_and_updates_entries(tmp_path):
    berlin_path = tmp_path / "berlin.xlsx"
    bonn_path = tmp_path / "bonn.xls"
    berlin_path.write_bytes(b"placeholder")
    bonn_path.write_bytes(b"placeholder")

    data_map = {
        str(berlin_path): _build_dataframe(
            100, "Initial Berlin VLAN", "10.10.0.0/24", "10.10.0.1", "ACI", "Berlin description"
        ),
        str(bonn_path): _build_dataframe(
            200, "Initial Bonn VLAN", "10.20.0.0/24", "10.20.0.1", "InvalidUsage", "Bonn description"
        ),
    }

    def fake_read_excel(path):
        return data_map[str(path)]

    with patch("vlans.management.commands.import_vlans_from_excel.pd.read_excel", side_effect=fake_read_excel):
        out_first = StringIO()
        call_command("import_vlans_from_excel", berlin=str(berlin_path), bonn=str(bonn_path), stdout=out_first)

    assert "Created: 2, Updated: 0" in out_first.getvalue()
    berlin_vlan = VLAN.objects.get(site="Berlin", vlan_id=100)
    assert berlin_vlan.name == "Initial Berlin VLAN"
    bonn_vlan = VLAN.objects.get(site="Bonn", vlan_id=200)
    assert bonn_vlan.usage_area == "Sonstiges"

    data_map[str(berlin_path)] = _build_dataframe(
        100, "Updated Berlin VLAN", "10.10.0.0/24", "10.10.0.254", "ACI", "Updated description"
    )
    data_map[str(bonn_path)] = _build_dataframe(
        200, "Updated Bonn VLAN", "10.20.0.0/24", "10.20.0.254", "Campus", "Updated Bonn"
    )

    with patch("vlans.management.commands.import_vlans_from_excel.pd.read_excel", side_effect=fake_read_excel):
        out_second = StringIO()
        call_command("import_vlans_from_excel", berlin=str(berlin_path), bonn=str(bonn_path), stdout=out_second)

    assert "Created: 0, Updated: 2" in out_second.getvalue()
    berlin_vlan.refresh_from_db()
    bonn_vlan.refresh_from_db()
    assert berlin_vlan.name == "Updated Berlin VLAN"
    assert berlin_vlan.gateway == "10.10.0.254"
    assert bonn_vlan.name == "Updated Bonn VLAN"
    assert bonn_vlan.usage_area == "Campus"
