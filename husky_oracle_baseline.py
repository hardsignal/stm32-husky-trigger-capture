#!/usr/bin/env python3
"""Clean Husky timing baseline; no physical glitch cable may be connected.

Run after review: ~/cw-env/bin/python ~/cw_nucleo_trigger/husky_oracle_baseline.py
The NUCLEO firmware must already generate rising PA0/TIO4 triggers.
Landmark = strongest sample-to-sample transition in 158.5–159.5 us, timestamped
at its later sample; amplitude retains its sign. Plot window is 145–170 us.
Times are relative to the capture trigger, with zero offset/presamples.
"""

import csv
from datetime import datetime
from pathlib import Path
import sys
import time

import chipwhisperer as cw
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COUNT = 10
SAMPLES = 8000
WINDOW_US = (145.0, 170.0)
TIMING_WINDOW_US = (158.5, 159.5)


def drivers_off(scope):
    scope.io.glitch_hp = False
    scope.io.glitch_lp = False
    if scope.io.glitch_hp or scope.io.glitch_lp:
        raise RuntimeError("Crowbar OFF readback failed")


def wait_locked(predicate, label, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            raise RuntimeError(f"{label} did not lock within {timeout:g} s")
        time.sleep(0.05)


def preflight(scope):
    if scope.io.glitch_hp or scope.io.glitch_lp:
        drivers_off(scope)
        raise RuntimeError("Unexpected crowbar state; outputs disabled, aborting")
    if scope.io.hs2 == "glitch":
        raise RuntimeError("Unexpected HS2 glitch routing")
    if not scope.clock.pll.pll_locked or not scope.glitch.mmcm_locked:
        raise RuntimeError("Clock PLL or glitch MMCM lost lock")


def configure(scope):
    drivers_off(scope)
    scope.glitch.enabled = False
    scope.io.hs2 = "disabled"
    scope.io.tio4 = "high_z"
    scope.clock.clkgen_src = "system"
    scope.clock.clkgen_freq = 10e6
    scope.clock.adc_mul = 4
    wait_locked(lambda: scope.clock.pll.pll_locked, "Clock PLL")
    fs = float(scope.clock.adc_freq)
    if not np.isfinite(fs) or not np.isclose(fs, 40e6, rtol=1e-6):
        raise RuntimeError(f"Expected 40 MHz ADC clock; got {fs} Hz")

    scope.trigger.module = "basic"
    scope.trigger.triggers = "tio4"
    scope.adc.basic_mode = "rising_edge"
    scope.adc.samples = SAMPLES
    scope.adc.offset = 0
    scope.adc.presamples = 0
    scope.adc.decimate = 1
    scope.adc.segments = 1
    scope.adc.stream_mode = False
    scope.adc.test_mode = False
    scope.ADS4128.mode = "normal"
    scope.adc.timeout = 3.0

    # Configure only the internal timing engine. Never route it to HS2/crowbars.
    scope.glitch.enabled = True
    scope.glitch.clk_src = "pll"
    wait_locked(lambda: scope.glitch.mmcm_locked, "Glitch MMCM")
    scope.glitch.trigger_src = "ext_single"
    scope.glitch.output = "glitch_only"
    scope.glitch.num_glitches = 1
    scope.glitch.ext_offset = 1590
    scope.glitch.repeat = 1
    drivers_off(scope)
    preflight(scope)
    print(f"PLL/MMCM locked; ADC {fs / 1e6:.6f} MHz; HP/LP OFF")
    print(f"ADC gain: {scope.gain.db} dB (not changed by this script)")
    return fs


def cleanup(scope):
    # Separate attempts ensure one USB failure does not skip other cleanup.
    ok = True
    for obj, attr, value in (
        (scope.io, "glitch_hp", False),
        (scope.io, "glitch_lp", False),
        (scope.glitch, "enabled", False),
    ):
        try:
            setattr(obj, attr, value)
        except Exception as exc:
            ok = False
            print(f"Cleanup {attr} failed: {exc}", file=sys.stderr)
    try:
        scope.dis()
    except Exception as exc:
        ok = False
        print(f"Disconnect failed: {exc}", file=sys.stderr)
    return ok


def main():
    # Unique directory preserves earlier runs and any partial results.
    out = Path(__file__).resolve().parent / (
        "husky_baseline_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    )
    out.mkdir()
    fields = ["capture", "status", "landmark_sample", "landmark_time_us",
              "landmark_amplitude", "landmark_delta", "adc_freq_hz", "error", "warning"]
    rows = []
    traces = []
    scope = None
    fs = None
    exit_code = 0
    try:
        with (out / "results.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            handle.flush()
            try:
                scope = cw.scope(name="Husky")
                fs = configure(scope)
                times = np.arange(SAMPLES) / fs * 1e6
                indices = np.flatnonzero(
                    (times >= WINDOW_US[0]) & (times <= WINDOW_US[1])
                )
                if not len(indices):
                    raise RuntimeError("Plot window is outside the trace")
                timing_indices = np.flatnonzero(
                    (times >= TIMING_WINDOW_US[0]) & (times <= TIMING_WINDOW_US[1])
                )
                if len(timing_indices) < 2:
                    raise RuntimeError("Timing window requires at least two samples")
                print(f"Timing search samples {timing_indices[0]}–"
                      f"{timing_indices[-1]} (zero-based)")
                for number in range(1, COUNT + 1):
                    row = dict.fromkeys(fields, "")
                    row.update(capture=number, status="FAIL", adc_freq_hz=fs)
                    fatal = False
                    try:
                        preflight(scope)
                        scope.adc.errors = 0
                        scope.arm()
                        if scope.capture():
                            row["error"] = "Capture timeout"
                        else:
                            preflight(scope)
                            trace = np.asarray(scope.get_last_trace(), dtype=float)
                            errors = scope.adc.errors
                            # Husky returns comma-separated flags with a trailing comma.
                            error_flags = [flag.strip() for flag in str(errors).split(",")
                                           if flag.strip()] if errors else []
                            if "gain too low error" in error_flags:
                                row["warning"] = "gain too low error"
                            other_errors = [flag for flag in error_flags
                                            if flag != "gain too low error"]
                            if trace.shape != (SAMPLES,) or not np.all(np.isfinite(trace)):
                                raise RuntimeError("Invalid or incomplete ADC trace")
                            if other_errors:
                                row["error"] = f"ADC errors: {errors}"
                            else:
                                segment = trace[timing_indices]
                                d = np.abs(np.diff(segment))
                                local = int(np.argmax(d))
                                landmark = int(timing_indices[local + 1])
                                row.update(status="OK", landmark_sample=landmark,
                                           landmark_time_us=float(times[landmark]),
                                           landmark_amplitude=float(trace[landmark]),
                                           landmark_delta=float(d[local]))
                                if row["landmark_delta"] < 0.0007:
                                    warning = "weak landmark: landmark_delta < 0.0007"
                                    row["warning"] = "; ".join(
                                        filter(None, (row["warning"], warning))
                                    )
                                    print(f"{number:02d}: WARNING  {warning}")
                                traces.append((number, trace.copy()))
                    except Exception as exc:
                        row["error"] = f"{type(exc).__name__}: {exc}"
                        fatal = True  # Do not reconnect/retry after USB or safety errors.
                    except KeyboardInterrupt:
                        row["error"] = "Interrupted by user"
                        fatal = True
                        exit_code = 130
                    rows.append(row)
                    writer.writerow(row)
                    handle.flush()
                    if row["status"] == "OK":
                        print(f"{number:02d}: OK  landmark_sample={row['landmark_sample']}  "
                              f"landmark_time_us={row['landmark_time_us']:.6f}  "
                              f"landmark_amplitude={row['landmark_amplitude']:+.8f}  "
                              f"landmark_delta={row['landmark_delta']:.8f}")
                    else:
                        print(f"{number:02d}: FAIL  landmark=N/A  {row['error']}")
                        exit_code = exit_code or 1
                    if fatal:
                        break
            finally:
                if scope is not None and not cleanup(scope):
                    exit_code = exit_code or 1
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        exit_code = 130
    except Exception as exc:
        print(f"Stopped: {type(exc).__name__}: {exc}", file=sys.stderr)
        exit_code = exit_code or 1

    landmarks = np.array([r["landmark_time_us"] for r in rows if r["status"] == "OK"])
    print(f"\nValid captures: {len(landmarks)}/{COUNT}; attempted: {len(rows)}")
    if len(landmarks):
        print(f"Landmark timing (us): mean={landmarks.mean():.6f}, min={landmarks.min():.6f}, "
              f"max={landmarks.max():.6f}, std={landmarks.std(ddof=0):.6f} (population)")
    else:
        print("Landmark timing statistics: N/A (no valid captures)")
    try:
        fig, ax = plt.subplots(figsize=(10, 5))
        if traces:
            for number, trace in traces:
                ax.plot(times[indices], trace[indices], alpha=0.7,
                        linewidth=0.9, label=f"Capture {number}")
            ax.legend(fontsize=8, ncol=2)
        else:
            ax.text(0.5, 0.5, "No valid captures", transform=ax.transAxes, ha="center")
        ax.set(xlim=WINDOW_US, xlabel="Time from trigger (us)",
               ylabel="ADC amplitude (normalized units)",
               title=f"Husky clean baseline: {len(traces)}/{COUNT} valid traces")
        ax.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(out / "overlay.png", dpi=180)
        plt.close(fig)
    except Exception as exc:
        print(f"Plot save failed: {exc}", file=sys.stderr)
        exit_code = exit_code or 1
    print(f"Results directory: {out}")
    return exit_code if len(landmarks) == COUNT else (exit_code or 1)


if __name__ == "__main__":
    sys.exit(main())
