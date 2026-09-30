#!/usr/bin/env python3
"""Read Siglent CH1 scalars and log rail droop as IDLE - MIN (not MEAN - MIN)."""

import argparse
import csv
from decimal import DecimalException
import json
import sys

import rail_droop_log as logger
import siglent_read as reader


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Even --dry-run contacts the scope with measurement queries only. "
               "Metadata describes an existing test; no hardware settings are changed. "
               "Initialize the CSV with rail_droop_log.py init first.",
    )
    parser.add_argument("--host", default=reader.HOST)
    parser.add_argument("--port", type=reader.port_number, default=reader.PORT)
    parser.add_argument("--offset", "--ext-offset", dest="offset",
                        type=logger.nonnegative_int, required=True,
                        help="reported ext_offset metadata, not ADC offset")
    parser.add_argument("--repeat", type=logger.nonnegative_int, required=True)
    parser.add_argument("--idle", "--idle-v", dest="idle", type=logger.voltage,
                        required=True, help="separately measured idle rail voltage (V)")
    parser.add_argument("--output-mode", default="unknown")
    for flag in ("--hp-state", "--lp-state-after-test"):
        parser.add_argument(flag, type=str.lower, choices=("true", "false", "unknown"),
                            default="unknown", help="operator-reported metadata only")
    parser.add_argument("--oracle", required=True, help="operator-reported oracle result")
    parser.add_argument("--capture", "--capture-return", dest="capture", type=str.lower,
                        choices=("true", "false", "unknown"), required=True,
                        help="reported capture return: true=timeout; not an oracle verdict")
    parser.add_argument("--notes", default="")
    parser.add_argument("--dry-run", action="store_true",
                        help="query live readings and preview a validated row without writing CSV")
    parser.add_argument("--json", action="store_true",
                        help="print JSON; row Decimal values are exact decimal strings")
    args = parser.parse_args(argv)
    try:
        # Fail on missing/incompatible/invalid CSV before contacting the scope.
        logger.validated_rows(logger.read_rows())
        readings = reader.read_measurements(args.host, args.port)
        # Convert via decimal text, avoiding Decimal's binary-float expansion.
        args.minimum = logger.voltage(str(readings["min_v"]))
        args.mean = logger.voltage(str(readings["mean_v"]))
        args.rms = logger.voltage(str(readings["rms_v"]))
        row = logger.add_result(args, dry_run=args.dry_run, quiet=True)
    except FileNotFoundError:
        print(f"Error: CSV not found: {logger.CSV_PATH}. Run rail_droop_log.py init first.",
              file=sys.stderr)
        return 1
    except (OSError, RuntimeError, ValueError, csv.Error,
            argparse.ArgumentTypeError, DecimalException) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"dry_run": args.dry_run, "csv_path": str(logger.CSV_PATH),
                          "row": row, "siglent_droop_mv": readings["droop_mv"]},
                         default=str, allow_nan=False))
    else:
        print("DRY RUN — CSV unchanged" if args.dry_run else f"Logged to {logger.CSV_PATH}")
        print(f"Siglent droop (MEAN - MIN): {readings['droop_mv']:.3f} mV; "
              f"rail logger droop (IDLE - MIN): {row['droop_mv']} mV")
        writer = csv.DictWriter(sys.stdout, fieldnames=logger.FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
