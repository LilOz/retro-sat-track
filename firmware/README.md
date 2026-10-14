# ORBIT revision E — ESP32-S3 / Adafruit 2050 client

The bench client now targets **ESP32-S3-DevKitC-1 N8R8 + Adafruit 2050 HX8357D**, landscape **480×320**. It compiles with PlatformIO and uses real backend telemetry. Hardware flashing, fit and electrical testing remain outstanding. The network host is configurable for LAN or validated HTTPS; the backend API is unchanged.

## Implemented

- HX8357D selected in the display constructor, with an explicit 16 MHz SPI clock.
- Green telemetry with altitude, speed, satellite name, UTC, stale/offline and old-element warnings.
- Real ISS/stations state polling every three seconds on a worker task; bounded, filtered JSON and exponential failure backoff up to 60 seconds.
- HOLD freezes the displayed sample; GRID currently toggles latitude/longitude detail.
- B10K intensity dial reads at 50 Hz with filtering and controls the **physical backlight** using 5 kHz PWM on GPIO15.
- GPIO2 reads the PowerBoost low-battery signal **through an NPN level translator**, with a two-second debounce. Warning continues during HOLD.
- One-second display redraw; no network I/O in the UI loop.

Selection is currently fixed to ISS (NORAD 25544). Encoder/push, group browsing, globe and pass pages are specified below, not implemented. No touchscreen or SD card support is enabled. Battery percentage, charging state and automatic power-off are not implemented.

## Pin map

| Signal | GPIO / connection |
| --- | --- |
| TFT CLK / MOSI / MISO | 12 /11 /13 |
| TFT CS / D-C / RST | 10 /9 /14 |
| TFT LITE backlight | 15; 5 kHz, 8-bit PWM, duty range 12–255 |
| TFT Vin / GND | System nominal 5 V rail / common GND |
| TFT IM2 | Close rear solder jumper to 3.3 V for SPI |
| TFT CCS | 10 kΩ to TFT 3Vo to deselect unused SD |
| Encoder A / B / push | 4 /5 /6 reserved; common to GND; enable pull-ups in future input driver |
| Pot wiper | 1 ADC1; ends ESP 3V3/GND, 100 nF wiper-to-GND |
| HOLD / GRID | 7 /8, switches to GND, internal pull-ups |
| Low-battery input | 2, NPN collector with 10 kΩ to ESP 3V3; HIGH means low battery |

All GPIO signalling is 3.3 V. Avoid boot straps, USB 19/20 and flash/PSRAM 26–37. Do not use the TFT 3Vo output to power the ESP32, or connect PowerBoost LBO directly to GPIO2. [Full assembly](../hardware/ASSEMBLY.md) and [power/translator circuit](../hardware/BATTERY.md) define the wiring.

**Disconnect the boost output/system-power link before plugging the DevKit into PC USB for upload or serial monitoring.** Disconnect PC USB before restoring that link. Rear USB goes only to the charger and cannot program the ESP32.

## Build and configuration

Copy `include/orbit_config.example.h` to ignored `include/orbit_config.h`. Set Wi-Fi, `API_BASE_URL` without trailing slash, optional bearer token and PEM root CA. Do not commit credentials. The default example is only a template.

```sh
pio run -d firmware
pio run -d firmware -t upload
pio device monitor -d firmware
```

Set the correct upload/monitor port if automatic detection is ambiguous. The environment pins Espressif32 6.10.0, Adafruit HX8357 1.1.20, GFX 1.11.11 and ArduinoJson 7.3.1. The Arduino core in this environment provides `ledcSetup`/`ledcAttachPin`; changing core major versions requires a PWM API review.

Compile result: **success**, static RAM **47,024 /327,680 bytes (14.4%)**, flash **918,041 /3,342,336 bytes (27.5%)**. This does not measure runtime TLS/JSON peak allocation or validate PSRAM, display wiring or network behaviour on a board. The starter requires a positive `Content-Length` no larger than 4096 bytes; a proxy must preserve that header.

LAN HTTP must be explicitly enabled. Use the PC's LAN address, not 127.0.0.1; start the server with `uv run --locked run.py --host 0.0.0.0 --no-browser`. WSL may need forwarding/firewall configuration. HTTPS requires a valid root CA and NTP-synchronised time, with no insecure fallback.

For future public hosting, put the API behind an HTTPS gateway that enforces device authentication. The MVP itself does not validate bearer tokens; sending one does not add protection. Protect observer updates separately and keep `.data` on persistent storage. The saved observer is server-global: use explicit coordinates for device-specific passes, and add per-device state handling before displaying shared-host look angles as personal values. No hosting provider is assumed.

## Remaining firmware design

1. **Inputs and selection:** sample full-detent quadrature at 2 ms, debounce push/toggles for 25 ms, map rotate to selection and push to page/menu. Retain brightness as physical PWM. Poll the catalogue in 16-item pages; preserve uint32 NORAD IDs and use group IDs from `/api/v1/status`.
2. **Model/network:** a length-one selection queue replaces obsolete requests; tag replies with selection generation and reject old responses. Keep one catalogue page, 48 track vectors and at most eight passes. Add retry jitter. Bound/filter every response and never query CelesTrak directly from the device.
3. **Display pages:** telemetry, wireframe orthographic globe with clipped rear hemisphere, and geometric passes. Fetch state every 3 s; track (`samples=48`), status and passes every 60 s. Label the track timestamp, preserve HOLD UTC and distinguish element age from connection age. Hide observer look angles if observer is unset.
4. **Pass navigation:** request the list before details; fetch `sky_path` only for selected passes. Refresh an expired detail ID after 404. Geometric passes do not establish optical visibility.
5. **Power/UI polish:** measure current and runtime, redraw dirty regions to reduce flicker, check low-battery behaviour under Wi-Fi load. A fuel gauge or automatic cutoff requires a separate hardware change.

## Bench acceptance still required

Verify real ISS data, malformed/oversized responses, unavailable catalogue, bad CA rejection, Wi-Fi interruption while controls respond, frozen HOLD timestamp, backlight range, low-battery warning, USB/battery transitions and supply stability. Once selection/pages are implemented, add rapid encoder turns, obsolete-reply rejection and expired pass-ID checks. Compilation alone does not complete these tests.
