> **Current hardware is revision D: Waveshare ESP32-S3-LCD-4 without touch.** This file and the compiled starter below describe the previous DevKitC/ILI9341 build. Do not use those pin assignments or flash that binary onto the Waveshare board. See [current BOM and firmware port design](../hardware/BOM.md) for the replacement RGB display/I²C control architecture.

[Battery power-service requirements](../hardware/BATTERY.md) are specified for Rev D but not implemented in this legacy starter.

# ESP32-S3 client design

Revision A architecture plus a telemetry bench starter. Compiled successfully with PlatformIO; not yet flashed or tested on hardware. No simulated data. Network host is configurable: LAN first, HTTPS hosting later. Backend API remains unchanged.

## Wiring (ESP32-S3-DevKitC-1 N8R8 only)

| Signal | GPIO / connection |
|---|---|
| TFT SCK / MOSI / MISO | 12 / 11 / 13 |
| TFT CS / DC / RESET | 10 / 9 / 14 |
| TFT Vin / GND | Board 5 V / common GND (Adafruit 1770 only) |
| Encoder A / B / push | 4 / 5 / 6, common to GND, pull-ups |
| Pot wiper | 1 ADC1; ends 3V3/GND, 100 nF wiper to GND |
| HOLD / GRID | 7 / 8, switch to GND, pull-ups |

Avoid flash/PSRAM pins 26–37, boot straps and USB pins 19/20. Confirm against the exact board schematic. All GPIO signalling is 3.3 V. The TFT backlight is fixed in this starter; intensity dial changes drawn green, not backlight current. Never put 5 V on pot or GPIO. Use one USB power source; do not backfeed two supplies.

## Modules and scheduling

- UI task owns TFT and control state: 2 ms encoder sampling, 25 ms button debounce; full-detent quadrature decoding. 10 Hz redraw, no network work on UI task.
- Network worker receives latest selection via length-one queue; overwrites obsolete selection requests. Performs bounded requests with 4 s timeout, retries 3/6/12/24/60 seconds plus jitter. UI discards replies for older selection generations.
- Model stores selection, group, page, timestamp, observer-configured flag, element age, cached telemetry, 48 vectors, at most 8 passes. JSON streaming/filtering and strict bounds, not entire active catalogue in memory.
- Catalogue: GET /api/v1/satellites?group=stations&limit=16&offset=0; retain one page, load adjacent pages at boundaries. Validate IDs as uint32_t, not 16-bit. Group selection menu follows /status; no guessed group IDs.
- State every 3 s; orbit track samples=48 every 60 s; passes hours=24 every 60 s or after selection/mask change (500 ms dial settling). Status every 60 s. Never query CelesTrak from device.
- Globe: orthographic projection of wireframe sphere and server ECEF orbit, clip hidden hemisphere; server track is frozen at its timestamp, so label it. Initial globe omits coastlines. Do not imply predicted positions are live measurements.
- Telemetry: altitude/speed, lat/lon, azimuth/elevation, age and timestamp. Observer unset means look angles are reference values and must be hidden.
- Passes: show rise/culmination/set, direction, maximum elevation; geometric passes, not guaranteed optical visibility. Filter sky_path before parsing; fetch details only after pass selection. 404 detail means refresh list because IDs expire after backend restart.
- HOLD freezes the displayed model and labels its UTC; resume requests a fresh sample. OFFLINE/STALE after 10 s without state. Show separate old-elements (>7 days), old-catalogue and HTTP warnings. Never retain data from the previously selected satellite as current.

## Hosting/configuration

Copy include/orbit_config.example.h to include/orbit_config.h (ignored). Set Wi-Fi, API_BASE_URL without trailing slash, optional bearer token and PEM root CA. LAN HTTP must be explicitly enabled; HTTPS must validate hostname/CA and sync clock with NTP before connecting. No setInsecure fallback. Do not commit credentials.

Use LAN PC address, not 127.0.0.1. Start server with run.py --host 0.0.0.0 --no-browser; allow only local-network traffic. WSL networking may require forwarding/firewall setup.

Future cloud: HTTPS reverse proxy + device bearer authentication. MVP does not validate tokens; gateway must enforce them. Protect POST /observer separately. Saved observer is server-global; use explicit lat/lon for per-device pass requests and add per-device state endpoint before using its look angles on shared hosting. Preserve .data on persistent disk. No assumption about which host provider you choose.

## Starter scope

src/main.cpp demonstrates real state polling and filtered JSON on a worker task, green telemetry, live/hold and grid/detail toggles. Encoder and dial/globe/pass screens are specified above for PR3 and are not implemented in this starter. State selection is fixed to ISS/stations until catalogue implementation. This distinction matters before ordering/final printing.

PlatformIO: pio run -d firmware; then upload/monitor with the correct port. Direct dependencies are pinned; compile validation passed with the pinned PlatformIO environment. Acceptance: compile; real ISS response; 409 observer unset; 404 selection; 503 cold catalogue; malformed/oversized JSON; unplug Wi-Fi while controls stay responsive; HTTPS bad CA rejected; HOLD sample timestamp frozen; reboot cache and expired pass IDs; encoder rapid turns; power stability; USB strain relief; panel fit coupon.

Build validation: PlatformIO success; static RAM 46,576 bytes (14.2%), flash 904,501 bytes (27.1%). This does not measure runtime TLS/JSON peak memory or validate PSRAM, display wiring or network behaviour on hardware. Starter rejects responses without Content-Length or above 4096 bytes; gateway must preserve this header.
