import os
from io import StringIO
from tempfile import NamedTemporaryFile

from django.core.management import call_command
from django.test import TestCase
from openpyxl import Workbook

from dcim.models import Area, Device, DeviceModule, Organization, Site


class TestImportModuleInventoryNumbersCommand(TestCase):
    def setUp(self):
        organization = Organization.objects.create(name="Org")
        site = Site.objects.create(name="Site", organization=organization)
        area = Area.objects.create(name="Area", site=site)
        device = Device.objects.create(
            name="device-01",
            management_ip="10.10.10.10",
            site=site,
            area=area,
        )
        self.module_1 = DeviceModule.objects.create(
            device=device,
            name="Module 1",
            serial_number="SER-001",
        )
        self.module_2 = DeviceModule.objects.create(
            device=device,
            name="Module 2",
            serial_number="SER-002",
            inventory_number="OLD-INV",
        )

    def _build_workbook_file(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Modules"
        sheet["C1"] = "Inventory Number"
        sheet["H1"] = "Serial Number"

        sheet["C2"] = "INV-001"
        sheet["H2"] = "SER-001"

        sheet["C3"] = "INV-002"
        sheet["H3"] = "SER-002"

        sheet["C4"] = "INV-404"
        sheet["H4"] = "SER-404"

        sheet["C5"] = ""
        sheet["H5"] = "SER-001"

        with NamedTemporaryFile(suffix=".xlsx", delete=False) as handle:
            workbook.save(handle.name)
            workbook.close()
            return handle.name

    def test_command_updates_module_inventory_numbers_by_serial(self):
        file_path = self._build_workbook_file()
        output = StringIO()
        try:
            call_command(
                "import_module_inventory_numbers",
                file_path,
                stdout=output,
            )

            self.module_1.refresh_from_db()
            self.module_2.refresh_from_db()

            self.assertEqual(self.module_1.inventory_number, "INV-001")
            self.assertEqual(self.module_2.inventory_number, "INV-002")
            self.assertIn("updated: 2", output.getvalue())
        finally:
            os.unlink(file_path)

    def test_command_dry_run_does_not_save(self):
        file_path = self._build_workbook_file()
        try:
            call_command(
                "import_module_inventory_numbers",
                file_path,
                "--dry-run",
            )

            self.module_1.refresh_from_db()
            self.module_2.refresh_from_db()

            self.assertEqual(self.module_1.inventory_number, None)
            self.assertEqual(self.module_2.inventory_number, "OLD-INV")
        finally:
            os.unlink(file_path)
