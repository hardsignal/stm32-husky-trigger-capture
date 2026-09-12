#!/usr/bin/env python3
"""Estimate capture-to-capture timing jitter in two ChipWhisperer CSV datasets.

The CSV files must be headerless numeric matrices with one trace per row and
one sample per column. By default, every trace is compared with trace 0 from
dataset A. A positive lag means the candidate trace occurs later than the
reference. Correlations use shifted, fixed-length slices and never wrap data
across a capture boundary.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np


DEFAULT_SAMPLE_RATE_MHZ = 40.0
DEFAULT_WINDOW_START_US = 145.0
DEFAULT_WINDOW_END_US = 170.0
DEFAULT_SEARCH_LAG_US = 2.0
DEFAULT_THRESHOLD = 0.70


@dataclass(frozen=True)
class Match:
    dataset: str
    trace_index: int
    lag_samples: int | None
    correlation: float
    accepted: bool


def finite_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected a number, got {text!r}") from exc
    if not math.isfinite(value):
        raise argparse.ArgumentTypeError("value must be finite")
    return value


def positive_float(text: str) -> float:
    value = finite_float(text)
    if value <= 0.0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return value


def nonnegative_float(text: str) -> float:
    value = finite_float(text)
    if value < 0.0:
        raise argparse.ArgumentTypeError("value must be nonnegative")
    return value


def threshold_float(text: str) -> float:
    value = finite_float(text)
    if not -1.0 <= value <= 1.0:
        raise argparse.ArgumentTypeError("threshold must be between -1 and 1")
    return value


def nonnegative_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a nonnegative integer") from exc
    if value < 0:
        raise argparse.ArgumentTypeError("expected a nonnegative integer")
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Estimate trace timing jitter by finding each trace's best "
            "correlation lag against a reference trace."
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
        type=nonnegative_float,
        default=DEFAULT_WINDOW_START_US,
        help=f"correlation-window start in us (default: {DEFAULT_WINDOW_START_US:g})",
    )
    parser.add_argument(
        "--end-us",
        type=positive_float,
        default=DEFAULT_WINDOW_END_US,
        help=f"correlation-window end in us, exclusive (default: {DEFAULT_WINDOW_END_US:g})",
    )
    parser.add_argument(
        "--search-lag-us",
        type=nonnegative_float,
        default=DEFAULT_SEARCH_LAG_US,
        help=f"maximum lag searched in either direction, in us (default: {DEFAULT_SEARCH_LAG_US:g})",
    )
    parser.add_argument(
        "--threshold",
        type=threshold_float,
        default=DEFAULT_THRESHOLD,
        help=f"minimum accepted Pearson correlation (default: {DEFAULT_THRESHOLD:.2f})",
    )
    parser.add_argument(
        "--reference-dataset",
        choices=("a", "b"),
        default="a",
        help="dataset containing the reference trace (default: a)",
    )
    parser.add_argument(
        "--reference-index",
        type=nonnegative_int,
        default=0,
        help="zero-based reference-trace row (default: 0)",
    )
    return parser.parse_args(argv)


def time_to_sample(time_us: float, sample_rate_hz: float) -> int:
    """Map a time boundary to the first sample at or after that time."""
    exact = time_us * 1e-6 * sample_rate_hz
    nearest = round(exact)
    if math.isclose(exact, nearest, rel_tol=0.0, abs_tol=1e-9):
        return int(nearest)
    return math.ceil(exact)


def load_traces(path: Path) -> np.ndarray:
    if not path.is_file():
        raise ValueError(f"file does not exist or is not a regular file: {path}")
    try:
        traces = np.loadtxt(path, delimiter=",", dtype=np.float64)
    except (OSError, ValueError) as exc:
        raise ValueError(f"could not read numeric CSV {path}: {exc}") from exc

    if traces.ndim != 2:
        raise ValueError(
            f"{path} must contain at least two trace rows and two sample columns; "
            "single-trace and mean-only inputs are invalid"
        )
    if traces.shape[0] < 2:
        raise ValueError(f"{path} contains fewer than two traces")
    if traces.shape[1] < 2:
        raise ValueError(f"{path} contains fewer than two samples per trace")
    if not np.isfinite(traces).all():
        raise ValueError(f"{path} contains NaN or infinite values")
    return traces


def pearson_correlation(reference: np.ndarray, candidate: np.ndarray) -> float:
    reference_centered = reference - np.mean(reference)
    candidate_centered = candidate - np.mean(candidate)
    denominator = float(
        np.linalg.norm(reference_centered) * np.linalg.norm(candidate_centered)
    )
    if denominator == 0.0:
        return math.nan
    value = float(np.dot(reference_centered, candidate_centered) / denominator)
    return max(-1.0, min(1.0, value))


def find_best_match(
    reference_window: np.ndarray,
    candidate: np.ndarray,
    start_sample: int,
    end_sample: int,
    max_lag_samples: int,
) -> tuple[int | None, float]:
    best_lag: int | None = None
    best_correlation = -math.inf

    for lag in range(-max_lag_samples, max_lag_samples + 1):
        shifted = candidate[start_sample + lag : end_sample + lag]
        correlation = pearson_correlation(reference_window, shifted)
        if math.isnan(correlation):
            continue
        if (
            correlation > best_correlation
            or (
                correlation == best_correlation
                and best_lag is not None
                and (abs(lag), lag) < (abs(best_lag), best_lag)
            )
        ):
            best_lag = lag
            best_correlation = correlation

    if best_lag is None:
        return None, math.nan
    return best_lag, best_correlation


def analyze_dataset(
    label: str,
    traces: np.ndarray,
    reference_window: np.ndarray,
    start_sample: int,
    end_sample: int,
    max_lag_samples: int,
    threshold: float,
) -> list[Match]:
    matches = []
    for trace_index, trace in enumerate(traces):
        lag, correlation = find_best_match(
            reference_window,
            trace,
            start_sample,
            end_sample,
            max_lag_samples,
        )
        matches.append(
            Match(
                dataset=label,
                trace_index=trace_index,
                lag_samples=lag,
                correlation=correlation,
                accepted=lag is not None and correlation >= threshold,
            )
        )
    return matches


def print_matches(matches: list[Match], sample_rate_mhz: float) -> None:
    print(f"Dataset {matches[0].dataset} trace matches")
    for match in matches:
        status = "ACCEPTED" if match.accepted else "LOW_CONFIDENCE"
        if match.lag_samples is None:
            print(
                f"  trace {match.trace_index:03d}: lag=undefined, "
                f"correlation=undefined, status={status}"
            )
            continue
        lag_us = match.lag_samples / sample_rate_mhz
        print(
            f"  trace {match.trace_index:03d}: lag={match.lag_samples:+d} samples "
            f"({lag_us:+.6f} us), correlation={match.correlation:.9f}, "
            f"status={status}"
        )


def print_summary(
    title: str,
    matches: list[Match],
    sample_rate_mhz: float,
) -> None:
    accepted_lags = np.asarray(
        [match.lag_samples for match in matches if match.accepted], dtype=np.float64
    )
    print(title)
    print(f"  Accepted traces: {accepted_lags.size}/{len(matches)}")
    print(f"  Low-confidence traces: {len(matches) - accepted_lags.size}/{len(matches)}")
    if accepted_lags.size == 0:
        print("  Lag range: undefined")
        print("  Mean lag: undefined")
        print("  Lag standard deviation: undefined")
        print("  Timing standard deviation: undefined")
        print("  Peak-to-peak timing spread: undefined")
        return

    minimum = int(np.min(accepted_lags))
    maximum = int(np.max(accepted_lags))
    mean = float(np.mean(accepted_lags))
    standard_deviation = (
        float(np.std(accepted_lags, ddof=1)) if accepted_lags.size > 1 else 0.0
    )
    peak_to_peak = maximum - minimum
    print(f"  Lag range: {minimum:+d} to {maximum:+d} samples")
    print(f"  Mean lag: {mean:+.6f} samples")
    print(f"  Lag standard deviation: {standard_deviation:.6f} samples")
    print(
        f"  Timing standard deviation: "
        f"{standard_deviation / sample_rate_mhz:.9f} us"
    )
    print(
        f"  Peak-to-peak timing spread: {peak_to_peak} samples "
        f"({peak_to_peak / sample_rate_mhz:.9f} us)"
    )


def run(args: argparse.Namespace) -> None:
    if args.end_us <= args.start_us:
        raise ValueError("--end-us must be greater than --start-us")

    sample_rate_hz = args.sample_rate_mhz * 1e6
    start_sample = time_to_sample(args.start_us, sample_rate_hz)
    end_sample = time_to_sample(args.end_us, sample_rate_hz)
    max_lag_samples = int(round(args.search_lag_us * args.sample_rate_mhz))
    if end_sample - start_sample < 2:
        raise ValueError("correlation window must contain at least two samples")

    traces_a = load_traces(args.dataset_a)
    traces_b = load_traces(args.dataset_b)
    for path, traces in ((args.dataset_a, traces_a), (args.dataset_b, traces_b)):
        if start_sample - max_lag_samples < 0:
            raise ValueError(
                f"correlation window plus negative search lag begins before {path}"
            )
        if end_sample + max_lag_samples > traces.shape[1]:
            raise ValueError(
                f"correlation window plus positive search lag ends at sample "
                f"{end_sample + max_lag_samples}, but {path} has only "
                f"{traces.shape[1]} samples per trace"
            )

    reference_traces = traces_a if args.reference_dataset == "a" else traces_b
    if args.reference_index >= reference_traces.shape[0]:
        raise ValueError(
            f"reference index {args.reference_index} is out of range for dataset "
            f"{args.reference_dataset.upper()} ({reference_traces.shape[0]} traces)"
        )
    reference_window = reference_traces[
        args.reference_index, start_sample:end_sample
    ]
    if np.ptp(reference_window) == 0.0:
        raise ValueError("the selected reference window is constant")

    matches_a = analyze_dataset(
        "A",
        traces_a,
        reference_window,
        start_sample,
        end_sample,
        max_lag_samples,
        args.threshold,
    )
    matches_b = analyze_dataset(
        "B",
        traces_b,
        reference_window,
        start_sample,
        end_sample,
        max_lag_samples,
        args.threshold,
    )

    print("ChipWhisperer capture timing analysis")
    print(f"Dataset A: {args.dataset_a} ({traces_a.shape[0]} traces)")
    print(f"Dataset B: {args.dataset_b} ({traces_b.shape[0]} traces)")
    print(
        f"Reference: dataset {args.reference_dataset.upper()}, "
        f"trace {args.reference_index}"
    )
    print(f"Sample rate: {args.sample_rate_mhz:g} MHz")
    print(
        f"Correlation window: {args.start_us:g}-{args.end_us:g} us "
        f"(samples {start_sample}:{end_sample})"
    )
    print(
        f"Search lag: +/-{args.search_lag_us:g} us "
        f"(+/-{max_lag_samples} samples)"
    )
    print(f"Acceptance threshold: {args.threshold:.6f}")
    print("Positive lag means the candidate trace occurs later than the reference.")
    print()
    print_matches(matches_a, args.sample_rate_mhz)
    print()
    print_matches(matches_b, args.sample_rate_mhz)
    print()
    print_summary("Dataset A summary", matches_a, args.sample_rate_mhz)
    print()
    print_summary("Dataset B summary", matches_b, args.sample_rate_mhz)
    print()
    print_summary(
        "Combined summary", matches_a + matches_b, args.sample_rate_mhz
    )


def main(argv: list[str] | None = None) -> int:
    try:
        run(parse_args(argv))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
