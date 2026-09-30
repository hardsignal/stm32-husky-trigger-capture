#!/usr/bin/env python3
"""Offline CSV logger for manually entered Siglent rail measurements."""

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, DecimalException, InvalidOperation
from html import escape
from pathlib import Path
import sys


CSV_PATH = Path(__file__).resolve().parent / "experiments/rail_droop_results.csv"
REPORT_PATH = CSV_PATH.with_name("rail_droop_report.md")
FIELDS = [
    "timestamp", "ext_offset", "repeat", "output_mode", "hp_state",
    "lp_state_after_test", "rail_idle_v", "rail_min_v", "rail_mean_v",
    "rail_rms_v", "droop_mv", "oracle_result", "capture_return", "notes",
]


def voltage(value):
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError("expected a finite voltage") from exc
    if not number.is_finite():
        raise argparse.ArgumentTypeError("expected a finite voltage")
    return number


def nonnegative_int(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("expected a nonnegative integer")
    return number


def read_rows(strict=True):
    with CSV_PATH.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        missing = [field for field in FIELDS if field not in columns]
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(missing))
        if len(columns) != len(set(columns)):
            raise ValueError("CSV contains duplicate column names")
        if strict and columns != FIELDS:
            raise ValueError(f"Unexpected CSV header in {CSV_PATH}")
        rows = list(reader)
        if any(None in row or None in row.values() for row in rows):
            raise ValueError("CSV contains an incomplete or oversized row")
        return rows


def validated_rows(rows=None):
    if rows is None:
        rows = read_rows(strict=False)
    droops = []
    for index, row in enumerate(rows, start=1):
        try:
            values = {}
            for field in ("rail_idle_v", "rail_min_v", "rail_mean_v",
                          "rail_rms_v", "droop_mv"):
                try:
                    values[field] = voltage(row[field])
                except argparse.ArgumentTypeError as exc:
                    raise ValueError(f"{field} must be a finite number") from exc
            for field in ("repeat", "ext_offset"):
                try:
                    nonnegative_int(row[field])
                except (ValueError, argparse.ArgumentTypeError) as exc:
                    raise ValueError(f"{field} must be a nonnegative integer") from exc
            if values["rail_min_v"] > values["rail_idle_v"]:
                raise ValueError("rail_min_v must be <= rail_idle_v")
            calculated = (values["rail_idle_v"] - values["rail_min_v"]) * 1000
            if abs(calculated - values["droop_mv"]) > Decimal("0.01"):
                raise ValueError("stored droop_mv differs from calculated droop "
                                 "by more than 0.01 mV")
            droops.append(calculated)
        except (ValueError, DecimalException) as exc:
            raise ValueError(f"Test #{index}: {exc}") from exc
    return rows, droops


def markdown_cell(value):
    """Escape table-sensitive characters and render newlines as <br>.

    Underscores remain literal in the Markdown source and may render as emphasis.
    """
    text = escape(str(value), quote=True)
    for character in "\\|`*[]":
        text = text.replace(character, f"&#{ord(character)};")
    return text.replace("\r\n", "<br>").replace("\r", "<br>").replace("\n", "<br>")


def report():
    rows, droops = validated_rows()
    lines = [
        "# Rail droop report", "",
        "Source: `experiments/rail_droop_results.csv`.", "",
        f"Number of tests: {len(rows)}", "",
        "All values and operator notes below come from the CSV. Droop is "
        "calculated as (rail_idle_v - rail_min_v) * 1000. Comparisons are "
        "descriptive and do not establish causality. Oracle results are "
        "reproduced as entered; no fault-success classification is inferred.", "",
    ]
    if not rows:
        lines.extend(["No tests logged. Droop statistics and baseline comparisons "
                      "are unavailable.", ""])
    else:
        # Include every CSV column, including any additional operator columns.
        columns = list(rows[0])
        headings = ["Test"] + columns + [
            "Calculated droop (mV)", "Droop delta vs test #1 (mV)",
        ]
        lines.append("| " + " | ".join(map(markdown_cell, headings)) + " |")
        lines.append("| " + " | ".join("---" for _ in headings) + " |")
        for index, (row, droop) in enumerate(zip(rows, droops), start=1):
            cells = [index] + [row[column] for column in columns] + [
                droop, format(droop - droops[0], "+f"),
            ]
            lines.append("| " + " | ".join(map(markdown_cell, cells)) + " |")
        largest = max(droops)
        largest_tests = ", ".join(
            f"#{index}" for index, droop in enumerate(droops, start=1)
            if droop == largest
        )
        lines.extend([
            "", f"Minimum calculated droop: {min(droops)} mV.", "",
            f"Maximum calculated droop: {largest} mV.", "",
            f"Mean calculated droop: {sum(droops) / len(droops):.3f} mV.", "",
            f"Largest measured droop: {largest} mV, test(s) {largest_tests}.", "",
            f"Baseline: first logged test (#1), calculated droop {droops[0]} mV. "
            "This reference is not necessarily an unperturbed control. "
            "Each table delta is the test's calculated droop minus this baseline; "
            "a positive delta means a larger measured droop.", "",
        ])
        if len(rows) == 1:
            lines.extend(["Only one row is logged; trend conclusions are not "
                          "possible yet.", ""])
    lines.extend([
        "---", "Hardsignal Labs  ",
        "Independent cyber-physical security research  ",
        "Researcher: Maciej Duranczyk", "",
    ])
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {REPORT_PATH}")


