# FI-0 — recovery baseline, 28 September 2026

Preparation stage only. These are the operator's verified findings from today's
session; this documentation task did not repeat the hardware checks.
Crowbar remained disconnected. No glitching has been performed yet.

## Verified sequence and outcome

- Husky and NUCLEO were both initially powered down.
- NUCLEO ST-LINK was verified over USB as `0483:374b`
  `STMicroelectronics ST-LINK/V2.1`.
- OpenOCD initially failed with NUCLEO powered and Husky unpowered but still
  connected through Measure POS/NEG.
- Disconnecting the Husky analog measurement leads restored OpenOCD connectivity.
- With both Husky and NUCLEO powered, OpenOCD worked normally.
- A clean NUCLEO power-cycle restored normal TIO4-triggered Husky capture.

This establishes an observed dependence on the connected Husky's power state;
it does not establish the electrical mechanism behind the connection failure.

Verified single capture after recovery (native trace values, no voltage conversion):

| Metric | Value |
| --- | ---: |
| Samples | 8000 |
| Minimum | 0.00146484375 |
| Maximum | 0.0029296875 |
| Peak-to-peak | 0.00146484375 |

These values record one capture, not acceptance tolerances for future captures.

## Safe working order for differential measurement

1. Power both devices off.
2. Connect Measure POS/NEG.
3. Power Husky first.
4. Power NUCLEO second.
5. Verify OpenOCD.
6. If recovery is needed, keep Husky powered and power-cycle the NUCLEO.

Keep the crowbar disconnected for FI-0. Power sequencing and physical connection
checks remain manual; USB visibility cannot establish wiring or crowbar state.

## Recovery check

[`fi0_recovery_check.py`](../fi0_recovery_check.py) checks ST-LINK and Husky USB
visibility, examines the STM32F446 target through OpenOCD, then arms once for one
normal TIO4 capture. It prints sample count, minimum, maximum, and peak-to-peak.
It requires Linux `lsusb`, `openocd` with its ST-LINK/STM32F4 scripts, USB access,
and the existing ChipWhisperer Python session with its configured `scope` object.
Close other OpenOCD/debugger sessions first. The running target firmware must
already generate PA0/TIO4 triggers.

Run in that existing Python session:

```python
import runpy
from pathlib import Path
runpy.run_path(
    str(Path.home() / "cw_nucleo_trigger/fi0_recovery_check.py"),
    init_globals={"scope": scope},
    run_name="__main__",
)
```

Reusing the connected scope is deliberate: the installed ChipWhisperer
`OpenADC.con()` resets FPGA state and writes settings. This checker never opens
or reconnects a scope, calls `default_setup()`, or assigns capture settings.
A standalone invocation checks USB visibility and then fails with instructions
to supply the existing scope. If that session no longer exists, the checker
cannot reconstruct it while preserving the no-settings-change constraint.

Preflight requires 8000 samples, one segment, non-streaming normal ADC mode,
a basic rising-edge TIO4 trigger with TIO4 as input, disabled glitch engine and
crowbar outputs, no HS2 glitch output, and an existing capture timeout in
`(0, 30]` seconds. Other acquisition settings are retained. It fails instead of
changing unsuitable settings. OpenOCD has a 15-second subprocess timeout, its
servers are disabled, and the stock target's examine-end register-write hook is
removed for this invocation. It issues no halt, reset, resume, firmware flash,
programming, or target-memory-write command. Debug attachment itself is not a
passive electrical measurement.

The script writes no trace files or CSVs, performs no automatic power-cycle,
and never requests a glitch. Capture arming and readout necessarily operate
the acquisition hardware. It leaves the caller's scope connection open, makes
no retries, and reports failure for missing/ambiguous devices, failed preflight,
failed target examination, capture timeout, invalid trace length/nonfinite data,
or ADC errors. Under `runpy`, failure raises `SystemExit(1)`; success returns
normally. Firmware, existing hardware-control code, and datasets are untouched.
