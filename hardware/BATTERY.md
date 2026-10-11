# ORBIT revision D - rechargeable power

Revision D adds a removable internal battery cradle and rear momentary power button to the Rev C enclosure. The screen, controls, API and exterior case dimensions remain the same. This is a CAD and electrical design proposal; it has not been assembled or electrically tested.

## Selected power architecture

Use one factory-assembled **protected 1S 3.7 V / 4,400 mAh Li-ion pack**, Adafruit 354 as the dimensional reference (69 x 37 x 18 mm). Its two cells are already connected in parallel under one protection circuit. Do not substitute a 7.4 V series pack, loose cells, LiFePO4 or a high-voltage lithium pack.

Rear USB 5 V -> panel USB extension -> Waveshare USB-C. The pack plugs into the Waveshare main PH2.0 battery header. The board contains the charger and battery conversion circuitry; an extra charger/boost board is not part of this design. The smaller RTC battery connector is a different circuit. All controls stay on the board's regulated 3.3 V I2C rail.

Specify **Waveshare ESP32-S3-LCD-4 V4.0** for the battery build. Earlier boards use a different charger/control path and need their own review. Confirm the delivered revision before connecting a battery.

## Required charge-current change on V4

The V4 schematic shows an ETA6098 charger with R13 = 82 kohm. The ETA6098 datasheet identifies 82 kohm as approximately 2 A charging. Adafruit recommends a maximum 1 A charge for this pack. **The selected pack must not be connected for USB charging with that unmodified 2 A setting.**

The prototype specifies **R13 = 220 kohm, 1%, same physical SMD package as the fitted part**, targeting approximately 0.8 A. Waveshare's published ETA6098 resistor table on its LCD-1.9 schematic gives 220 kohm / 0.8 A. This is a hardware rework, not an ESP firmware setting. Have a competent assembler perform it, verify the exact V4 schematic/part location and measure charge current and final voltage before installing the pack. Target <=1 A and nominal 4.2 V termination within the pack's specified tolerance. If the delivered board differs, stop and select a compatible charger configuration rather than applying this component reference blindly.

The pack protection board is a backup against faults; it does not replace the charger. Confirm BAT+ and GND at both ends with a meter: a mating JST/PH plug does not establish polarity. Use a correctly wired extension/adapter without cutting the live pack leads. Charge-current and temperature checks apply with the screen running and off; a 5 V / 2 A supply remains the input allowance with the reduced charge setting.

## Mechanical integration

The rear cover carries an **85 x 51 x 24 mm cradle** above the control tray, behind the screen. In assembly coordinates it occupies X16-101, Y91-142, Z66-90. The battery reference occupies X24-93, Y98.5-135.5, Z69-87. The cradle stays below the rear ventilation slots beginning at Y145 and left of the existing USB route at X102-106. A 1 mm insulating pad and a soft 10 mm hook-and-loop strap retain the pack without a hard clamp or adhesive on its wrapper.

Four M3 through fixings at (19,94), (98,94), (19,139), (98,139) attach the cradle to the revised rear panel. The panel has integral 2 mm spacers to let the strap pass behind the cradle. Starting hardware: four M3x12 screws with washers and nuts; verify engagement before assembly. All screw axes are outside the pack footprint. The new holder can be printed in charcoal PLA and needs no enclosure enlargement.

A generic 12 mm momentary normally-open button fits the revised rear panel at X117/Y112 (12.2 mm clearance). Its modelled body is 14 mm diameter x 12 mm deep; buy a part with a bushing long enough for the 3 mm panel and verify the footprint. Wire its two contacts in parallel with the **two electrical sides of the board's BAT_PWR/PWRKEY switch**, following the actual revision's schematic. Do not attach it to a guessed GPIO, battery positive or a guessed pair of tactile-switch legs. This requires board-level soldering; confirm the switch nets first. It controls battery on/off; behaviour with USB connected is subject to the board power circuit and must be tested.

Open the rear slowly: the battery and power button move with it. Provide a detachable battery lead and power-key connector with service slack, strain relief and no loops near the antenna. The CAD wire shapes reserve space only; connector placement and bend radii still need the purchased board.

