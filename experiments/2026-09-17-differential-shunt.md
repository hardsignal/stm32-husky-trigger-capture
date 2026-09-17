# Differential-shunt measurements — 2026-09-17

Experiment date: 17 September 2026 (Europe/London). This note records the operator-reported configuration and independently reproduced CSV statistics. It does not change acquisition settings or prescribe hardware changes.

## Reported physical configuration

The user reported the following differential measurement configuration:

| Connection | Reported location/state |
| --- | --- |
| Husky MEASURE POS | Breadboard row 30 |
| Husky MEASURE NEG | Breadboard row 35 |
| Both measurement shields/grounds | Row 25, common GND |
| NEG shorting cap | Removed for differential mode |

These are user-reported physical observations, not independently verified wiring facts. The CSVs cannot establish wiring, shorting-cap state, gain, firmware identity at capture time, or the actual sampling clock. Dataset names and the user's experiment description identify the intended control/workload conditions.

## Analysis method and assumptions

All eight differential datasets below were read successfully as finite numeric matrices of 20 traces × 8,000 samples, with one trace per row. Analysis uses 40 MHz sampling, sample zero as time zero, and the half-open 10–145 µs window: columns `[400:5800]`, or 5,400 samples. Sampling rate and time origin are analysis assumptions consistent with the existing comparison script; these headerless CSVs contain no acquisition metadata to independently confirm them.

No alignment, filtering, baseline subtraction, normalization, or trace rejection is applied. Amplitude statistics retain the CSV's amplitude units; no conversion to volts or current is asserted.

For a windowed dataset `X`, the mean waveform is `mean(X, axis=0)`. Within-run noise is `sqrt(mean((X - mean(X, axis=0))**2))`, the RMS residual across traces and samples (population convention, `ddof=0`). It can include timing variation and drift as well as measurement noise. Mean-waveform correlation is Pearson correlation; waveform RMS difference is `sqrt(mean((mean_B - mean_A)**2))`. Percentage noise change is `100 * (noise_B - noise_A) / noise_A`.

For each control/workload pair, define `D_i = mean(workload_i) - mean(control_i)` over the same window. Difference-waveform correlations compare the signed `D_i` waveforms. The combined difference is `(D_1 + D_2 + D_3) / 3`; its RMS is taken after averaging the waveforms, not by averaging their RMS values. With 20 traces per condition per pair, this also equals the difference of the pooled 60-trace workload and control means.

## Repeated differential workload captures

| Role | CSV |
| --- | --- |
| A | `workload50_differential_shunt_20traces.csv` |
| B | `workload50_differential_shunt_repeat_20traces.csv` |

| Metric | Reproduced value |
| --- | ---: |
| Within-run RMS residual noise A | 0.000182347819 |
| Within-run RMS residual noise B | 0.000180275760 |
| Mean-waveform Pearson correlation | 0.793353323 |
| Mean-waveform RMS difference | 0.000178248899 |
| Noise change, B relative to A | -1.13632204% |

For context, the following earlier comparisons were rerun with exactly the same analysis window and formulas:

| Repeat pair | Noise A | Noise B | Mean correlation | Mean RMS difference |
| --- | ---: | ---: | ---: | ---: |
| Direct shunt red | 0.000189307475 | 0.000195536450 | 0.124636816 | 0.000210380890 |
| 18 cm grabbers | 0.000192879535 | 0.000194673482 | -0.0358838663 | 0.000154308424 |

The direct-shunt-red pair is `workload50_direct_shunt_red_20traces.csv` and `workload50_direct_shunt_red_repeat_20traces.csv`. The grabber pair is `workload50_18cm_grabbers_20traces.csv` and `workload50_18cm_grabbers_repeat_20traces.csv`. Their earlier single-ended configuration is based on the experiment history supplied by the user, rather than metadata inside the files.

The differential repeats show lower observed within-run noise and materially stronger waveform-shape correlation than these earlier single-ended repeats. This supports improved measurement stability in those respects. It is not an improvement in every metric: differential repeat RMS difference is lower than the direct-shunt-red pair's, but higher than the older grabber pair's. Pearson correlation removes waveform means, whereas RMS difference retains offsets and amplitude differences; a higher correlation alone does not establish closer absolute waveform agreement. These comparisons also do not isolate configuration changes from other changes between captures.

## Three control/workload pairs

