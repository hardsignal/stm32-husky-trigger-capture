#!/usr/bin/env python3
"""Estimate relative timing from headerless CSVs: rows=traces, columns=samples.

Requires Python 3.10+ and NumPy. Both inputs need multiple traces and a common
sampling rate/time origin. A single-row or single-column mean file is rejected;
numeric matrices cannot reveal whether their rows were previously averaged.

The reference window is fixed. Candidate windows have identical lengths and
move by integer samples within the requested search radius, with no padding or
wrapping. Positive lag means the candidate feature arrives later. Maximize
signed Pearson correlation; exact ties prefer the smallest absolute lag, then
the negative lag. Constant candidate windows have undefined correlation.

Summaries use accepted matches only and sample standard deviation (ddof=1),
undefined for fewer than two accepted traces. The reference self-match is
included and marked. Threshold selection can exclude poorly matching traces;
reported variation describes that accepted subset at integer-sample resolution.
"""

import argparse
import csv
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR, localcontext
from pathlib import Path

import numpy as np


def number(text):
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError("expected a finite number") from exc
    if not value.is_finite():
        raise argparse.ArgumentTypeError("expected a finite number")
    return value


def read_matrix(source):
    """Parse strictly, including cells outside the correlation window."""
    rows = []
    width = None
    for line, cells in enumerate(csv.reader(source, strict=True), 1):
        if not cells or any(not cell.strip() for cell in cells):
            raise ValueError(f"row {line}: empty row or cell")
        if width is None:
            width = len(cells)
        if len(cells) != width:
            raise ValueError(f"row {line}: expected {width} columns, got {len(cells)}")
        try:
            row = np.asarray(cells, dtype=float)
        except ValueError as exc:
            raise ValueError(f"row {line}: expected numeric amplitudes, no header") from exc
        if not np.isfinite(row).all():
            raise ValueError(f"row {line}: NaN or infinite amplitude")
        rows.append(row)
    if len(rows) < 2 or width is None or width < 2:
        raise ValueError("need at least two trace rows and two sample columns; mean-only vectors are invalid")
    return np.stack(rows)


def indices(rate, start, end, radius):
    if rate <= 0 or start < 0 or end <= start or radius < 0:
        raise ValueError("require rate > 0, 0 <= start < end, and search lag >= 0")
    with localcontext() as ctx:
        ctx.prec = max(28, sum(len(x.as_tuple().digits) for x in (rate, start, end, radius)))
        left = int((start * rate).to_integral_value(rounding=ROUND_CEILING))
        right = int((end * rate).to_integral_value(rounding=ROUND_CEILING))
        limit = int((radius * rate).to_integral_value(rounding=ROUND_FLOOR))
    if right - left < 2:
        raise ValueError("correlation window must contain at least two samples")
    if left < limit:
        raise ValueError("negative search lag would cross the capture start")
    return left, right, limit


def match_trace(trace, template, left, right, limit):
    """Return (lag, Pearson r); template is centered and unit-normalized."""
    region = trace[left - limit:right + limit]
    windows = np.lib.stride_tricks.sliding_window_view(region, right - left)
    # Scale each window before centering to avoid overflow for large inputs.
    scales = np.max(np.abs(windows), axis=1, keepdims=True)
    centered = windows / np.where(scales == 0, 1, scales)
    centered -= centered.mean(axis=1, keepdims=True)
    norms = np.sqrt(np.einsum("ij,ij->i", centered, centered))
    scores = np.full(len(windows), -np.inf)
    valid = norms > 0
    scores[valid] = np.einsum("ij,j->i", centered[valid], template) / norms[valid]
    if not valid.any():
        return None, None
    best = scores.max()
    tied_lags = np.flatnonzero(scores == best) - limit
    lag = min(map(int, tied_lags), key=lambda x: (abs(x), x))
    return lag, float(np.clip(best, -1, 1))


