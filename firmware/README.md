# Firmware status — Rev F USB terminal

**The checked-in firmware is the legacy Rev E Adafruit HX8357D telemetry starter. It does not drive the new MSP3525/ST7796U panel.** No ST7796 port, encoder navigation, globe or pass UI is claimed in this hardware/CAD PR. [Legacy build/configuration](revision-E.md) · [Rev F wiring](../hardware/ASSEMBLY.md) · [UI concept](../hardware/UI-CONCEPT.md).

The PC browser application and JSON API work today. The legacy client compiles and polls real ISS telemetry, but its display driver and battery warning are specific to Rev E. Do not flash it expecting the new hardware or mock-up to work.

## Next implementation

1. Bring up the delivered **MSP3525 no-touch, ST7796U** with its vendor example, explicit 480×320 landscape orientation and verified 3.3 V logic/backlight control. Generic ST7796S initialization must be checked against the U variant; no assumed drop-in driver compatibility.
2. Replace HX8357D, remove PowerBoost/GPIO2 handling, retain configurable API URL, bounded JSON, background network requests and CA-validated HTTPS. Keep Wi-Fi credentials in ignored `include/orbit_config.h`. The MVP needs an authenticated HTTPS gateway before public hosting; sending a bearer token alone does not secure it.
3. Add debounced quadrature/push input. Rotate to select a satellite; click to open details; click/hold navigation must be tested. Keep HOLD, GRID and intensity dial as inexpensive tactile controls.
4. Build the three concept views: ~40 mm Earth with 3–5 markers and selected orbit; details; next passes. Use paginated catalogues, stale-data indicators and selection-generation checks. Do not present sample artwork as live data.

State can poll every 3 s; tracks (`samples=48`) and geometric passes every 60 s. Fetch group IDs from `/api/v1/status`. Preserve NORAD IDs as uint32; bound lists. Observer-unset views must hide local look angles. See the [PC/API guide](../docs/PC-GUIDE.md) for endpoints, hosting and checks.