The separate differential workload repeatability files above are not substituted for the workload members of these pairs.

| Pair | Control CSV | Workload CSV |
| --- | --- | --- |
| 1 | `control_delay277_differential_shunt_20traces.csv` | `workload50_differential_shunt_ab_20traces.csv` |
| 2 | `control_delay277_differential_shunt_repeat_20traces.csv` | `workload50_differential_shunt_repeat_ab_20traces.csv` |
| 3 | `control_delay277_differential_shunt_pair3_20traces.csv` | `workload50_differential_shunt_pair3_20traces.csv` |

| Statistic | Reproduced value |
| --- | ---: |
| Pair 1 difference RMS | 7.514295640639346e-05 |
| Pair 2 difference RMS | 0.00010140561215570668 |
| Pair 3 difference RMS | 7.713020062660322e-05 |
| Difference-waveform Pearson correlation, pairs 1/2 | 0.38416345358006576 |
| Difference-waveform Pearson correlation, pairs 1/3 | 0.2738440005545997 |
| Difference-waveform Pearson correlation, pairs 2/3 | 0.3832974956478396 |
| Combined difference RMS | 6.541915329837584e-05 |

The correlations round to 0.384163, 0.273844, and 0.383297, respectively. Reported digits reproduce the calculations; they are not estimates of measurement accuracy.

## Scientific conclusion

Differential shunt measurement improved observed measurement stability and reduced within-run residual noise in these comparisons. However, arithmetic-specific control/workload separation remains only weak-to-moderately reproducible and is not demonstrated convincingly. The modest correlations between the three difference waveforms show that the apparent difference is not strongly repeatable across pairs. A nonzero difference RMS or a nonzero combined difference does not by itself establish an arithmetic-specific effect.

These are descriptive statistics, not a leakage test or a causal attribution. No leakage claim is supported here. This analysis does not quantify statistical significance, confidence intervals, or contributions from timing variation, drift, and other capture conditions.

## Reproduction

Run from the repository root with Python and NumPy installed. These commands only read existing data and print results; `-B` suppresses Python bytecode files.

```bash
python3 -B compare_trace_csv.py workload50_differential_shunt_20traces.csv workload50_differential_shunt_repeat_20traces.csv --sample-rate-mhz 40 --start-us 10 --end-us 145
python3 -B compare_trace_csv.py workload50_direct_shunt_red_20traces.csv workload50_direct_shunt_red_repeat_20traces.csv --sample-rate-mhz 40 --start-us 10 --end-us 145
python3 -B compare_trace_csv.py workload50_18cm_grabbers_20traces.csv workload50_18cm_grabbers_repeat_20traces.csv --sample-rate-mhz 40 --start-us 10 --end-us 145
```

The following in-memory calculation reproduces all pair-difference statistics without creating another script or changing CSV files:

```bash
python3 -B - <<'PY'
import numpy as np

pairs = [
    ('control_delay277_differential_shunt_20traces.csv',
     'workload50_differential_shunt_ab_20traces.csv'),
    ('control_delay277_differential_shunt_repeat_20traces.csv',
     'workload50_differential_shunt_repeat_ab_20traces.csv'),
    ('control_delay277_differential_shunt_pair3_20traces.csv',
     'workload50_differential_shunt_pair3_20traces.csv'),
]
differences = []
for index, (control_path, workload_path) in enumerate(pairs, 1):
    control = np.loadtxt(control_path, delimiter=',')
    workload = np.loadtxt(workload_path, delimiter=',')
    assert control.shape == workload.shape == (20, 8000)
    assert np.isfinite(control).all() and np.isfinite(workload).all()
    difference = workload[:, 400:5800].mean(axis=0) - control[:, 400:5800].mean(axis=0)
    differences.append(difference)
    print(f'Pair {index} RMS:', float(np.sqrt(np.mean(difference**2))))
for i, j in ((0, 1), (0, 2), (1, 2)):
    print(f'Pairs {i+1}/{j+1} correlation:',
          float(np.corrcoef(differences[i], differences[j])[0, 1]))
combined = np.mean(differences, axis=0)
print('Combined difference RMS:', float(np.sqrt(np.mean(combined**2))))
PY
```

At documentation time, the new differential capture CSVs were present locally but untracked in Git. Reproduction from a fresh checkout requires those same data files to be made available; this documentation update does not add or modify them.
