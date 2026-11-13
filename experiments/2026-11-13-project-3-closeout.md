# Project 3 — STM32 / ChipWhisperer Husky Closeout

**Hardsignal Labs | 13 November 2026**

**Status:** Closed — limitations documented; further investigation deferred.

## Objective

Evaluate STM32 firmware instrumentation, acquisition timing,
workload-dependent power measurements, and fault-injection preparation
using NUCLEO-F446RE, ChipWhisperer Husky, Saleae Logic 8,
Siglent SDS1104X-U, and a 10-ohm shunt arrangement.

## Achievements

- Developed bare-metal STM32 trigger, workload, and oracle firmware.
- Established SWD debugging and firmware programming.
- Captured and analysed digital timing using Saleae.
- Established Husky acquisition at 40 MHz, 8000 samples / 200 us.
- Developed Python measurement and evidence-analysis utilities.
- Built and measured Phase 6 v2 CONTROL and WORKLOAD variants.

## Phase 6 v2 Timing

| Firmware | PA5 HIGH duration |
| --- | ---: |
| CONTROL100 | 83.4 us |
| WORKLOAD100 | 195.7 us |
| CONTROL25 | 22.6 us |
| WORKLOAD25 | 50.6 us |
| Matched CONTROL | Approximately 49 us |

## Power Analysis

Repeated differential-shunt and interleaved comparisons did not
establish a reproducible workload-dependent power signature.

The later Siglent CH1 comparison produced:

- CONTROL mean: 40.0097 raw counts
- WORKLOAD mean: 39.9902 raw counts
- Mean difference: -0.0195 raw counts
- Waveform correlation: +0.0348

The November comparison used one capture per condition and does not
establish statistical repeatability.

A September record reports one operator-entered 80 mV rail difference.
Its cause was not established.

No successful fault injection was demonstrated.

## Hardware Incident

During subsequent troubleshooting, the NUCLEO showed an abnormally
low reported 3V3 voltage and low 3V3-to-GND resistance.

Hardware damage is suspected, but the failed component and root cause
remain unconfirmed. The board was withdrawn from powered experiments.

## Conclusion

Project 3 demonstrated firmware instrumentation, acquisition setup,
digital timing validation, and evidence-based experimental analysis.

The tested measurement arrangement did not demonstrate reproducible
workload-dependent power leakage above the observed variation.

This negative result does not establish that the STM32F446RE is
inherently resistant to side-channel analysis.

**Disposition:** Closed with limitations.

Further work requires replacement or repaired hardware and a
separately verified power-measurement configuration.

## Follow-on Project

Project 4: AES-128 key recovery using ChipWhisperer Husky and CW313.

The new project has separate objectives and acceptance criteria.
