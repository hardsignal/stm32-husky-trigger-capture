# Oracle timing and safe glitch preparation

Bench observations supplied by the operator; the new preparation script has
only been AST syntax-checked, not run against hardware.

- Setup: ChipWhisperer Husky, NUCLEO-F446RE, and Saleae; PA0 feeds Husky TIO4.
- Clean baseline: 40 MHz ADC, 8000 samples (200 µs); workload-end/oracle
  landmark approximately 159 µs after PA0, manually validated near 159.0–159.2 µs.
  Automated timing uses the strongest absolute sample-to-sample transition in
  158.5–159.5 µs, timestamped at the later sample. The baseline plot remains
  145–170 µs. A delta below 0.0007 produces a warning without substituting a point.
  Low-gain warnings remain visible; other ADC errors reject the capture.
- HS2 timing-only validation: at a 10 MHz glitch clock, `ext_offset=1590`
  produced an event about 159 µs after PA0. `enable_only`, `repeat=10`
  produced an approximately 1.1 µs observable pulse.
- Operator-reported reset state: `output="glitch_only"`, `repeat=1`, `width=0`,
  `glitch_hp=False`, and `glitch_lp=False`.
- The physical crowbar remained disconnected throughout these timing checks.

`husky_oracle_glitch_prep.py` reuses the baseline configuration, safety checks,
and cleanup. It explicitly disables HS2 routing, keeps HP/LP off, checks PLL/MMCM
locks, validates one clean capture, and prints the prepared settings before
disabling the engine and disconnecting. Safety readbacks occur at checkpoints;
they are not continuous monitoring. No crowbar enabling, HS2 glitch routing,
target-power changes, fault injection, or sweep is implemented.
