# Firmware status — Rev F USB terminal

The Rev F desktop prototype uses the same 480×320 drawable size as the planned MSP3525/ST7796U panel. The ESP32 display and encoder adapter is still pending. The legacy Adafruit HX8357D client remains a separate PlatformIO build for Rev E. [Legacy build and configuration](revision-E.md) · [Rev F wiring](../hardware/ASSEMBLY.md) · [UI concept](../hardware/UI-CONCEPT.md)

## Run the Rev F preview

Use Ubuntu on Windows with WSLg, or Linux with an X11 session. Install the build dependencies once.

```sh
sudo apt install build-essential cmake libx11-dev python3
```

Build and launch from the repository root in Ubuntu.

```sh
cmake -S firmware/rev-f-ui -B build/orbit-rev-f -DCMAKE_BUILD_TYPE=Release
cmake --build build/orbit-rev-f --parallel
./build/orbit-rev-f/orbit-rev-f
```

| Key | Action |
| --- | --- |
| Left / Right or Up / Down | Open Categories from Earth, then move through categories, satellites, or pass rows |
| Enter / Space | Open a category or select a satellite. On Earth, push to open Details, then Passes |
| Esc / Backspace | Simulate a long press. Enter rotation mode on Earth or go back from another view |
| H / G | Freeze or resume the displayed clock / toggle the Earth grid |
| Q | Close the preview |

While `ROTATE` is visible, use Left or Up to rotate the globe west and Right or Down to rotate it east. Enter or Space keeps the orientation for this session. Esc or Backspace cancels the change.

**SAMPLE** includes a grouped offline catalog and illustrative orbit and telemetry data for ISS, TIANGONG, HST, and NOAA 19. Other catalog entries display an unavailable state. The simulated UTC pass clock starts at 14:23:28 with a sample London observer. Positions and telemetry are fixed, and the countdown advances while the window runs. For actual orbital data, use the [PC tracker](../docs/PC-GUIDE.md).

The portable C++17 renderer and navigation are in `rev-f-ui/orbit_ui.*`. They take a bounded scene, a UTC timestamp, encoder actions, and an RGB565 drawing surface. The desktop adapter provides the X11 surface and key mapping. The build packs map data from the existing bundled Natural Earth coastlines. Configure with `-DORBIT_BUILD_DESKTOP=OFF` to build the shared library without X11.

## Next implementation

1. Bring up the delivered **MSP3525 no-touch, ST7796U** with its vendor example, explicit 480×320 landscape orientation and verified 3.3 V logic/backlight control. Generic ST7796S initialization must be checked against the U variant; no assumed drop-in driver compatibility.
2. Replace HX8357D, remove PowerBoost/GPIO2 handling, retain configurable API URL, bounded JSON, background network requests and CA-validated HTTPS. Keep Wi-Fi credentials in ignored `include/orbit_config.h`. The MVP needs an authenticated HTTPS gateway before public hosting; sending a bearer token alone does not secure it.
3. Add debounced quadrature/push input. Rotate to select a satellite; click to open details; click/hold navigation must be tested. Keep HOLD, GRID and intensity dial as inexpensive tactile controls.
4. Feed the shared UI with live catalogue, state, orbit and pass data. Use paginated catalogues, stale-data indicators and selection-generation checks.

State can poll every 3 s; tracks (`samples=48`) and geometric passes every 60 s. Fetch group IDs from `/api/v1/status`. Preserve NORAD IDs as uint32; bound lists. Observer-unset views must hide local look angles. See the [PC/API guide](../docs/PC-GUIDE.md) for endpoints, hosting and checks.
