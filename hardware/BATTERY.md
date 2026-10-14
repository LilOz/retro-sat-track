# ORBIT revision E — rechargeable power

Use **Adafruit PowerBoost 1000C (2465)** with the **Adafruit 354 protected 1S 3.7 V /4400 mAh pack**. This replaces Rev D's Waveshare charger and resistor modification. The battery is a factory-assembled parallel pack with protection, not two loose cells to wire together. This power design has not yet been assembled or electrically tested.

## Power wiring

```text
Rear USB 5 V /2 A input → micro-USB input on PowerBoost 1000C
Protected pack → PowerBoost battery JST (verify polarity)
PowerBoost 5V output → detachable system-power link → ESP32 5V + TFT Vin
PowerBoost GND → common ground, ESP32 GND, TFT GND, controls
Latching rear SPST switch → PowerBoost EN and GND
```

The boost output is nominally **5.2 V**, sold for nominal 5 V loads. Check the delivered boards' ratings and measure the rail before connecting them. The charger's load sharing permits operation while charging, and its 1 A charge setting matches the pack's maximum recommended charge current. A battery must be connected for normal PowerBoost 1000C operation. The optional USB-A output socket is omitted to fit the tray; use soldered output leads.

Switch **closed = OFF**, **open = ON**. The latching switch pulls EN to ground; charging continues when the booster is disabled. EN is pulled up to the charger's supply rail and is not connected to an ESP GPIO. This is a physical power switch, not the former Waveshare momentary power key. Label the two positions after checking the purchased button's action.

The rear USB port is a **charging port only**. For programming, remove the rear and **disconnect the PowerBoost output/system-power link before connecting a PC to the DevKit USB port**. PC USB then powers the ESP32 and TFT rail. Do not parallel PC USB power with the boost output, even if the boost is switched off. Disconnect PC USB before restoring the output link. Use a keyed, labelled two-pin power connector; grounds remain common through the signal wiring. The switch alone does not provide the required separation.

Sources: [PowerBoost product and power requirements](https://www.adafruit.com/product/2465), [pinout and enable behaviour](https://learn.adafruit.com/adafruit-powerboost-1000c-load-share-usb-charge-boost/pinouts), [protected pack](https://www.adafruit.com/product/354).

## Low-battery signal

PowerBoost **LBO falls low below approximately 3.2 V**, but its high level is pulled to battery voltage. Never connect it directly to a 3.3 V GPIO. Fit this NPN translator on the carrier:

```text
PowerBoost LBO ── 47 kΩ ── 2N3904 base
                            │
                           1 MΩ
                            │
Common GND ─────────────── emitter

ESP32 3V3 ── 10 kΩ ──┬── GPIO2
                    └── 2N3904 collector
```

Verify the transistor's actual pin order from its supplier; packages differ. Healthy battery drives the transistor on, so GPIO2 is LOW. Low battery turns it off, so the ESP-side pull-up makes GPIO2 HIGH. Check both levels at the GPIO before connecting it. The second BOM 10 kΩ resistor keeps the TFT SD card chip select inactive; it is not part of this translator.

Firmware filters a HIGH indication for two seconds and displays **LOW BATTERY — CONNECT CHARGER / SWITCH OFF**. The warning remains active during HOLD. A disconnected translator also produces a warning through the input pull-up. This is not a fuel gauge, charging-status indicator or automatic shutdown; switch off or connect the charger when warned. Pack protection is a last-resort cutoff. Do not connect LBO directly to EN.

## Mechanical integration

The **85×51×24 mm cradle** occupies X16–101/Y91–142/Z66–90, above the tray. The pack envelope is X24–93/Y98.5–135.5/Z69–87. Four M3 fixings at (19,94), (98,94), (19,139), (98,139) attach it to integral 2 mm rear-panel spacers. Starting screws are M3×12 with washers/nuts; verify clearance and engagement. Screws remain outside the pack footprint.

Retain the pack with a 1 mm insulating pad and a soft 10 mm hook-and-loop strap through the backplate slots. Smooth the cradle edges; the strap should retain the pack without deforming its wrapper. Leave access to inspect and unplug the pack. The cradle stays below the rear vents.

The rear switch uses a 12.2 mm clearance hole at (117,112), with a nominal 14 mm diameter ×12 mm body reference. Confirm the actual bushing fits the 3 mm panel. Battery, switch and USB extension move with the rear cover; open it slowly and use detachable service leads. Keep battery wiring short, adequately sized and strain-relieved; confirm JST polarity with a meter rather than relying on plug fit. Cable geometry reserves space, not a final wire cut list.

## Endurance and charging estimates

Stored energy is nominally 3.7×4.4 = **16.28 Wh**. An 80% usable-energy allowance and assumed 2.3–3.0 W average system draw give **4.3–5.7 hours**, rounded to a **4–6 hour target**. This is a planning estimate; screen brightness, Wi-Fi, conversion losses, age and cutoff behaviour determine actual runtime.

At 1 A charging, capacity/current gives a 4.4-hour lower bound; allow roughly **5–7 hours with the terminal off**, pending measurement. Running while charging may take longer. The pack page gives differing discharge figures; use its conservative **less than 1 A continuous** recommendation until the delivered pack datasheet is confirmed. Measure current at low charge: if the terminal exceeds that recommendation, reduce its load or select a suitably rated pack and revise the holder. USB input current and battery charge current are different measurements.

## First power-up

1. Inspect soldering, polarity and insulation with battery/USB disconnected. Confirm EN switch wiring, detachable power link and transistor pinout.
2. Bench-test the charger and pack outside the enclosure. Measure output voltage, charge current (no more than the pack's 1 A recommendation), termination and temperature using suitable equipment. Check pack polarity before insertion.
3. Connect the system and exercise Wi-Fi and full backlight. Measure battery current and supply stability, including near low charge; verify GPIO2 stays within 0–3.3 V and the warning polarity is correct.
4. Test USB removal/reconnection, charging while on and off, the latching switch and programming-link procedure. Avoid shorting the live battery or probing loose exposed connectors.
5. After installing, repeat temperature and runtime tests with the rear fitted and vents clear. PLA and lithium cells must remain within their specified operating temperatures. Do not assume the CAD vents establish adequate cooling.

A future automatic shutdown/fuel-gauge feature needs additional circuitry and firmware. It is not provided by this revision.
