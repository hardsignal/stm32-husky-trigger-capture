# Hardsignal Labs — STM32/Husky characterization

Maciej Duranczyk · September 2026

## Objective and hardware

Develop a repeatable workflow for STM32 firmware-oracle, acquisition-timing, and
rail-voltage characterization on owned lab hardware. The documented stack combines
an STM32 NUCLEO-F446RE, ChipWhisperer Husky, Saleae Logic 8, Siglent oscilloscope,
ST-LINK/V2.1, and a 10 ohm shunt measurement path. The NUCLEO uses its own USB
power; Husky target power is not used. See the [project overview](../README.md).

## Firmware oracle and timing

[Bare-metal firmware](../main_fault_oracle.c) executes a 50-iteration arithmetic
workload with three separate signals: **PA0/A0** triggers Husky through TIO4,
**PA5/D13** marks the workload, and **PA1/A1** reports result equality with
`0x8FAEE67B`. The oracle is cleared before each iteration and updated before PA0
falls; LOW during computation is not a completed fault verdict.

The [operator-reported baseline](2026-09-29-oracle-glitch-prep.md) uses a **40 MHz
ADC and 8000 samples / 200 µs**. Manual observations place the workload-end/oracle
landmark near **159.0–159.2 µs** after PA0. HS2 timing-only checks produced an
event near 159 µs and an approximately 1.1 µs pulse with the crowbar disconnected.
The Python timing estimator identifies an analog transition; it does not directly
measure a PA1 edge or classify the oracle.

## Rail measurement workflow and evidence

Siglent readings are entered manually through a [standard-library Python logger](../rail_droop_log.py).
It validates CSV measurements, calculates idle-to-minimum droop, preserves operator
notes, and produces summaries and Markdown reports against the first logged row.

The [CSV](rail_droop_results.csv) contains **one operator-entered result**:
**3.20 V idle, 3.12 V minimum, 80 mV calculated droop, oracle PASS**. This is a
recorded voltage difference, not evidence of its cause or a successful fault.
The [bench note](2026-09-30-rail-droop-characterization.md) reports no oracle anomaly
and a latest safe state of **HP=False, LP=False**; these are operator reports,
not a current hardware readback. No automatic crowbar sweep is implemented in
the documented preparation workflow.

## Lessons and limitations

Separating trigger, workload marker, and verdict makes their timing and meaning
explicit. Timing-only validation and electrical rail characterization remain
separate evidence streams. Operator-reported Siglent vertical-scale and
probe-ground troubleshooting highlights the importance of measurement setup.

Earlier [differential-shunt analysis](2026-09-17-differential-shunt.md) found improved
repeatability in some metrics, but did not convincingly establish arithmetic-specific
control/workload separation. The single rail row cannot establish trends or
causality, and the rail transient is not yet well resolved electrically. A complete
independent oracle validation record and detailed per-offset LP sweep results are
absent. The oracle alone cannot distinguish reset from hang. **No successful fault
injection has been demonstrated.**

## Next experiment

Improve Siglent transient capture of the MCU-side rail before changing glitch
strength further, recording paired readings, settings, and operator observations.

## Skills demonstrated

- STM32 bare-metal C and GPIO trigger/workload/oracle design, supported by firmware source.
- Saleae logic-analysis instrumentation and Husky acquisition/timing work, documented as operator-reported bench observations.
- Debugger bring-up and recovery with ST-LINK/OpenOCD; prior J-Link work is reported in the [project context](2026-09-30-rail-droop-characterization.md#project-context), without a dedicated J-Link validation record here.
- Oscilloscope rail measurement and setup troubleshooting, documented as operator-reported work.
- Python CLI tooling for CSV validation, calculated statistics, and Markdown reporting.
- Git-based experiment documentation linking source, measurements, assumptions, and limitations.

## Portfolio achievements

- Implemented a bare-metal STM32 arithmetic oracle with separate acquisition trigger, workload marker, and completion verdict.
- Documented operator-reported 40 MHz Husky acquisition and a ~159 µs timing landmark, distinguishing HS2 timing checks from rail measurements.
- Built offline Python measurement logging, validation, and reporting with preserved operator notes and explicit limits on conclusions from one rail result.
