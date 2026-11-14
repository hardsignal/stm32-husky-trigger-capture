# Hardsignal Labs — Project 3 Wiring Reference

**Status:** Historical reference / teardown record. **Not an approved wiring or power-up procedure.**

This document records known connections from the NUCLEO-F446RE / ChipWhisperer Husky work, and clearly distinguishes separate NFC-project wiring and standard connector pinouts. Some final Project 3 connections were not recorded and must not be inferred.

## 1. ChipWhisperer Husky — Project 3

| Husky connection | STM32 connection | Purpose / confidence |
|---|---|---|
| TIO4 | NUCLEO PA0 / A0 | External trigger; recorded |
| GND | NUCLEO GND | Common reference; recorded |
| Target 20-pin connector | Configuration-dependent | Complete final connections unverified |
| Measurement input | External measurement arrangement | Final routing unverified |
| Glitch output | Not validated | No demonstrated successful fault delivery |

Recorded capture settings: `scope.trigger.triggers = 'tio4'`, clock generator 10 MHz, ADC 40 MHz, 8,000 samples, offset 0, nominal 200 µs capture.

## 2. Saleae Logic 8

**Project 3:** PA0 trigger observation was recorded, but a definitive final Saleae channel assignment was not established. **Do not treat D0 → PA0 as confirmed for the final setup.** Saleae ground was common to the NUCLEO when connected.

**Separate Project 2 NFC wiring — NOT Project 3:**

| Saleae channel | NUCLEO | Signal |
|---|---|---|
| D0 | D13 / PA5 | SPI SCLK |
| D1 | D11 / PA7 | SPI MOSI |
| D2 | D10 / PB6 | SPI CS/SEN |
| D3 | D12 / PA6 | SPI MISO |
| D4 | A0 / PA0 | NFC IRQ |
| GND | GND | Ground |

## 3. SEGGER J-Link PLUS Compact

The following is a **standard 20-pin J-Link SWD signal reference**, not a verified Project 3 as-wired record. Check the actual adapter and pin-1 orientation before use.

| J-Link 20-pin | Signal | NUCLEO MCU pin |
|---|---|---|
| 1 | VTref | 3V3 target reference |
| 4 | GND | GND |
| 7 | SWDIO | PA13 |
| 9 | SWCLK | PA14 |
| 15 | nRESET | NRST, optional |
| 13 | SWO | PB3, optional |

Some earlier notes mention GPIO observations involving PA0 and PA5; these are **not** substitutes for SWDIO or SWCLK.

## 4. ChipWhisperer target 20-pin header — reference only

| Pin | Signal | Pin | Signal |
|---:|---|---:|---|
| 1 | 5V (NC on Husky) | 2 | GND |
| 3 | 3.3V | 4 | HS1 |
| 5 | nRST | 6 | HS2 |
| 7 | MISO | 8 | VREF (NC) |
| 9 | MOSI | 10 | TIO1 |
| 11 | SCK | 12 | TIO2 |
| 13 | PDIC/CS | 14 | TIO3 |
| 15 | PDID | 16 | TIO4 |
| 17 | GND | 18 | 3.3V |
| 19 | GND | 20 | 5V (NC on Husky) |

**Caution:** The Husky front digital I/O connector is different from this target connector. Confirm connector identity and official hardware documentation before any future connection.

## 5. Project 3 teardown

**Before any changes:** Power down and unplug Husky, NUCLEO, Rigol, external supplies, and all connected instruments. Verify the breadboard is not powered; beware USB back-power paths.

After de-energising, remove the retired PA0/TIO4 jumper, Saleae and J-Link target leads, breadboard power/ground/shunt leads, and attached measurement probes as applicable. Preserve the 10 Ω shunt and leads for future characterised work. Do not disturb unrelated validated NFC wiring.

## 6. Project closeout boundaries

- Trigger and acquisition functionality were demonstrated.
- The external power measurement arrangement did not establish a reproducible fault-injection bypass.
- A negative result in this configuration **does not prove** the STM32 is fault-resistant.
- Complete final Project 3 Saleae/J-Link wiring and measurement routing remain **unknown** where not recorded.
- No external breadboard shunt configuration is approved for reuse by this reference.

**Publication status:** This is a historical draft. Review against the physical bench and repository evidence before public release.
