#!/usr/bin/env python3
"""FI-0 check; run with an existing, configured Husky scope (see experiment note)."""

import math
import subprocess
import sys


def run_command(args, timeout=15):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    output = result.stdout + result.stderr
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed ({result.returncode}):\n{output}")
    return output


def recovery_check(scope):
    """Print checks and one trace's statistics; never configure or reconnect scope."""
    usb = run_command(["lsusb"])
    for label, ids in (("ST-LINK/V2.1", ("0483:374b",)),
                       ("Husky", ("2b3e:ace5", "2b3e:ace6"))):
        matches = [line for line in usb.splitlines()
                   if any(device_id in line.lower() for device_id in ids)]
        if len(matches) != 1:
            raise RuntimeError(f"Expected exactly one {label}; found {len(matches)}")
        print(f"PASS USB {label}: {matches[0]}")

    if scope is None:
        raise RuntimeError("Pass the existing configured scope from your Python session; "
                           "see experiments/2026-09-28-fi-0-recovery-baseline.md. "
                           "No new connection is opened because it would change settings.")
    if "Husky" not in scope.get_name():
        raise RuntimeError("The supplied scope is not a Husky")

    # Read settings only. Fail closed instead of silently repairing configuration.
    checks = {
        "8000 samples": scope.adc.samples == 8000,
        "single segment": scope.adc.segments == 1,
        "non-streaming capture": not scope.adc.stream_mode,
        "basic TIO4 trigger": (scope.trigger.module == "basic"
                               and scope.trigger.triggers == "tio4"),
        "rising edge": scope.adc.basic_mode == "rising_edge",
        "TIO4 input": scope.io.tio4 == "high_z",
        "normal ADC": not scope.adc.test_mode and scope.ADS4128.mode == "normal",
        "glitch engine disabled": not scope.glitch.enabled,
        "crowbar outputs disabled": not scope.io.glitch_hp and not scope.io.glitch_lp,
        "no HS2 glitch output": scope.io.hs2 != "glitch",
        "bounded capture timeout": (math.isfinite(scope.adc.timeout)
                                    and 0 < scope.adc.timeout <= 30),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("Scope preflight failed: " + ", ".join(failed))
    print("PASS existing scope configuration; no settings changed")

    # Disable servers and the stock examine-end register-write hook. No halt,
    # reset, resume, flash, programming, or target-memory-write commands.
    output = run_command([
        "openocd", "-c", "gdb_port disabled; tcl_port disabled; telnet_port disabled",
        "-f", "interface/stlink.cfg", "-c", "transport select hla_swd",
        "-f", "target/stm32f4x.cfg",
        "-c", "stm32f4x.cpu configure -event examine-end {}; reset_config none",
        "-c", 'init; if {![stm32f4x.cpu was_examined]} {error "Target not examined"}; '
              'echo FI0_TARGET_EXAMINED; shutdown',
    ])
    if "FI0_TARGET_EXAMINED" not in output:
        raise RuntimeError("OpenOCD did not confirm target examination:\n" + output)
    print("PASS OpenOCD target examination")

    scope.arm()
    if scope.capture():
        raise RuntimeError("TIO4 capture timed out; no retry performed")
    trace = scope.get_last_trace()
    if trace is None or len(trace) != 8000 or not all(math.isfinite(x) for x in trace):
        raise RuntimeError("Capture did not return 8000 finite samples")
    low, high = float(min(trace)), float(max(trace))
    print(f"Capture: samples={len(trace)}, min={low}, max={high}, peak-to-peak={high-low}")
    errors = scope.adc.errors
    if errors:
        raise RuntimeError(f"ADC reported errors: {errors}")
    print("PASS one normal TIO4 capture (statistics are not an exact-match acceptance test)")


if __name__ == "__main__":
    try:
        recovery_check(globals().get("scope"))
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