def initialize():
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with CSV_PATH.open("x", newline="", encoding="utf-8") as stream:
            csv.DictWriter(stream, fieldnames=FIELDS).writeheader()
    except FileExistsError:
        read_rows()
        print(f"Already initialized: {CSV_PATH}")
    else:
        print(f"Created: {CSV_PATH}")


def add_result(args):
    rows = read_rows()  # Require init and the exact append schema.
    row = dict(zip(FIELDS, [
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
        args.offset, args.repeat, args.output_mode, args.hp_state,
        args.lp_state_after_test, args.idle, args.minimum, args.mean,
        args.rms, (args.idle - args.minimum) * 1000,
        args.oracle, args.capture, args.notes,
    ]))
    validated_rows(rows + [row])  # Reject invalid data before opening for append.
    with CSV_PATH.open("a", newline="", encoding="utf-8") as stream:
        csv.DictWriter(stream, fieldnames=FIELDS).writerow(row)
    print(f"Logged droop {row['droop_mv']} mV to {CSV_PATH}")


def summarize():
    rows, droops = validated_rows()
    if not rows:
        print("No tests logged.")
        return
    writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    print(f"\nTests: {len(rows)}")
    print(f"Calculated droop (mV): min={min(droops)}, max={max(droops)}, "
          f"mean={sum(droops) / len(droops):.3f}, "
          f"spread={max(droops) - min(droops)}")
    print("Calculated droop comparison (mV; delta from first logged baseline; "
          "not necessarily an unperturbed control):")
    for index, (row, droop) in enumerate(zip(rows, droops), start=1):
        print(f"  #{index}: offset={row['ext_offset']}, repeat={row['repeat']}, "
              f"droop={droop}, delta={droop - droops[0]:+.3f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create CSV without overwriting existing data")
    add = commands.add_parser("add", help="Append one manually entered result")
    add.add_argument("--offset", type=nonnegative_int, required=True,
                     help="Reported ext_offset, not ADC offset; record clock context in notes")
    add.add_argument("--repeat", type=nonnegative_int, required=True)
    add.add_argument("--idle", type=voltage, required=True, help="Idle rail voltage (V)")
    add.add_argument("--min", dest="minimum", type=voltage, required=True,
                     help="Minimum rail voltage (V)")
    add.add_argument("--mean", type=voltage, required=True, help="Mean rail voltage (V)")
    add.add_argument("--rms", type=voltage, required=True, help="RMS rail voltage (V)")
    add.add_argument("--oracle", required=True, help="Operator-reported oracle result")
    add.add_argument("--capture", type=str.lower, choices=("true", "false", "unknown"),
                     required=True, help="Reported capture API return: true=timeout, "
                     "false=no timeout; not an oracle verdict")
    add.add_argument("--output-mode", default="unknown", help="Reported output mode")
    for flag in ("--hp-state", "--lp-state-after-test"):
        add.add_argument(flag, type=str.lower, choices=("true", "false", "unknown"),
                         default="unknown", help="Reported state; metadata only")
    add.add_argument("--notes", default="")
    commands.add_parser("summary", help="Print all rows and compare measured droop")
    commands.add_parser("report", help="Write an offline Markdown report from the CSV")
    commands.add_parser("validate", help="Check CSV columns and measurement values")
    args = parser.parse_args()
    try:
        if args.command == "init":
            initialize()
        elif args.command == "add":
            add_result(args)
        elif args.command == "report":
            report()
        elif args.command == "validate":
            rows, _ = validated_rows()
            print(f"Validation passed: {len(rows)} test(s).")
        else:
            summarize()
    except FileNotFoundError:
        parser.exit(1, f"CSV not found: {CSV_PATH}. Run init first.\n")
    except (OSError, ValueError, csv.Error, argparse.ArgumentTypeError,
            DecimalException) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
