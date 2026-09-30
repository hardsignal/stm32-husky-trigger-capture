"""Integration tests use mocked readings and temporary CSVs, never equipment/data."""

import contextlib
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import siglent_log as integration


class SiglentLogTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "results.csv"
        for patcher in (
            patch.object(integration.logger, "CSV_PATH", self.path),
            patch.object(integration.reader.socket, "create_connection",
                         side_effect=AssertionError("network forbidden in offline tests")),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(integration.reader, "read_measurements", return_value={
            "min_v": 3.12, "mean_v": 3.19, "rms_v": 3.19, "droop_mv": 70.0,
        })
        self.read = patcher.start()
        self.addCleanup(patcher.stop)
        with contextlib.redirect_stdout(io.StringIO()):
            integration.logger.initialize()
        self.args = ["--offset", "200", "--repeat", "8", "--idle", "3.20",
                     "--oracle", "PASS", "--capture", "false", "--notes", 'a,"note"\nline 2']

    def invoke(self, extra=()):
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            result = integration.main(self.args + list(extra))
        return result, output.getvalue(), error.getvalue()

    def test_dry_run_shows_row_without_writing(self):
        before = self.path.read_bytes()
        result, output, error = self.invoke(["--dry-run", "--json"])
        self.assertEqual((result, error), (0, ""))
        payload = json.loads(output)
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["row"]["droop_mv"], "80.00")
        self.assertEqual(payload["siglent_droop_mv"], 70.0)
        self.assertEqual(payload["row"]["notes"], self.args[-1])
        self.assertEqual(payload["row"]["hp_state"], "unknown")
        self.assertEqual(self.path.read_bytes(), before)
        self.read.assert_called_once_with("192.168.1.170", 5025)

    def test_append_preserves_existing_bytes_and_metadata(self):
        self.assertEqual(self.invoke(["--json"])[0], 0)
        before = self.path.read_bytes()
        result, output, error = self.invoke([
            "--host", "example.invalid", "--port", "5000", "--output-mode", "reported",
            "--hp-state", "false", "--lp-state-after-test", "false", "--json",
        ])
        self.assertEqual((result, error), (0, ""))
        self.assertTrue(self.path.read_bytes().startswith(before))
        rows = integration.logger.read_rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[-1]["droop_mv"], "80.00")
        self.assertEqual(rows[-1]["output_mode"], "reported")
        self.assertEqual(rows[-1]["lp_state_after_test"], "false")
        self.assertEqual(rows[-1]["notes"], self.args[-1])
        payload = json.loads(output)
        self.assertFalse(payload["dry_run"])
        self.assertEqual(rows[-1], {key: str(value) for key, value in payload["row"].items()})
        self.read.assert_called_with("example.invalid", 5000)

    def test_invalid_live_values_do_not_write(self):
        before = self.path.read_bytes()
        for name, value in (("min_v", 3.3), ("mean_v", float("nan")), ("rms_v", float("inf"))):
            self.read.return_value = {"min_v": 3.12, "mean_v": 3.19, "rms_v": 3.19,
                                      "droop_mv": 70.0, name: value}
            for extra in ([], ["--dry-run"]):
                with self.subTest(name=name, extra=extra):
                    result, output, error = self.invoke(extra)
                    self.assertEqual(result, 1)
                    self.assertEqual(output, "")
                    self.assertIn("Error:", error)
                    self.assertEqual(self.path.read_bytes(), before)

    def test_reader_failure_does_not_write(self):
        before = self.path.read_bytes()
        self.read.side_effect = RuntimeError("mock SCPI timeout")
        result, output, error = self.invoke()
        self.assertEqual((result, output), (1, ""))
        self.assertIn("mock SCPI timeout", error)
        self.assertEqual(self.path.read_bytes(), before)

    def test_missing_csv_fails_before_network(self):
        self.path.unlink()
        self.assertEqual(self.invoke(["--dry-run"])[0], 1)
        self.read.assert_not_called()
        self.assertFalse(self.path.exists())

    def test_invalid_existing_csv_fails_before_network(self):
        # Synthetic invalid row; the repository's experiment CSV is never used.
        row = dict.fromkeys(integration.logger.FIELDS, "0")
        row.update(rail_idle_v="3.20", rail_min_v="3.12", droop_mv="70")
        with self.path.open("a", newline="") as stream:
            csv.DictWriter(stream, fieldnames=integration.logger.FIELDS).writerow(row)
        before = self.path.read_bytes()
        self.assertEqual(self.invoke()[0], 1)
        self.read.assert_not_called()
        self.assertEqual(self.path.read_bytes(), before)

    def test_text_preview_labels_both_droops(self):
        result, output, error = self.invoke(["--dry-run"])
        self.assertEqual((result, error), (0, ""))
        self.assertIn("DRY RUN", output)
        self.assertIn("MEAN - MIN): 70.000 mV", output)
        self.assertIn("IDLE - MIN): 80.00 mV", output)
        self.assertIn("rail_idle_v", output)

    def test_invalid_metadata_fails_before_network(self):
        for extra in (["--idle", "nan"], ["--repeat", "-1"], ["--port", "0"]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                integration.main(self.args + extra)
        self.read.assert_not_called()


if __name__ == "__main__":
    unittest.main()
