# STM32/Husky/Siglent bench checkpoint — 2026-09-30

Hardsignal Labs — Maciej Duranczyk.

These are operator-verified observations reported from today's bench session.
They were not independently repeated during this documentation update. No raw
waveforms, screenshots, per-read scalar records, or kernel logs were supplied
with this checkpoint; no waveform evidence or measurement CSV rows are created.

## Siglent trigger correction

The SDS1104X-U setup was CH1 = MCU rail and CH2 = PA0 timing signal. The edge
trigger used CH2, rising edge, with a level of approximately 1.50 V and a
20 µs/div timebase.

Horizontal Delay had accidentally been set to approximately −155 ms. Resetting
Delay to 0.00 s placed the PA0 rising edge at the trigger reference and produced
repeatable single acquisitions, according to the operator.

## Scalar baseline observations

Across five Siglent scalar baseline reads, the operator observed:

| Quantity | Reported range |
| --- | --- |
| CH1 MIN | 3.08–3.12 V |
| CH1 MEAN | 3.17–3.18 V |
| MEAN − MIN | 50–90 mV |

The difference range is operator-reported from the reads, not reconstructed by
pairing extrema from the aggregate ranges. This scalar variation is **not
evidence of a resolved glitch transient**. MEAN − MIN is the Siglent utility's
definition; the rail logger separately uses IDLE − MIN. No individual readings
are inferred from these ranges.

## Controlled Husky USB stability sequence

The operator established a fresh ChipWhisperer connection with clkgen = 10 MHz,
ADC = 40 MHz, HP=False, and LP=False, then reported:

1. Approximately five minutes idle with no new USB disconnect.
2. Twenty consecutive hardware reads succeeded.
3. Five clean captures succeeded, each with 8000 samples and `capture=False`
   (no timeout).
4. Glitch-subsystem configuration succeeded with the following reported settings:

   | Setting | Reported value |
   | --- | --- |
   | enabled | True |
   | clk_src | pll |
   | trigger_src | ext_single |
   | output | enable_only |
   | ext_offset | 200 |
   | repeat | 8 |
   | MMCM locked | True |

5. One capture succeeded with the glitch engine configured and HP/LP disabled.
6. One controlled LP event completed with `capture=False`, 8000 samples, LP
   returned to False, and no new kernel USB disconnect observed afterward.

The historical USB disconnect issue **was not reproduced during this controlled
sequence**; it is not established as solved. Completion of the LP event and
capture does not establish a resolved rail disturbance or successful fault
injection. No new oracle outcome is inferred for that event.

## PLL inspection and timing limits

The operator reported `input_freq=12 MHz`, `f_out=10 MHz`,
`target_freq=10 MHz`, and `pll_locked=True`.

The relationship between `ext_offset=200` and a physical time delay has **not
yet been experimentally verified**. These clock readbacks do not establish that
relationship, and this checkpoint assigns no time-delay value to the offset.

## Timing-output investigation and final state

The operator observed that `scope.io.glitch_trig_mcx` currently exposes the
Trigger/Glitch Out MCX routing. HS2 was temporarily set to `glitch` during the
investigation and then restored to `None`.

Final operator-reported safe state: **HS2=None, HP=False, LP=False**.
This is the session's reported final state, not a live readback during this edit.

Direct oscilloscope verification of Husky glitch timing was deferred because
proper coax/adapters for Trigger/Glitch Out → Siglent are not currently available.
No improvised loose-wire connection was used. The outstanding evidence remains
a directly recorded timing waveform and a resolved MCU-side rail transient;
neither is supplied by the scalar readings or successful capture returns.

Related records: [rail characterization](2026-09-30-rail-droop-characterization.md)
and [earlier timing-only observations](2026-09-29-oracle-glitch-prep.md).
