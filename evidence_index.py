#!/usr/bin/env python3
"""Offline evidence inventory; never acquires measurements or controls equipment."""

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "experiments/evidence_index.csv"
FILE_FIELDS = ("measurement_file", "saleae_file", "husky_trace_file",
               "siglent_image_file", "notes_file")
NUMBER_FIELDS = ("siglent_min_v", "siglent_mean_v", "siglent_rms_v", "rail_droop_mv")
FIELDS = ["run_id", "timestamp", "experiment", "ext_offset", "repeat",
          "oracle_result", "capture_return", *NUMBER_FIELDS, *FILE_FIELDS,
          "sha256_manifest", "notes"]
FORMAT = "hardsignal-evidence-sha256-v1"


def local_file(value):
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError(f"Evidence must be an existing file within the repository: {value}")
    return path


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def manifest_data(row):
    return {"format": FORMAT, "run_id": row["run_id"], "files": [
        {"field": field, "path": row[field], "sha256": digest(local_file(row[field]))}
        for field in FILE_FIELDS if row[field]
    ]}


def validate_rows(rows, check_manifests=True):
    seen = set()
    for row in rows:
        run = row["run_id"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run):
            raise ValueError("run_id must be 1–80 letters/digits/hyphens/underscores")
        if run in seen:
            raise ValueError(f"Duplicate run_id: {run}")
        seen.add(run)
        try:
            stamp = datetime.fromisoformat(row["timestamp"])
        except ValueError as exc:
            raise ValueError(f"{run}: timestamp must be ISO 8601") from exc
        if stamp.utcoffset() is None or not row["experiment"].strip():
            raise ValueError(f"{run}: timezone and experiment description are required")
        for field in ("ext_offset", "repeat"):
            if row[field] and not re.fullmatch(r"[0-9]+", row[field]):
                raise ValueError(f"{run}: {field} must be a nonnegative integer or blank")
        for field in NUMBER_FIELDS:
            if row[field]:
                try:
                    number = Decimal(row[field])
                except InvalidOperation as exc:
                    raise ValueError(f"{run}: invalid {field}") from exc
                if not number.is_finite():
                    raise ValueError(f"{run}: {field} must be finite")
        if row["capture_return"] not in ("", "true", "false", "unknown"):
            raise ValueError(f"{run}: invalid capture_return")
        for field in FILE_FIELDS:
            if row[field]:
                if local_file(row[field]) == INDEX.resolve():
                    raise ValueError("The evidence index cannot reference itself as evidence")
        if row["sha256_manifest"] and check_manifests:
            path = local_file(row["sha256_manifest"])
            if json.loads(path.read_text(encoding="utf-8")) != manifest_data(row):
                raise ValueError(f"{run}: manifest mismatch (evidence changed or wrong manifest)")


def read_rows(check_manifests=True):
    with INDEX.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError("Unexpected evidence index header")
        rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise ValueError("Malformed evidence index row")
    validate_rows(rows, check_manifests)
    return rows


def atomic_write(path, contents):
    """Replace an index/manifest without truncating it on a failed write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                         dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(contents)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def initialize():
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    try:
        with INDEX.open("x", newline="", encoding="utf-8") as stream:
            csv.DictWriter(stream, fieldnames=FIELDS).writeheader()
    except FileExistsError:
        read_rows()
    print(f"Evidence index ready: {INDEX}")


def add(args):
    rows = read_rows()
    row = {field: getattr(args, field) for field in FIELDS}
    row["timestamp"] = row["timestamp"] or datetime.now(timezone.utc).isoformat(timespec="seconds")
    for field in (*FILE_FIELDS, "sha256_manifest"):
        if row[field]:
            row[field] = local_file(row[field]).relative_to(ROOT.resolve()).as_posix()
    validate_rows(rows + [row])
    if not args.dry_run:
        with INDEX.open("a", newline="", encoding="utf-8") as stream:
            csv.DictWriter(stream, fieldnames=FIELDS).writerow(row)
    print(json.dumps({"dry_run": args.dry_run, "row": row}, ensure_ascii=False))


def hash_run(run_id):
    # Permit intentional refresh of stale hashes; still validate metadata/files.
    rows = read_rows(check_manifests=False)
    row = next((item for item in rows if item["run_id"] == run_id), None)
    if row is None:
        raise ValueError(f"Unknown run_id: {run_id}")
    data = manifest_data(row)
    if not data["files"]:
        raise ValueError(f"{run_id}: no evidence files supplied; nothing to hash")
    path = ROOT / "experiments/evidence_manifests" / f"{run_id}.sha256.json"
    if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Manifest destination must stay inside the repository without a file symlink")
    protected = {INDEX.resolve(), (ROOT / "experiments/rail_droop_results.csv").resolve()}
    protected.update(local_file(item[field]) for item in rows for field in FILE_FIELDS if item[field])
    if path.resolve() in protected:
        raise ValueError("Manifest destination overlaps an evidence/data file")
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(previous, dict) or previous.get("format") != FORMAT or previous.get("run_id") != run_id:
            raise ValueError("Refusing to overwrite an unrelated manifest file")
    atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    row["sha256_manifest"] = path.relative_to(ROOT).as_posix()
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    atomic_write(INDEX, output.getvalue())
    print(f"Hashed {len(data['files'])} file(s): {row['sha256_manifest']}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create an empty index without replacing existing rows")
    adding = commands.add_parser("add", help="Index operator-supplied metadata and local evidence")
    for field in FIELDS:
        options = {"required": True} if field in ("run_id", "experiment") else {"default": ""}
        adding.add_argument("--" + field.replace("_", "-"), **options)
    adding.add_argument("--dry-run", action="store_true", help="Print proposed row; do not write")
    commands.add_parser("validate", help="Check rows, referenced files, and any recorded hashes")
    commands.add_parser("summary", help="Print all rows, preserving blank unknown fields")
    hashing = commands.add_parser("hash", help="Write/update this run's SHA-256 manifest and index link")
    hashing.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            initialize()
        elif args.command == "add":
            add(args)
        elif args.command == "hash":
            hash_run(args.run_id)
        else:
            rows = read_rows()
            if args.command == "summary":
                writer = csv.DictWriter(sys.stdout, fieldnames=FIELDS, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            print(f"Validated {len(rows)} run(s).")
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
