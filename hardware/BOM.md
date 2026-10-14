# ORBIT revision E — bill of materials

Selected display: **Adafruit 2050, 3.5-inch 480×320 HX8357D TFT breakout**, mounted landscape. This build uses a separate **ESP32-S3-DevKitC-1 N8R8**, a PowerBoost 1000C and the protected rechargeable pack. ESP8266-12F is not used. Rev E replaces the Waveshare board and the seesaw/MCP23017/ADS1115 interfaces with direct GPIO controls.

GBP ranges are planning allowances, not live UK quotations. Quantities cover one terminal; delivery and filament are additional.

| Qty   | Item                                                                                                                                  | GBP allowance | Selection / purpose                                                                                  |
| ----: | ------------------------------------------------------------------------------------------------------------------------------------- | ------------: | ---------------------------------------------------------------------------------------------------- |
| 1     | [Adafruit 2050 TFT](https://www.adafruit.com/product/2050)                                                                            | £35–45        | 480×320, HX8357D, SPI; close IM2 jumper; resistive touch/SD unused                                   |
| 1     | [ESP32-S3-DevKitC-1 N8R8](https://documentation.espressif.com/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.0.html) | £15–25        | 8 MB flash, 8 MB octal PSRAM; buy the specified variant and check outline                            |
| 1     | [Adafruit PowerBoost 1000C, 2465](https://www.adafruit.com/product/2465)                                                              | £18–25        | Load-sharing 1 A Li-ion charger and nominal 5.2 V boost; omit optional USB-A socket                  |
| 1     | [Adafruit 354 protected 3.7 V 4400 mAh pack](https://www.adafruit.com/product/354)                                                    | £20–30        | Factory 1S parallel pack, 69×37×18 mm; maximum recommended charging 1 A                              |
| 1     | Panel incremental encoder with push, 6 mm shaft                                                                                       | £2–5          | Nominal 7 mm threaded bushing, body within 13×13×17 mm; A/B/push to GPIO                             |
| 1     | B10K linear panel potentiometer                                                                                                       | £1–3          | 6 mm shaft, nominal 7 mm threaded bushing, body ≤17 mm diameter                                      |
| 2     | M6-bushing SPST ON/OFF metal toggles                                                                                                  | £3–6 total    | HOLD and GRID; contacts close to GND                                                                 |
| 2     | 22 mm diameter knobs for 6 mm shafts                                                                                                  | £3–8 total    | Grub-screw type; purchased, not printed                                                              |
| 1     | 12 mm **latching SPST** rear pushbutton                                                                                               | £3–6          | EN-to-GND power control; body ≤14 mm diameter ×12 mm deep, bushing suits 3 mm panel                  |
| 1     | Reputable USB 5 V, 2 A supply                                                                                                         | £7–12         | Charging input to PowerBoost micro-USB                                                               |
| 1 set | Charge cable and bolted panel USB extension ending in micro-USB male                                                                  | £5–10         | Generic adapter models 16×9 mm cutout / 24 mm flange pitch; measure purchased extension              |
| 1 set | 33×61 mm trimmed perfboard, two 22-way 2.54 mm female sockets, headers, wire, plugs, heat shrink                                      | £8–14         | Socket carrier, detachable controls, battery lead, switch lead and removable 2-pin system-power link |
| 1 set | 2N3904, 47 kΩ, 1 MΩ, two 10 kΩ resistors, 100 nF capacitor                                                                            | £1–3          | LBO level translator, SD CS pull-up and pot filter; see wiring                                       |
| 1 set | Fixings and spacers listed below                                                                                                      | £8–14         | Display, tray, charger, battery and case assembly                                                    |
| 4     | Rubber feet                                                                                                                           | £1–3 total    | Tabletop base                                                                                        |
| 1 set | 10 mm hook-and-loop strap and 1 mm insulating foam                                                                                    | £2–4          | Soft battery retention, strain relief                                                                |

**Allow approximately £135–215, excluding filament and delivery.** Reuse suitable supplies and fixings. No Waveshare charge-current resistor rework is required in this revision.

## Fixings

| Qty   | Starting specification                             | Location / fit check                                                      |
| ----: | -------------------------------------------------- | ------------------------------------------------------------------------- |
| 4     | M3 heat inserts, approximately 4.6 mm OD ×5 mm     | Shell tray supports: 4.4 mm pilot ×5 mm; calibrate with supplier's insert |
| 4     | M2.5 heat inserts, approximately 3.5 mm OD ×4 mm   | Front display bosses: 3.3 mm pilot ×4 mm; calibrate before fitting        |
| 4     | M2.5×5 screws and thin nylon washers               | TFT mounting tabs into front inserts; verify engagement and no bottoming  |
| 4     | M3×10 screws                                       | Tray into shell inserts                                                   |
| 6     | M2.5×16 screws/nuts/washers and 6 mm nylon spacers | Four carrier mounts and two PowerBoost mounts                             |
| 4     | M3×12 screws/nuts/washers                          | Battery cradle to rear cover                                              |
| 8     | M3×16 screws/nuts                                  | Four front and four rear through-boss fixings                             |
| 2 + 2 | M3 adapter screws/nuts and M2.5 USB-flange fixings | Lengths to suit extension flange, rear and 2 mm adapter                   |

Fastener lengths are prototype selections. Verify engagement, nut access and clearance from traces and the battery before tightening. Print an insert/display fit coupon before full panels.

## PLA colours — Bambu P1S

- **Bambu PLA Matte Ivory White:** front, shell and rear cover.
- **Bambu PLA Matte Charcoal:** landscape bezel, electronics tray, USB adapter and battery cradle.

Separate parts allow both colours without AMS. Start with one spool of each if needed; allow roughly 300–450 g combined including supports, then use the slicer's actual estimate. The display provides the green. [Bambu PLA Matte range](https://uk.store.bambulab.com/products/pla-matte).

## Wiring and firmware

Use the [Rev E assembly pin map](ASSEMBLY.md) and [power wiring](BATTERY.md). All GPIO signalling is 3.3 V. TFT Vin and ESP32 5V share the removable PowerBoost output link. Do not power the ESP32 from the TFT's 3Vo output. PowerBoost LBO needs the specified transistor level translator; it is not a GPIO-safe signal.

The [firmware](../firmware/README.md) now compiles for this TFT: green 480×320 telemetry, Wi-Fi API polling, HOLD/detail toggle, brightness PWM and translated low-battery warning. Encoder selection, globe and pass pages remain planned. This is a bench prototype, not a hardware-tested complete client.
