# Next session: direct Husky timing verification — 2026-09-30

## Purpose and evidence boundary

Measure Trigger/Glitch Out timing on the Siglent relative to PA0 before further
fault-injection tuning. This is a manual measurement plan, not an executed test
or a parameter sweep. No successful fault injection is established.

The [bench checkpoint](2026-09-30-bench-checkpoint.md) records operator-verified
observations, including the corrected Siglent delay, a controlled USB sequence,
and final HS2=None / HP=False / LP=False. Those states require fresh verification
next session. The historical USB issue was not reproduced in that sequence;
it is not established as solved. Direct MCX timing verification remains deferred
until the proper cable is available.

## Intended measurement topology

| Siglent channel/setting | Intended use/value |
| --- | --- |
| CH1 | MCU-side rail |
| CH2 | PA0 firmware timing signal |
| CH3 | Husky Trigger/Glitch Out through proper 50-ohm MCX-male to BNC-male coax |
| Initial timing reference | CH2 rising edge; approximately 1.50 V trigger level |
| Horizontal Delay | 0.00 s |
| Initial timebase | 20 µs/div |

CH3 is the new, unverified measurement connection. Cable impedance alone does not
specify the oscilloscope input termination; confirm instrument/output compatibility
and record the actual input settings before connection. Do not improvise wiring.

## Configuration to verify and record

Clock/acquisition settings below are supported by
[baseline source](../husky_oracle_baseline.py); the glitch settings and PLL
inspection values are operator-reported in the bench checkpoint. They are not
a fresh combined readback.

| Setting | Recorded configuration to check |
| --- | --- |
| clkgen_src | system |
| clkgen_freq | 10 MHz |
| adc_mul | 4 |
| adc_freq | 40 MHz |
| trigger | tio4 |
| adc.samples | 8000 |
| adc.offset | 0 |
| glitch.enabled | True |
| glitch.clk_src | pll |
| glitch.trigger_src | ext_single |
| glitch.output | enable_only |
| glitch.ext_offset | 200 |
| glitch.repeat | 8 |
| PLL input_freq | 12 MHz |
| PLL f_out | 10 MHz |
| PLL target_freq | 10 MHz |
| PLL locked | True |
| MMCM locked | True (operator-reported) |

Safe starting readbacks: `scope.io.hs2=None`, `scope.io.glitch_hp=False`,
`scope.io.glitch_lp=False`. Keep HS2 disabled throughout this MCX measurement.
Do not increase repeat/strength or infer a time equivalent for `ext_offset=200`.
Existing baseline/preparation scripts configure different glitch settings; do
not assume running them reproduces this checkpoint. This runbook changes no script.

## Stage 0 — Physical safety/checks

1. Power down/unplug the target before changing coax or probe wiring.
2. Connect the proper MCX-to-BNC coax from Trigger/Glitch Out to CH3. Use no
   improvised loose-wire connection.
3. Inspect grounds, existing CH1 rail/CH2 PA0 wiring, and channel/input settings.
   Resolve any connection or termination uncertainty before proceeding.
4. Reconnect the target only after wiring inspection. Retain the documented
   [FI-0 power-order precautions](2026-09-28-fi-0-recovery-baseline.md#safe-working-order-for-differential-measurement)
   where the differential measurement connection is present.
5. Verify the safe starting readbacks, PLL/MMCM lock, CH2 trigger reference,
   horizontal Delay = 0.00 s, and initial 20 µs/div timebase. Record discrepancies.

## Stage 1 — Timing-only verification

1. Keep HP=False and LP=False. Verify the configuration above without changing
   offset, repeat, or strength to search for an effect.
2. Use the installed ChipWhisperer version's supported `scope.io.glitch_trig_mcx`
   API to route the glitch timing signal to Trigger/Glitch Out, then read the
   routing back and record it. The repository establishes the property name but
   not its accepted selector values; confirm those from the installed API's
   documentation before using it. Stop if routing cannot be verified; do not
   guess a selector, use direct register writes, or substitute HS2 routing.
3. Capture CH2 PA0 and CH3 timing output together, retaining CH2 rising edge as
   the initial trigger reference. Verify that the observed edges are identifiable.
4. Measure PA0 rising edge → the identified CH3 output edge directly. Record the
   edge definitions, cursor positions, units, and acquisition settings. Do not
   calculate the claimed delay solely from ext_offset or PLL frequency.

## Stage 2 — Repeatability

Collect several timing-only captures with HP/LP disabled and unchanged test
settings. Record each measured delay, number of captures, and observed min/max
or spread; retain failed/ambiguous acquisitions as such. Save screenshots and
raw exports where practical, associated with a run ID. Do not claim timing
precision beyond the Siglent acquisition evidence or confuse display digits
with measurement accuracy. A stable analog-output timing observation is not
an oracle verdict or proof of a rail disturbance.

## Stage 3 — Rail correlation

Only after timing is verified, inspect CH1 rail with CH2 and CH3 in the same
acquisition. Begin with the HP/LP-disabled baseline and preserve its evidence.
Any later LP event is a separate deliberate, one-at-a-time operator action;
immediately restore LP=False afterward and verify it. Keep HP=False and do not
increase repeat/strength or introduce automated firing/sweeps.

Distinguish scalar MIN/MEAN/RMS from a resolved waveform at a documented time.
Siglent utility droop is MEAN − MIN; the rail logger uses IDLE − MIN. A scalar
difference or `capture=False` (no timeout) does not prove successful fault
injection. Record an oracle result only if actually observed in its valid interval.

## STOP conditions

Stop the session on any USB disconnect/reset, unexpected target reset, loss of
PLL/MMCM lock, unverifiable HP/LP state, unexpected rail collapse, uncertain
probe/coax connection, or ambiguous scope trigger/timing reference. Treat unknown
hardware state as unknown; do not continue captures or assume cleanup succeeded.
Re-establish inspected wiring and verified safe state before resuming. The
[preparation note](2026-09-29-oracle-glitch-prep.md) documents the USBErrorIO
cleanup exception; a disconnected device cannot provide a trustworthy readback.

## Evidence checklist and closeout

- Configuration and routing readback, including HS2/HP/LP and PLL/MMCM locks.
- Siglent screenshot with channels, reference, scales, and Delay visible.
- Directly measured PA0 → glitch-output delay and identified edges.
- Repeated timing measurements, count, spread, and acquisition limitations.
- CH1 rail waveform if resolved; otherwise explicitly record that it is unresolved.
- Oracle result only if actually observed; capture return recorded separately.
- Relevant kernel USB messages and the session observation interval.
- Existing [evidence-index/hash workflow](../README.md#offline-bench-evidence-index)
  updated only with actual local artifacts and verified run associations.

At closeout, verify and record HS2=None, HP=False, LP=False and the final MCX
routing state. Preserve evidence without altering existing measurement CSV rows.
Do not label a missing screenshot, waveform, or oracle observation as completed.
