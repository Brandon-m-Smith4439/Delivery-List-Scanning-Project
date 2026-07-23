from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTOMATION = ROOT / "automation" / "crystal_delivery_export"


class CrystalDeliveryExportAutomationTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        required = {
            "README.md",
            "crystal-export.config.json",
            "Setup-DeliveryListAutomation.bat",
            "Initialize-DeliveryListAutomation.ps1",
            "Run-DeliveryListAutomation.ps1",
            "Install-DeliveryListAutomationTasks.ps1",
            "import_delivery_folder.py",
        }
        self.assertEqual(required - {path.name for path in AUTOMATION.iterdir()}, set())

    def test_config_matches_known_aw_report(self) -> None:
        config = json.loads((AUTOMATION / "crystal-export.config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["Report"]["ParameterName"], "DeliveryDate")
        self.assertEqual(config["Database"]["Server"], "SQLAWGLASS")
        self.assertEqual(config["Database"]["Database"], "BFSMAIN")
        self.assertEqual(config["Database"]["User"], "bsmith")
        self.assertTrue(config["Report"]["SourcePath"].endswith(r"BFS\CR\DeliveryList.rpt"))
        self.assertTrue(config["DestinationFolder"].startswith(r"\\bfs.buildersfirstsource.com\Departments"))
        self.assertNotIn("Password", config["Database"])

    def test_password_is_prompted_and_dpapi_encrypted(self) -> None:
        setup = (AUTOMATION / "Initialize-DeliveryListAutomation.ps1").read_text(encoding="utf-8")
        self.assertIn("Read-Host", setup)
        self.assertIn("-AsSecureString", setup)
        self.assertIn("ConvertFrom-SecureString", setup)
        self.assertNotIn("DbPassword", setup)

    def test_exporter_uses_safe_publish_and_existing_importer(self) -> None:
        runner = (AUTOMATION / "Run-DeliveryListAutomation.ps1").read_text(encoding="utf-8")
        self.assertIn("SetParameterValue", runner)
        self.assertIn("ExportToDisk", runner)
        self.assertIn(".partial", runner)
        self.assertIn("Get-FileHash", runner)
        self.assertIn("import_delivery_folder.py", runner)
        self.assertIn("Local\\BFSDeliveryListAutomation", runner)

    def test_import_wrapper_reuses_project_business_layer(self) -> None:
        importer = (AUTOMATION / "import_delivery_folder.py").read_text(encoding="utf-8")
        self.assertIn("from scanner_config import load_config", importer)
        self.assertIn("from delivery_store import create_store", importer)
        self.assertIn("store.import_delivery_folder", importer)
        compile(importer, str(AUTOMATION / "import_delivery_folder.py"), "exec")


if __name__ == "__main__":
    unittest.main()
