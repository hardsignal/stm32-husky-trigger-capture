#!/usr/bin/env python3
"""Compare two ChipWhisperer trace sets stored as numeric CSV files.

Each CSV is expected to contain one trace per row and one sample per column.
The selected time window is half-open: start <= time < end.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np


DEFAULT_SAMPLE_RATE_MHZ = 40.0
DEFAULT_START_US = 10.0
DEFAULT_END_US = 145.0


def positive_float(value: str) -> float:
    """Parse a finite, positive command-line number."""
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected a number, got {value!r}") from exc
    if not math.isfinite(parsed) or parsed <= 0.0:
        raise argparse.ArgumentTypeError("value must be finite and greater than zero")
    return parsed


def finite_float(value: str) -> float:
    """Parse a finite command-line number."""
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected a number, got {value!r}") from exc
    if not math.isfinite(parsed):
        raise argparse.ArgumentTypeError("value must be finite")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two numeric ChipWhisperer CSV trace sets. Each row must be "
            "one trace and each column one sample."
        )
    )
    parser.add_argument("dataset_a", type=Path, help="first trace CSV")
    parser.add_argument("dataset_b", type=Path, help="second trace CSV")
    parser.add_argument(
        "--sample-rate-mhz",
        type=positive_float,
        default=DEFAULT_SAMPLE_RATE_MHZ,
        help=f"sampling rate in MHz (default: {DEFAULT_SAMPLE_RATE_MHZ:g})",
    )
    parser.add_argument(
        "--start-us",
        type=finite_float,
        default=DEFAULT_START_US,
        help=f"analysis-window start in microseconds (default: {DEFAULT_START_US:g})",
    )
    parser.add_argument(
        "--end-us",
        type=finite_float,
        default=DEFAULT_END_US,
        help=f"analysis-window end in microseconds, exclusive (default: {DEFAULT_END_US:g})",
    )
    return parser.parse_args(argv)


def load_trace_set(path: Path) -> np.ndarray:
    """Load and validate a headerless CSV containing one trace per row."""
    if not path.is_file():
        raise ValueError(f"file does not exist or is not a regular file: {path}")

    try:
        traces = np.loadtxt(path, delimiter=",", dtype=np.float64)
    except (OSError, ValueError) as exc:
        raise ValueError(f"could not read numeric CSV {path}: {exc}") from exc

    if traces.ndim != 2:
        raise ValueError(
            f"{path} must have at least two trace rows and two sample columns; "
            "single-trace and mean-only CSV files cannot provide within-run noise"
        )
    if traces.shape[0] < 2:
        raise ValueError(f"{path} contains fewer than two traces")
    if traces.shape[1] < 2:
        raise ValueError(f"{path} contains fewer than two samples per trace")
    if not np.isfinite(traces).all():
        raise ValueError(f"{path} contains NaN or infinite values")
    return traces


def boundary_to_sample(time_us: float, sample_rate_hz: float) -> int:
    """Return the first sample whose timestamp is at least time_us."""
    exact_index = time_us * 1e-6 * sample_rate_hz
    nearest_integer = round(exact_index)
    if math.isclose(exact_index, nearest_integer, rel_tol=0.0, abs_tol=1e-9):
        return int(nearest_integer)
    return math.ceil(exact_index)


def select_window(
    traces: np.ndarray,
    path: Path,
    start_sample: int,
    end_sample: int,
) -> np.ndarray:
    if start_sample < 0:
        raise ValueError("analysis-window start must not precede the capture")
    if end_sample > traces.shape[1]:
        raise ValueError(
            f"analysis window ends at sample {end_sample}, but {path} has only "
            f"{traces.shape[1]} samples per trace"
        )
    return traces[:, start_sample:end_sample]


def within_run_noise(traces: np.ndarray, mean_waveform: np.ndarray) -> float:
    """Return RMS residual from the mean waveform across traces and samples."""
    residuals = traces - mean_waveform
    return float(np.sqrt(np.mean(np.square(residuals))))


def mean_waveform_correlation(mean_a: np.ndarray, mean_b: np.ndarray) -> float:
    centered_a = mean_a - np.mean(mean_a)
    centered_b = mean_b - np.mean(mean_b)
    denominator = float(np.linalg.norm(centered_a) * np.linalg.norm(centered_b))
    if denominator == 0.0:
        return math.nan
    return float(np.dot(centered_a, centered_b) / denominator)


def format_metric(value: float, suffix: str = "") -> str:
    if math.isnan(value):
        return "undefined"
    return f"{value:.9g}{suffix}"


def run(args: argparse.Namespace) -> None:
    if args.end_us <= args.start_us:
        raise ValueError("--end-us must be greater than --start-us")

    sample_rate_hz = args.sample_rate_mhz * 1e6
    start_sample = boundary_to_sample(args.start_us, sample_rate_hz)
    end_sample = boundary_to_sample(args.end_us, sample_rate_hz)
    if end_sample <= start_sample:
        raise ValueError("analysis window contains no samples at this sampling rate")

    traces_a = load_trace_set(args.dataset_a)
    traces_b = load_trace_set(args.dataset_b)
    window_a = select_window(traces_a, args.dataset_a, start_sample, end_sample)
    window_b = select_window(traces_b, args.dataset_b, start_sample, end_sample)

    mean_a = np.mean(window_a, axis=0)
    mean_b = np.mean(window_b, axis=0)
    noise_a = within_run_noise(window_a, mean_a)
    noise_b = within_run_noise(window_b, mean_b)
    correlation = mean_waveform_correlation(mean_a, mean_b)
    rms_difference = float(np.sqrt(np.mean(np.square(mean_b - mean_a))))
    noise_change = math.nan if noise_a == 0.0 else (noise_b - noise_a) / noise_a * 100.0

    print("ChipWhisperer trace comparison")
    print(f"Dataset A: {args.dataset_a} ({traces_a.shape[0]} traces)")
    print(f"Dataset B: {args.dataset_b} ({traces_b.shape[0]} traces)")
    print(f"Sampling rate: {args.sample_rate_mhz:g} MHz")
    print(
        f"Analysis window: {args.start_us:g}-{args.end_us:g} us "
        f"(samples {start_sample}:{end_sample}, {end_sample - start_sample} samples)"
    )
    print()
    print(f"Within-run noise A (RMS residual): {format_metric(noise_a)}")
    print(f"Within-run noise B (RMS residual): {format_metric(noise_b)}")
    print(f"Mean-waveform correlation: {format_metric(correlation)}")
    print(f"Mean-waveform RMS difference: {format_metric(rms_difference)}")
    print(f"Noise change (B relative to A): {format_metric(noise_change, '%')}")
    if math.isnan(correlation):
        print("Note: correlation is undefined because a mean waveform is constant.")
    if math.isnan(noise_change):
        print("Note: noise change is undefined because dataset A has zero within-run noise.")


def main(argv: list[str] | None = None) -> int:
    try:
        run(parse_args(argv))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