def summarize(lags, total, rate):
    print(f"Accepted traces: {len(lags)}/{total}; total traces: {total}")
    print(f"Low-confidence traces: {total - len(lags)}")
    if not lags:
        print("Lag range, mean lag, lag SD, timing SD, peak-to-peak: undefined")
        return
    values = np.asarray(lags, dtype=float)
    print(f"Lag range (samples): {min(lags):+d} to {max(lags):+d}")
    print(f"Mean lag (samples): {values.mean():+.9f}")
    if len(lags) > 1:
        deviation = values.std(ddof=1)
        print(f"Lag standard deviation (samples, ddof=1): {deviation:.9f}")
        print(f"Timing standard deviation (us): {deviation / rate:.9f}")
    else:
        print("Lag standard deviation (samples, ddof=1): undefined (n < 2)")
        print("Timing standard deviation (us): undefined (n < 2)")
    print(f"Peak-to-peak timing spread (us): {(max(lags) - min(lags)) / rate:.9f}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dataset_a", type=Path)
    parser.add_argument("dataset_b", type=Path)
    parser.add_argument("--sample-rate-mhz", type=number, default=Decimal("40"), help="default: 40")
    parser.add_argument("--start-us", type=number, default=Decimal("145"), help="inclusive; default: 145")
    parser.add_argument("--end-us", type=number, default=Decimal("170"), help="exclusive; default: 170")
    parser.add_argument("--search-lag-us", type=number, default=Decimal("2"), help="symmetric maximum; default: 2")
    parser.add_argument("--threshold", type=number, default=Decimal("0.70"), help="minimum Pearson r; default: 0.70")
    parser.add_argument("--reference-dataset", choices=["a", "b"], default="a")
    parser.add_argument("--reference-index", type=int, default=0, help="zero-based trace row; default: 0")
    args = parser.parse_args(argv)
    try:
        left, right, limit = indices(args.sample_rate_mhz, args.start_us, args.end_us, args.search_lag_us)
        rate = float(args.sample_rate_mhz)
        if not np.isfinite(rate) or rate <= 0:
            raise ValueError("sampling rate exceeds the supported numeric range")
        if not -1 <= args.threshold <= 1:
            raise ValueError("threshold must be between -1 and 1")
        datasets = []
        for path in (args.dataset_a, args.dataset_b):
            try:
                with path.open(encoding="utf-8-sig", newline="") as source:
                    data = read_matrix(source)
                if right + limit > data.shape[1]:
                    raise ValueError(f"window plus lag needs {right + limit} samples; found {data.shape[1]}")
            except (OSError, UnicodeError, csv.Error, ValueError) as exc:
                raise ValueError(f"{path}: {exc}") from exc
            datasets.append(data)
        reference_set = 0 if args.reference_dataset == "a" else 1
        if not 0 <= args.reference_index < len(datasets[reference_set]):
            raise ValueError("reference index is out of range")
        reference = datasets[reference_set][args.reference_index, left:right].copy()
        if np.all(reference == reference[0]):
            raise ValueError("reference window is constant; Pearson correlation is undefined")
        reference /= np.max(np.abs(reference))
        reference -= reference.mean()
        reference /= np.linalg.norm(reference)
        results = [[match_trace(row, reference, left, right, limit) for row in data] for data in datasets]
    except (ValueError, ArithmeticError) as exc:
        parser.error(str(exc))

    print(f"Sampling rate: {args.sample_rate_mhz} MHz")
    print(f"Correlation window: [{args.start_us}, {args.end_us}) us; samples [{left}, {right})")
    print(f"Search: +/-{limit} samples (+/-{limit / rate:g} us); threshold: {args.threshold}")
    print(f"Reference: {args.reference_dataset.upper()} trace {args.reference_index}; positive lag = later candidate")
    print("Accepted-only summaries include reference self-match; SD uses ddof=1.")
    for dataset_index, (path, matches) in enumerate(zip((args.dataset_a, args.dataset_b), results)):
        print(f"\nDataset {'AB'[dataset_index]}: {path}")
        accepted = [lag is not None and score >= float(args.threshold) for lag, score in matches]
        for group, label in ((True, "ACCEPTED"), (False, "LOW_CONFIDENCE")):
            print(label)
            print("trace  lag_samples  lag_us       correlation   notes")
            for index, ((lag, score), passed) in enumerate(zip(matches, accepted)):
                if passed != group:
                    continue
                note = "reference-self" if (dataset_index, index) == (reference_set, args.reference_index) else ""
                if lag is None:
                    print(f"{index:02d}     undefined    undefined    undefined     {note}")
                else:
                    if limit and abs(lag) == limit:
                        note += " search-boundary"
                    print(f"{index:02d}     {lag:+4d}         {lag / rate:+.6f}    {score:.9f}   {note}".rstrip())
        summarize([lag for (lag, _), passed in zip(matches, accepted) if passed], len(matches), rate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
