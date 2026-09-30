#!/usr/bin/env python3
"""Read CH1 scalar measurements over Ethernet SCPI; DROOP = MEAN - MIN."""

import argparse
import json
import math
import re
import socket
import sys
import time


HOST = "192.168.1.170"
PORT = 5025
TIMEOUT = 3.0
MAX_RESPONSE = 4096
MEASUREMENTS = ("MIN", "MEAN", "RMS")


def parse_voltage(response, measurement):
    """Parse a PAVA reply (or headerless value) into volts."""
    pattern = (
        rf"(?:(?:C1:(?:PAVA|PARAMETER_VALUE)\s+)?{re.escape(measurement)},\s*)?"
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)"
        r"\s*(V|mV|uV|µV|nV)?(?:\s*,\s*OK)?"
    )
    match = re.fullmatch(pattern, response.strip())
    if not match:
        raise ValueError(f"{measurement}: invalid or unavailable voltage reply {response!r}")
    value = float(match[1])
    # Do not print nonfinite values or large SCPI invalid-measurement sentinels.
    if not math.isfinite(value) or abs(value) >= 9e37:
        raise ValueError(f"{measurement}: unavailable/out-of-range value {response!r}")
    scale = {None: 1.0, "V": 1.0, "mV": 1e-3, "uV": 1e-6,
             "µV": 1e-6, "nV": 1e-9}
    return value * scale[match[2]]


def query(host, port, measurement):
    """Send one read-only query and read a bounded, newline-terminated reply."""
    command = f"C1:PAVA? {measurement}"
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT) as connection:
            deadline = time.monotonic() + TIMEOUT
            connection.settimeout(TIMEOUT)
            connection.sendall((command + "\n").encode("ascii"))
            data = bytearray()
            while b"\n" not in data:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("response deadline exceeded")
                if len(data) >= MAX_RESPONSE:
                    raise ValueError("response exceeds 4096 bytes")
                connection.settimeout(remaining)
                chunk = connection.recv(min(1024, MAX_RESPONSE - len(data)))
                if not chunk:
                    raise ValueError("connection closed before a complete reply")
                data.extend(chunk)
            line, trailing = bytes(data).split(b"\n", 1)
            if trailing.strip():
                raise ValueError("unexpected data after measurement reply")
            return parse_voltage(line.decode("utf-8").strip(), measurement)
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"{host}:{port}, {command}: {exc}") from exc


def read_measurements(host, port):
    values = {name.lower() + "_v": query(host, port, name) for name in MEASUREMENTS}
    values["droop_mv"] = (values["mean_v"] - values["min_v"]) * 1000
    return values


def port_number(value):
    port = int(value)
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="DROOP (mV) = (MEAN - MIN) * 1000, not the rail logger's idle - MIN. "
               "Queries current measurements only; does not configure or trigger acquisition.",
    )
    parser.add_argument("--host", default=HOST, help=f"scope address (default: {HOST})")
    parser.add_argument("--port", type=port_number, default=PORT,
                        help=f"SCPI TCP port (default: {PORT})")
    parser.add_argument("--json", action="store_true", help="print numeric JSON with unit-suffixed keys")
    args = parser.parse_args(argv)
    try:
        values = read_measurements(args.host, args.port)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(values, allow_nan=False))
    else:
        print(f"MIN={values['min_v']:.3f} V  MEAN={values['mean_v']:.3f} V  "
              f"RMS={values['rms_v']:.3f} V  DROOP={values['droop_mv']:.0f} mV")
    return 0


if __name__ == "__main__":
    sys.exit(main())