## Expected endurance

Nominal stored energy: 3.7 V x 4.4 Ah = 16.28 Wh. With a planning allowance of 80% usable energy after conversion/cutoff and an assumed average 2.3-3.0 W system load, runtime is approximately **4.3-5.7 hours**. Round this to a **4-6 hour target**, not a measured specification. Brightness, Wi-Fi traffic, battery age and actual load change it. At 0.8 A charge current the capacity/current lower bound is 5.5 hours; allow roughly 6-8 hours with the terminal off, pending measurement. Running while charging may take longer.

The Adafruit page gives differing discharge figures; use its conservative <1 A continuous recommendation until the current pack datasheet is confirmed. Measure battery current down to the intended low-voltage shutdown point. If normal load exceeds that recommendation, reduce load or select a differently rated pack and update its cradle before use.

## Firmware design changes - not yet implemented

- Use the revision-matched Waveshare BSP and CH32 helper for battery voltage and board power control. Do not copy SW6106 register writes from V1-V3 onto V4.
- Add a power service alongside display/input/network tasks; read battery voltage through the shared I2C mutex once per second, filter it and expose USB/battery/charging state only where reliably reported by the BSP.
- Show a battery icon with coarse calibrated levels and a low-battery label. Raw voltage is not an accurate remaining percentage; do not claim a fuel gauge. A dedicated gauge can be added later if needed.
- Dim the backlight after inactivity, restore it on any control input, and reduce animation/redraw/network frequency in low-power mode. Green pixels alone do not save LCD backlight power.
- Start bench calibration with a sustained 3.5 V low-battery warning and 3.3 V shutdown threshold (10 seconds persistence, hysteresis), then tune using loaded measurements and the pack's discharge curve. Save settings once, stop network work and request board power-off through supported BSP functions; deep sleep alone may leave the screen/boost circuit powered.
- Verify rear-key wake/off behaviour, USB attach/detach without brownout, operation at low charge, charge termination with screen on/off, and recovery after pack-protection cutoff. If the BSP cannot confirm a power state, show unknown rather than infer charging from USB presence.

The tracked Rev A ILI9341 starter is still incompatible with the selected Waveshare board. This revision updates the power requirements; no rechargeable firmware implementation or hardware validation is claimed.

## First build

1. Confirm V4 board, battery specifications and actual connector polarity; perform and measure the charger-current rework before connecting the selected pack for USB charging.
2. Bench-test battery-only start, USB-only operation, plug/unplug transitions and the rear power key using the board's matching example.
3. Print the cradle and revised rear; reuse the other six Rev C printed parts. Smooth strap slots and pack-facing edges. Fit the insulating pad, soft strap and fasteners with no pressure on the pack wrapper.
4. Install the pack last, route/strain-relieve both rear-panel leads, and measure current, enclosure temperature and charge termination before closing it. Keep the rear vents unobstructed. PLA is a mechanical holder, not battery fire containment.
5. Record actual runtime at the intended brightness and Wi-Fi update interval before replacing the estimates above.

## Sources checked 2026-10-11

- [Waveshare board family and battery header](https://www.waveshare.com/wiki/ESP32-S3-Touch-LCD-4)
- [Waveshare V4 schematic](https://github.com/waveshareteam/ESP32-S3-Touch-LCD-4/blob/main/hardware/schematics/ESP32-S3-Touch-LCD-4%20V4.0.pdf)
- [ETA6098 manufacturer datasheet](https://www.eta-semi.com/wp-content/uploads/2022/03/ETA6098_V1.1.pdf)
- [Waveshare ETA6098 current-selection table](https://files.waveshare.com/wiki/ESP32-S3-LCD-1.9/ESP32-S3-LCD-1.9-Schematic.pdf) (same charger IC, not the target board's component numbering)
- [Adafruit 354 pack ratings, protection and dimensions](https://www.adafruit.com/product/354)
- [Waveshare V4 BSP and hardware reference](https://github.com/waveshareteam/ESP32-S3-Touch-LCD-4/blob/main/hardware/HARDWARE_REFERENCE.md)
