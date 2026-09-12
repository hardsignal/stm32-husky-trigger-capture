#!/usr/bin/env python3
"""Compare headerless CSV trace matrices using only the Python standard library.

Rows are repeated traces; columns are successive amplitude samples, starting
at time zero. At least two rows and two columns are required. Time/index
columns, headers, single traces, and mean-only vectors are not supported.
Inputs must already share a sampling rate and timing reference: no alignment,
resampling, centering of individual traces, or amplitude normalization occurs.

Noise is sqrt(mean population variance across the selected sample positions)),
equivalently the RMS residual from each dataset's own mean waveform (ddof=0).
Noise and waveform difference retain the CSV amplitude units.

Example:
    python3 compare_trace_csv_astra.py run_a.csv run_b.csv \
        --sample-rate-mhz 40 --start-us 10 --end-us 145
"""

import argparse
import csv
from decimal import Decimal, InvalidOperation, ROUND_CEILING, localcontext
import math
from pathlib import Path


def decimal_argument(text):
    try:
        value = Decimal(text)
    except InvalidOperation as error:
        raise argparse.ArgumentTypeError("expected a finite number") from error
    if not value.is_finite():
        raise argparse.ArgumentTypeError("expected a finite number")
    return value


def sample_bounds(rate, start, end):
    """Convert MHz and microseconds to indices for start <= sample time < end."""
    if rate <= 0 or start < 0 or end <= start:
        raise ValueError("require sample rate > 0 and 0 <= start < end")
    # Decimal avoids moving an exact sample boundary due to binary rounding.
    with localcontext() as context:
        context.prec = max(28, sum(len(x.as_tuple().digits) for x in (rate, start, end)))
        first, stop = (
            int((time * rate).to_integral_value(rounding=ROUND_CEILING))
            for time in (start, end)
        )
    if stop - first < 2:
        raise ValueError("window must contain at least two samples for correlation")
    return first, stop


def summarize(rows, first, stop):
    """Validate all CSV cells and accumulate window means and population noise.

    Welford's online algorithm keeps memory proportional to one trace rather
    than the entire capture. `rows` may be any iterable of CSV row lists.
    """
    count = 0
    width = None
    average = []
    squared_deviations = []
    for line, row in enumerate(rows, 1):
        if not row:
            raise ValueError(f"row {line}: blank rows are not allowed")
        if width is None:
            width = len(row)
            if width < 2:
                raise ValueError("single-column/mean-only input is not a trace matrix")
            if stop > width:
                raise ValueError(f"window needs {stop} samples; each trace has {width}")
            average = [0.0] * (stop - first)
            squared_deviations = [0.0] * (stop - first)
        if len(row) != width:
            raise ValueError(f"row {line}: expected {width} columns, got {len(row)}")
        count += 1
        for column, cell in enumerate(row):
            try:
                amplitude = float(cell)
            except ValueError as error:
                raise ValueError(f"row {line}, column {column + 1}: nonnumeric cell") from error
            if not math.isfinite(amplitude):
                raise ValueError(f"row {line}, column {column + 1}: nonfinite value")
            if first <= column < stop:
                index = column - first
                delta = amplitude - average[index]
                average[index] += delta / count
                squared_deviations[index] += delta * (amplitude - average[index])
    if count < 2:
        raise ValueError("need at least two trace rows; empty or mean-only input is invalid")
    noise = math.sqrt(math.fsum(squared_deviations) / count / len(average))
    if not math.isfinite(noise) or not all(map(math.isfinite, average)):
        raise ValueError("amplitudes exceed the supported numeric range")
    return count, width, average, noise


def compare(means_a, means_b, noise_a, noise_b):
    length = len(means_a)
    offset_a = math.fsum(means_a) / length
    offset_b = math.fsum(means_b) / length
    centered_a = [x - offset_a for x in means_a]
    centered_b = [x - offset_b for x in means_b]
    norm_a, norm_b = math.hypot(*centered_a), math.hypot(*centered_b)
    correlation = None
    if norm_a and norm_b:
        correlation = max(-1.0, min(1.0, math.fsum(
            (a / norm_a) * (b / norm_b) for a, b in zip(centered_a, centered_b)
        )))
    difference = math.hypot(*(b - a for a, b in zip(means_a, means_b))) / math.sqrt(length)
    change = 100 * (noise_b / noise_a - 1) if noise_a else None
    for value in (correlation, difference, change):
        if value is not None and not math.isfinite(value):
            raise ValueError("comparison exceeds the supported numeric range")
    return correlation, difference, change


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dataset_a", type=Path)
    parser.add_argument("dataset_b", type=Path)
    parser.add_argument("--sample-rate-mhz", type=decimal_argument, default=Decimal("40"), help="MHz (default: 40)")
    parser.add_argument("--start-us", type=decimal_argument, default=Decimal("10"), help="inclusive start, us (default: 10)")
    parser.add_argument("--end-us", type=decimal_argument, default=Decimal("145"), help="exclusive end, us (default: 145)")
    args = parser.parse_args(argv)
    try:
        first, stop = sample_bounds(args.sample_rate_mhz, args.start_us, args.end_us)
        results = []
        for path in (args.dataset_a, args.dataset_b):
            try:
                with path.open("r", encoding="utf-8-sig", newline="") as source:
                    results.append(summarize(csv.reader(source, strict=True), first, stop))
            except (OSError, UnicodeError, csv.Error, ValueError) as error:
                raise ValueError(f"{path}: {error}") from error
        a, b = results
        correlation, difference, change = compare(a[2], b[2], a[3], b[3])
    except (ValueError, ArithmeticError) as error:
        parser.error(str(error))

    print(f"Dataset A: {args.dataset_a} ({a[0]} traces, {a[1]} samples/trace)")
    print(f"Dataset B: {args.dataset_b} ({b[0]} traces, {b[1]} samples/trace)")
    print(f"Sampling rate: {args.sample_rate_mhz} MHz")
    print(f"Window: [{args.start_us}, {args.end_us}) us; samples [{first}, {stop}); {stop - first} samples")
    print(f"Within-run RMS residual noise A: {a[3]:.12g}")
    print(f"Within-run RMS residual noise B: {b[3]:.12g}")
    print("Mean-waveform Pearson correlation: " + (
        f"{correlation:.12g}" if correlation is not None else "undefined (constant mean waveform)"
    ))
    print(f"Mean-waveform RMS difference: {difference:.12g}")
    print("Noise change B relative to A: " + (
        f"{change:.12g}%" if change is not None else "undefined (zero noise in A)"
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
