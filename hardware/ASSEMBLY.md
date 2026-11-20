# Rev F — assembly and wiring

[Shopping list](BOM.md) · [CAD downloads](cad/generated-revf/) · [screen concept](UI-CONCEPT.md) · [firmware status](../firmware/README.md)

## Layout and fit

Body **135×175×95 mm**; front Z0–3, rear Z92–95. The full shell and both sides stay present. The removable lower tray carries only the ESP32. A single USB cable enters the rear and plugs into its USB-C socket; no charging board or internal battery.

| Part | CAD reference in mm | Before printing |
| --- | --- | --- |
| MSP3525 no-touch PCB | 98×55.5; X19.54/Y93.25/Z12; thickness 1.6 | Verify exact SKU, PCB outline and active-area offset |
| TFT mounting centres | X22.54/114.54, Y96.25/145.75; 92×49.5 pitch; 3.2 mm holes | Family drawing evidence; confirm delivered no-touch board |
| Active area / front aperture | 73.44×48.96 /74.2×49.8; centred (67.5,121) | Screen offset and rotation need checking on the powered board |
| Display carrier | 110×72 mm at X14/Y85/Z7; 2 mm plate plus 3 mm bosses | Replaceable; lateral slots give ±1.3 mm adjustment; depth requires measured shims or regenerated bosses |
| Display stack | Glass/adhesive nominal Z9–12, PCB Z12–13.6; headers reserved to Z23.3 | Up to 14.3 mm total reserved; confirm pin direction and plug clearance |
| Controller tray | 110×70 mm at X12.5/Y10/Z55 | Four M3 shell ledges; antenna opening X88–106/Y17–49 |
| ESP32 envelope | X40–102.5/Y20–45.4/Z64–65.6; USB end toward X40 | Candidate clone may differ; support pads must avoid pins/solder and metal must avoid antenna |
| Rear USB entry | 16×10 opening at X15/Y24; adjacent tie slots | Check moulded C plug/boot; smooth edges, cushion jacket and add tie strain relief |

The source family drawing labels MSP3526 although its dimensional notes include a no-touch stack. XY dimensions agree with the MSP3525 manufacturer listing; the exact delivered board and depth remain **provisional**. This is not an Adafruit mounting pattern. The carrier separates supplier-specific dimensions from the shell; it is not a universal fit guarantee. Reference electronics are simplified envelopes, with cable routes excluded from rigid interference checks.

## Power and planned pin map

**One supply:** USB-A supply → data cable → ESP32 USB-C → board USB-derived 5V pin → display VCC. All grounds common. Confirm the board's 5V pin is the USB-derived rail and the module's rated VCC before connection. The selected module is specified for 5 V; logic uses 3.3 V. Never power the ESP32 from a display regulator output.

| Signal | ESP32 GPIO / connection |
| --- | --- |
| SCK / SDI(MOSI) / SDO(MISO) | 12 /11 /13 |
| LCD_CS / LCD_RS (D-C) / LCD_RST | 10 /9 /14 |
| LED backlight control | Reserve 15; verify control polarity/current against the actual schematic before connecting; leave default-on for first light |
| Encoder A / B / push | 4 /5 /6; common to GND, firmware pull-ups planned |
| B10K pot | Wiper 1; ends 3V3/GND, 100 nF to GND |
| HOLD / GRID toggles | 7 /8; switch to GND, pull-ups planned |
| SD_CS | 10 kΩ to ESP32 3V3; card slot unused |
| Touch pins, battery GPIO2 | Unconnected; no touch or battery service |

No Adafruit IM2 solder-jumper instruction applies here. Avoid boot straps 0/3/45/46, USB 19/20 and flash/PSRAM 26–37. Check the **44-pin** candidate's pin labels, USB connector choice and module memory variant. Use short SPI leads, ideally ≤10 cm, with adjacent grounds. For programming, move the same USB cable from the wall supply to the PC; do not connect another powered USB port at the same time.

## Build

1. **Confirm parts and first light.** Check the exact panel and board drawings, then run the vendor's example for the delivered **ST7796U** variant. The repository's current HX8357D firmware is legacy and will not drive this panel. Verify orientation, active-area alignment, rails and backlight control.
2. **Print a mounting coupon first.** Check hole pitch, glass clearance, inserts, controls and USB plug. Adjust the replaceable carrier/tray before full printing. P1S starting profile: 0.4 mm nozzle, 0.2 mm layers, four walls, 15% gyroid. Orient/drop each STL to the bed and inspect supports under shell ledges. Print six parts, ivory main enclosure and charcoal internals/bezel.
3. **Fit inserts before electronics.** Eight M3: four front carrier supports and four shell tray ledges. Four M2.5 in display-carrier bosses. Calibrate 4.4/3.3 mm pilots to actual insert OD. Fit bezel with pegs and small foam-tape strips outside the viewing opening.
4. **Mount panel and controls.** M2.5×5 +nylon washers secure PCB tabs to the carrier; four M3×6 attach the carrier to the front. Check engagement and glass clearance before tightening. Fit encoder, pot and toggles using their supplied nuts/washers; add the two knobs.
5. **Fit controller.** Place 1 mm foam on the tray's four support pads, check clearance beneath the PCB, then loosely secure with two ties through the slots. Route over clear PCB areas, not components or antenna. No perfboard or guessed DevKit mounting holes. Fit four M3×6 tray screws and plug in labelled wiring.
6. **Route USB and close.** Feed the cable's C plug through the rear opening, plug into the correct DevKit port, add a padded tie restraint at the rear slots and leave service slack. Confirm the cable does not tug the socket when the cover opens. Secure front/rear with eight M3×16 screws/nuts, check nut access and add feet.
7. **Bench-check the assembly.** Confirm no shorts, correct rails, stable Wi-Fi/display under load, acceptable temperatures and cable strain relief. Check knob/toggle operation when their firmware is implemented. CAD checks do not establish physical or electrical fit.

[MSP3525 manufacturer](https://www.ronboe.com/shop/msp3525/) · [family mechanical drawing](https://manuals.plus/m/b19a9ff6dabe51bb10851c12a399a0ba7ec1a1a8baeee17ada31d1aa02a08ef6.pdf)
