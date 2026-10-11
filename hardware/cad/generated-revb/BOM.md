# ORBIT revision B — bill of materials

Selected display: **Waveshare ESP32-S3-LCD-4, without touch, 4-inch square 480×480**. This board includes ESP32-S3, 16 MB flash and 8 MB PSRAM. Do not buy an additional DevKitC or the former 2.8-inch Adafruit TFT. ESP8266-12F is not needed in this build.

GBP ranges below are purchasing allowances, not live UK quotations. Shipping, tax and reseller pricing vary. Quantities and allowances refer to one terminal.

| Qty | Item | GBP allowance | Selection / purpose |
|---:|---|---:|---|
| 1 | [Waveshare ESP32-S3-LCD-4 without touch](https://www.waveshare.com/product/mcu-tools/esp32-s3-touch-lcd-4.htm) | £25–40 | Square 480×480 RGB IPS display and controller in one module; verify revision |
| 1 | [Adafruit seesaw encoder breakout 4991](https://www.adafruit.com/product/4991) | £6–10 | I²C encoder counting; encoder not included |
| 1 | [Adafruit MCP23017 breakout 5346](https://www.adafruit.com/product/5346) | £8–12 | Reads two toggle switches via I²C |
| 1 | [Adafruit ADS1115 breakout 1085](https://www.adafruit.com/product/1085) | £12–18 | Reads the analogue dial via I²C |
| 1 | Panel-mount PEC11-pinout incremental encoder with push | £2–5 | Compatible with 4991; 6 mm shaft, nominal 7 mm bushing; verify exact footprint/thread |
| 1 | B10K linear panel potentiometer | £1–3 | 6 mm shaft, nominal 7 mm bushing |
| 2 | M6-bushing SPST ON/OFF metal toggle switches | £3–6 total | LIVE/HOLD and GRID; contacts to logic ground |
| 2 | 22 mm diameter, 6 mm-shaft grub-screw knobs | £3–8 total | Purchased hardware; CAD knobs are visual references |
| 1 | Reputable USB 5 V, 2 A supply | £7–12 | USB power only for the prototype |
| 1 set | Matching USB cable and bolted panel extension | £5–10 | Match actual board connector; final adapter plate depends on extension |
| 1 set | STEMMA QT/JST-SH leads, terminal-to-QT pigtail, wire, headers, perfboard, heat shrink | £6–12 | 3.3 V I²C harness; verify wire order |
| 8 + 4 spare | M3×16 screws and M3 nuts | £3–6 | Front/rear through-boss fixings; spare fasteners for mounts |
| 4 | Display-mount screws and nylon spacers, size pending drawing | £2–4 | Do not order hole size from the CAD proxy |
| 4 | Rubber feet | £1–3 | Stable tabletop base |
| 1 + optional 1 | 100 nF pot filter; 470 µF ≥10 V bulk capacitor | £1–2 | Pot wiper filter; optional power bulk capacitance |

**Budget: approximately £95–155 excluding filament and delivery.** Reuse suitable supplies, wire and fixings.

## Filament — Bambu P1S

- **Bambu PLA Matte Ivory White (11100):** shell, front and rear.
- **Bambu PLA Matte Charcoal:** bezel and electronics tray.
- Optional **Matte Latte Brown (11800):** future chin insert, not required for revision B.

Print separate colour parts; AMS is optional. Buy one spool of ivory and one charcoal if none in stock. Planning allowance 300–450 g combined including margins/supports; actual use comes from the slicer. No green filament: the screen supplies the green. [Bambu PLA Matte colour range](https://bambu-lab-global.myshopify.com/products/pla-matte).

## Wiring architecture

Waveshare external I²C terminal → shared 3.3 V SDA/SCL/GND rail → seesaw 4991 + MCP23017 + ADS1115. Configure the board's I²C supply selector to **3.3 V** and confirm with a meter. Do not assume the terminal ships set that way. Keep leads short and check combined pull-up resistance on the chained breakouts.

| Device | Planned address | Connection |
|---|---|---|
| Encoder seesaw | 0x36 | Compatible encoder A/B/push on its dedicated encoder footprint; it counts locally |
| MCP23017 | 0x20 | GPA0 HOLD, GPA1 GRID; internal pull-ups, SPST contacts to GND |
| ADS1115 | 0x48 | A0 pot wiper; pot ends 3V3/GND; 100 nF wiper to GND; input range ±4.096 V |

Scan and confirm addresses before bringing up the UI. V4.0 Waveshare documentation lists its helper controller at 0x24 and RTC at 0x51, so these planned addresses do not overlap. GPIO mapping varies by revision: V4.0 shared I²C is SDA15/SCL7, while earlier documentation used different pins. Use the exact purchased board's BSP and schematic, not the former DevKitC pin table. [First-party hardware reference](https://github.com/waveshareteam/ESP32-S3-Touch-LCD-4/blob/main/hardware/HARDWARE_REFERENCE.md).

## Firmware consequence

The existing ILI9341/DevKitC starter is for revision A only; it must not be flashed onto this board. Port the network/model tasks onto Waveshare's revision-matched RGB LCD BSP and 480×480 LVGL UI. Poll seesaw position and push at 50 Hz, switches at 50 Hz with 25 ms debounce, ADS1115 at 20 Hz with filtering/hysteresis. Use the same shared-bus mutex as the display helper/RTC; do not independently reinitialise I²C. Network URL, TLS and the existing API contract remain unchanged. This hardware revision updates the firmware design; the Waveshare port is not implemented or hardware-tested yet.
