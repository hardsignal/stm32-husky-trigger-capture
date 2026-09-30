"""Offline evidence-index tests using synthetic files in temporary repositories."""

import contextlib
import hashlib
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

import evidence_index as evidence


class EvidenceIndexTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.index = self.root / "experiments/evidence_index.csv"
        for patcher in (patch.object(evidence, "ROOT", self.root),
                        patch.object(evidence, "INDEX", self.index),
                        patch.object(socket, "socket", side_effect=AssertionError("network forbidden"))):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.assertEqual(self.invoke("init")[0], 0)
        self.file = self.root / "notes.txt"
        self.file.write_text("synthetic bench notes\n", encoding="utf-8")
        self.args = ["add", "--run-id", "test-1", "--experiment", "Synthetic fixture",
                     "--notes-file", "notes.txt"]

    def invoke(self, *args):
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            status = evidence.main(list(args))
        return status, output.getvalue(), error.getvalue()

    def test_dry_run_and_blank_values(self):
        before = self.index.read_bytes()
        status, output, error = self.invoke(*self.args, "--dry-run")
        self.assertEqual((status, error), (0, ""))
        row = json.loads(output)["row"]
        self.assertEqual(row["siglent_min_v"], "")
        self.assertEqual(row["saleae_file"], "")
        self.assertTrue(row["timestamp"].endswith("+00:00"))
        self.assertEqual(self.index.read_bytes(), before)

    def test_append_exact_metadata_and_preserve_existing_rows(self):
        self.assertEqual(self.invoke(*self.args)[0], 0)
        before = self.index.read_bytes()
        note = 'comma, quote" and\nnewline'
        self.assertEqual(self.invoke(*self.args, "--run-id", "test-2", "--notes", note,
                                    "--ext-offset", "200", "--repeat", "8",
                                    "--siglent-min-v", "3.12", "--siglent-mean-v", "3.19",
                                    "--siglent-rms-v", "3.19", "--rail-droop-mv", "80.00",
                                    "--oracle-result", "PASS", "--capture-return", "false")[0], 0)
        self.assertTrue(self.index.read_bytes().startswith(before))
        row = evidence.read_rows()[-1]
        self.assertEqual(row["notes"], note)
        self.assertEqual(row["rail_droop_mv"], "80.00")
        self.assertEqual(self.invoke("init")[0], 0)
        self.assertEqual(self.invoke("summary")[0], 0)

    def test_invalid_metadata_and_missing_files_do_not_write(self):
        before = self.index.read_bytes()
        for extra in (("--run-id", "../escape"), ("--repeat", "-1"),
                      ("--siglent-rms-v", "NaN"), ("--rail-droop-mv", "Infinity"),
                      ("--timestamp", "2026-09-30T00:00:00"),
                      ("--capture-return", "yes"), ("--saleae-file", "missing.sal"),
                      ("--notes-file", "experiments"),
                      ("--notes-file", "experiments/evidence_index.csv")):
            with self.subTest(extra=extra):
                self.assertEqual(self.invoke(*self.args, *extra)[0], 1)
                self.assertEqual(self.index.read_bytes(), before)

    def test_duplicate_id_rejected(self):
        self.invoke(*self.args)
        before = self.index.read_bytes()
        self.assertEqual(self.invoke(*self.args)[0], 1)
        self.assertEqual(self.index.read_bytes(), before)

    def test_outside_path_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other) / "outside.txt"
            outside.write_text("not evidence")
            (self.root / "link.txt").symlink_to(outside)
            for value in (str(outside), "link.txt"):
                self.assertEqual(self.invoke(*self.args, "--notes-file", value)[0], 1)

    def test_hash_validation_and_explicit_refresh(self):
        self.invoke(*self.args)
        before = self.file.read_bytes()
        self.assertEqual(self.invoke("hash", "--run-id", "test-1")[0], 0)
        row = evidence.read_rows()[0]
        manifest = self.root / row["sha256_manifest"]
        record = json.loads(manifest.read_text())["files"][0]
        self.assertEqual(record["sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(self.file.read_bytes(), before)
        self.file.write_text("changed synthetic notes")
        self.assertEqual(self.invoke("validate")[0], 1)
        self.assertEqual(self.invoke("hash", "--run-id", "test-1")[0], 0)
        self.assertEqual(self.invoke("validate")[0], 0)

    def test_hash_requires_files_and_known_run(self):
        self.assertEqual(self.invoke("hash", "--run-id", "absent")[0], 1)
        self.invoke(*self.args, "--notes-file", "")
        self.assertEqual(self.invoke("hash", "--run-id", "test-1")[0], 1)
        self.assertFalse((self.root / "experiments/evidence_manifests").exists())

    def test_unrelated_manifest_not_overwritten(self):
        self.invoke(*self.args)
        path = self.root / "experiments/evidence_manifests/test-1.sha256.json"
        path.parent.mkdir()
        path.write_text('{"unrelated": true}')
        before = path.read_bytes()
        self.assertEqual(self.invoke("hash", "--run-id", "test-1")[0], 1)
        self.assertEqual(path.read_bytes(), before)

    def test_missing_referenced_file_fails_validation(self):
        self.invoke(*self.args)
        self.file.unlink()
        self.assertEqual(self.invoke("validate")[0], 1)

    def test_measurement_csv_is_only_read(self):
        data = self.root / "experiments/rail_droop_results.csv"
        data.write_bytes(b"timestamp,rail_min_v\nsynthetic,3.12\n")
        before = data.read_bytes()
        self.assertEqual(self.invoke(*self.args, "--measurement-file",
                                    "experiments/rail_droop_results.csv")[0], 0)
        self.assertEqual(self.invoke("hash", "--run-id", "test-1")[0], 0)
        self.assertEqual(data.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
