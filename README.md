# STM32 Husky Trigger Capture

A minimal hardware-security lab project using:

- STM32 NUCLEO-F446RE
- ChipWhisperer Husky
- Saleae Logic 8

## Goal

Create a repeatable STM32 workload, generate a clean trigger on PA0, verify timing with Saleae, and capture the synchronized acquisition window with ChipWhisperer Husky.

## Current wiring

### NUCLEO → Husky

- PA0 / A0 → Husky TIO4
- GND → Husky GND

### NUCLEO → Saleae

- PA0 / A0 → Saleae D4
- PA5 / D13 → Saleae D0
- GND → Saleae GND

The NUCLEO is powered by its own USB connection. Husky target power is not used.

## Firmware

`main.c` drives:

- PA0 HIGH as the capture trigger
- PA5 HIGH as a workload marker
- a short repeatable arithmetic workload
- PA5 LOW
- PA0 LOW

The workload was reduced to 5 loop iterations so the active region fits inside the Husky capture window.

## Husky capture settings

- ADC samples: 1000
- ADC clock: 40 MHz
- Capture window: 25 µs
- Trigger source: TIO4

## Verified results

- Saleae confirms PA0 and PA5 timing
- Short workload is approximately 18–19 µs
- Husky captures 1000 samples successfully
- 10 repeated acquisitions complete consistently
- Current trigger/capture path is working

## Next step

Connect the Husky analog measurement input to the STM32 power-measurement path and capture the real power signature of the workload.

The current ADC traces only validate synchronized acquisition; they are not yet meaningful STM32 power traces.
