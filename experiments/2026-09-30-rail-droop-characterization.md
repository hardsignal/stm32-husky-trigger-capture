# Rail droop characterization — 2026-09-30

## Project context

This experiment is part of **Hardsignal Labs**, an independent hardware-security lab focused on cyber-physical systems, embedded devices, RF/SDR, fault injection, firmware analysis, and automotive security.

Researcher: Maciej Duranczyk  
Lab: Hardsignal Labs  
Project: STM32 fault-oracle and voltage-glitch characterization

The work is being carried out on owned lab hardware in a controlled bench environment. Measurements, timing validation, oracle behaviour, and rail-characterization results are recorded as part of a repeatable experimental workflow rather than as one-off observations.

The current STM32/Husky work builds on prior bring-up and instrumentation work with J-Link, Saleae, ChipWhisperer Husky, oscilloscope measurements, and controlled power-path characterization.

## Operator-reported results

These observations are operator-reported from manual STM32/Husky bench tests
using Siglent rail measurements. They have not been independently verified.

- Current safe state reported by the operator: HP=False, LP=False.
- The timing sweep has already been completed manually.
- Repeat values tested: 1, 2, 4, and 8.
- Observed idle rail voltage: roughly 3.20–3.22 V.
- Observed minimum rail voltage: around 3.12–3.16 V.
- No oracle anomaly was observed.
- Measurement setup troubleshooting included Siglent vertical scale and probe
  ground issues.

Individual paired measurements and their settings were not supplied, so these
aggregate observations are not entered as CSV test rows. The example below is
usage syntax, not a recorded result.

## Offline logging

`rail_droop_log.py` uses only the Python standard library and local CSV files.
It does not access hardware, import ChipWhisperer, arm or capture, or control
HP/LP. State, output mode, oracle result, and capture return are manually
reported metadata. Omitted output mode and HP/LP states are recorded as
`unknown`; the current safe state is not assumed for historical tests.

From the repository directory:

```bash
python3 rail_droop_log.py init
python3 rail_droop_log.py add --offset 200 --repeat 8 --idle 3.20 --min 3.12 --mean 3.20 --rms 3.20 --oracle PASS --capture false
python3 rail_droop_log.py summary
```

Optional metadata flags: `--output-mode`, `--hp-state true|false|unknown`,
`--lp-state-after-test true|false|unknown`, and `--notes`.

The CSV location is `experiments/rail_droop_results.csv`, relative to the script,
regardless of the working directory. `init` creates the header and preserves
existing data. `add` requires an initialized CSV, records a UTC timestamp, and
calculates `droop_mv = (rail_idle_v - rail_min_v) * 1000`.
`summary` prints every field of every logged test, droop statistics, and each
test's droop difference from the first logged test. These comparisons describe
the entered measurements only; they do not establish a causal effect of settings.

Validation for this change is AST parsing only. The logger and the commands
above have not been executed, and no measurements have been collected.
