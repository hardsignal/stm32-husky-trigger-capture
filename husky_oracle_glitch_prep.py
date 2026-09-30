#!/usr/bin/env python3
"""Prepare Husky timing and validate one clean capture; no fault injection.

Keep the physical crowbar cable disconnected. The NUCLEO must already emit
PA0/TIO4 triggers. No target power, gain, or firmware changes are made.
"""

import sys

import chipwhisperer as cw
import numpy as np
from usb1 import USBErrorIO

from husky_oracle_baseline import (
    SAMPLES, TIMING_WINDOW_US, cleanup, configure, drivers_off, preflight,
)


def check_safe(scope):
    # Readback checks at each checkpoint; these are not continuous monitoring.
    preflight(scope)
    # ChipWhisperer 6.0.0 returns None for the "disabled" HS2 mode.
    if scope.io.hs2 is not None:
        raise RuntimeError("HS2 must remain disabled")


def main():
    scope = None
    exit_code = 0
    capture_usb_failure = False
    try:
        scope = cw.scope(name="Husky")
        # Do not silently accept an initially enabled crowbar driver.
        if scope.io.glitch_hp or scope.io.glitch_lp:
            drivers_off(scope)
            raise RuntimeError("Crowbar was enabled on connection; disabled, aborting")

        # Shared setup forces HP/LP off and HS2 disabled, configures 10/40 MHz,
        # waits for main PLL, enables the engine, selects PLL, then waits for MMCM.
        fs = configure(scope)
        print("HS2 readback:", repr(scope.io.hs2))
        check_safe(scope)
        scope.glitch.width = 0
        check_safe(scope)

        expected = {
            "enabled": True, "clk_src": "pll", "trigger_src": "ext_single",
            "ext_offset": 1590, "repeat": 1, "width": 0,
            "output": "glitch_only", "num_glitches": 1,
        }
        for name, value in expected.items():
            if getattr(scope.glitch, name) != value:
                raise RuntimeError(f"Glitch setting readback mismatch: {name}")

        scope.adc.errors = 0
        check_safe(scope)
        scope.arm()
        try:
            timed_out = scope.capture()
        except USBErrorIO:
            capture_usb_failure = True
            raise
        check_safe(scope)
        if timed_out:
            raise RuntimeError("Clean capture timed out")
        trace = np.asarray(scope.get_last_trace(), dtype=float)
        errors = scope.adc.errors
        error_flags = [flag.strip() for flag in str(errors).split(",")
                       if flag.strip()] if errors else []
        if "gain too low error" in error_flags:
            print("WARNING: gain too low error (retained; timing analysis allowed)")
        other_errors = [flag for flag in error_flags if flag != "gain too low error"]
        if trace.shape != (SAMPLES,) or not np.all(np.isfinite(trace)):
            raise RuntimeError("Invalid or incomplete ADC trace")
        if other_errors:
            raise RuntimeError(f"ADC errors: {errors}")

        times = np.arange(SAMPLES) / fs * 1e6
        timing_indices = np.flatnonzero(
            (times >= TIMING_WINDOW_US[0]) & (times <= TIMING_WINDOW_US[1])
        )
        if len(timing_indices) < 2:
            raise RuntimeError("Timing window requires at least two samples")
        segment = trace[timing_indices]
        d = np.abs(np.diff(segment))
        local = int(np.argmax(d))
        landmark = int(timing_indices[local + 1])
        delta = float(d[local])
        print(f"Clean capture OK: {SAMPLES} finite samples")
        print(f"landmark_sample={landmark}, landmark_time_us={times[landmark]:.6f}, "
              f"landmark_amplitude={trace[landmark]:+.8f}, landmark_delta={delta:.8f}")
        if delta < 0.0007:
            print("WARNING: weak landmark: landmark_delta < 0.0007")

        check_safe(scope)
        print("Final prepared glitch settings (before cleanup):")
        print(scope.glitch)
        print(f"glitch_hp={scope.io.glitch_hp}, glitch_lp={scope.io.glitch_lp}, "
              f"hs2={scope.io.hs2}")
        check_safe(scope)
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        exit_code = 130
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        exit_code = 1
    finally:
        if capture_usb_failure:
            print("USB transport failure: Husky state unknown. "
                  "Physically disconnect/reconnect Husky before continuing.",
                  file=sys.stderr)
            # Do not access FPGA registers after a failed USB/FIFO capture.
            if scope is not None:
                try:
                    scope.dis()
                except Exception as exc:
                    print(f"Best-effort disconnect failed: {exc}", file=sys.stderr)
        elif scope is not None:
            try:
                scope.io.hs2 = "disabled"
            except Exception as exc:
                print(f"Cleanup hs2 failed: {exc}", file=sys.stderr)
                exit_code = exit_code or 1
            if cleanup(scope):
                print("Cleanup completed: HP/LP OFF, glitch engine disabled, disconnected")
            else:
                exit_code = exit_code or 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
