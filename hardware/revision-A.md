# Superseded revision A — historical reference

# ORBIT tabletop terminal — revision A

Prototype design after PR1. Not yet fit-tested or print-approved.

## Recommended build

Macintosh-inspired upright ivory body, inset black bezel, broad chin, decorative disk-slot motif, metal toggles and two knurled knobs. No Apple branding. 120 wide × 95 deep × 150 high mm. USB 5 V power, no battery.

ESP32-S3-DevKitC-1 N8R8 plus Adafruit 1770 2.8-inch ILI9341 SPI TFT, landscape 320×240. Black background, phosphor-green text and dim green grid. This is a colour TFT displaying green. ESP8266-12F can demonstrate a smaller monochrome client, but its GPIO/RAM and bare-module power/programming requirements make it a poor choice here.

| Control | Behaviour |
|---|---|
| Left encoder / push | Select satellite / cycle orbit, telemetry, passes |
| Right B10K dial | Orbit zoom; pass elevation mask 0–30°; telemetry intensity |
| LIVE/HOLD toggle | Freeze displayed sample, visibly label HOLD |
| GRID toggle | Grid or additional detail |

Controls operate the device UI. Browser synchronisation would require an additional shared session/control API. Server continues orbit propagation.

## Bill of materials

GBP figures are budget allowances, not checked supplier quotes. Shipping/VAT may vary.

| Qty | Part | Allowance |
|---:|---|---:|
| 1 | ESP32-S3-DevKitC-1 N8R8 | £12–20 |
| 1 | Adafruit 1770 2.8-inch SPI ILI9341 TFT | £25–40 |
| 1 | Panel EC11-type encoder with push, 6 mm shaft, nominal 7 mm bushing | £2–5 |
| 1 | B10K linear panel pot, 6 mm shaft, nominal 7 mm bushing | £1–3 |
| 2 | Mini SPST ON/OFF metal toggle, M6 bushing | £3–6 total |
| 2 | 20–24 mm diameter knobs, 6 mm shaft, grub screw | £3–8 total |
| 1 | Reputable USB 5 V supply ≥1 A | £5–10 |
| 1 set | Matching board USB lead and panel extension | £4–8 |
| 1 set | Perfboard, headers, stranded wire, connectors, heat shrink | £9–18 |
| 12 | M3×16 screws/nuts, verify lengths during assembly | £2–4 |
| 4 | M2.5 screen screws/nuts and nylon spacers | £2–4 |
| 4 | Rubber feet | £1–3 |
| 1 each | 100 nF pot filter capacitor; optional 470 µF ≥10 V bulk capacitor | £1–2 |

Allow £70–130 excluding filament. Verify board USB connector before buying extension.

Bambu PLA Matte Ivory White (11100): case/front/rear. Matte Charcoal: bezel, tray, purchased or printed knobs. Optional Matte Latte Brown (11800): chin detail. Separate parts mean no AMS required. Unvalidated material estimate 250–400 g.

## CAD

`cad/OrbitTerminal.py` generates a new Fusion document with editable separate front, shell, rear, tray and bezel components. The official local Fusion MCP is now connected and has created the refined design in Fusion. Live exports are in `cad/generated`: native F3D, assembly and per-part STEP, five STL files, preview and validation reports. All five exported printable parts are single solids with healthy Fusion features; STL checks confirm closed two-manifold meshes and expected dimensions. This is geometric validation, not physical fit approval. The original generator remains a simpler draft; `cad/generated/BuildOrbit.py.txt` records the exact refined MCP construction source.

Coordinates: X horizontal, Y vertical, Z depth, mm. Front 120×150×3. Screen provisional 58×44 aperture centred at (60,100). Encoder/pot at (32,35)/(88,35), 7.4 holes; toggles at (18,65)/(102,65), 6.4 holes. 2.4 shell walls. Rear opening and removable cover. Four short corner bosses at each face use M3 through screws with accessible nuts inside. Measure nut/screw reach before final assembly. Tray has adjustable slots; screen adapter and USB connector plate must be finalised against purchased parts.

Measure screen glass, visible area, PCB, holes, cable clearance and offsets before final printing. Aperture is provisional, not a verified supplier dimension. Do not clamp glass. Leave 0.3–0.5 mm part clearance. Check bushing threads span 3 mm panel plus washers. Check knobs do not foul toggles. Keep antenna end near plastic rear, clear of metal/wiring.

Fusion: Utilities → Scripts and Add-ins → add Python script folder → run OrbitTerminal. Save F3D; export components STEP and bodies STL/3MF. Script dimensions are editable constants, not fully constrained user parameters. Add exterior fillets after fit verification.

P1S: 0.4 nozzle, 0.2 layers, 4 walls, 15% gyroid, matching PLA profile. Front/rear flat, inside facing up; shell front rim on bed/open rear upwards. Inspect bridges/supports in Bambu Studio. Print a control-hole/screen-aperture coupon first. Keep PLA away from hot sunlight.

## Next PRs and gates

1. PR2 bench firmware: telemetry, configurable URL/credentials, all controls, TLS and errors; compile and breadboard test.
2. PR3 embedded UI: paginated satellite selection, 48-sample orbit globe, pass list and polar plot, timestamp/freshness/observer warnings.
3. PR4 enclosure: exact purchased part drawings, screen/USB adapters, screw fit, fillets/vents, coupon then full assembly; validated F3D/STEP/STL.
4. PR5 hosting: HTTPS reverse proxy, device credentials/rate limiting, protect observer writes, persist .data. Multi-device hosting needs per-device observers or explicit pass coordinates.

Sources: [Fusion MCP](https://help.autodesk.com/view/fusion360/ENU/?guid=FMCP-OVERVIEW), [display](https://www.adafruit.com/product/1770), [display drawings](https://learn.adafruit.com/adafruit-2-8-and-3-2-color-tft-touchscreen-breakout-v2/downloads), [ESP8266](https://www.espressif.com/sites/default/files/documentation/0a-esp8266ex_datasheet_en.pdf), [PLA colours](https://bambu-lab-global.myshopify.com/products/pla-matte).

## Live Fusion revision

Refined case: 120×150×95 mm shell/front/rear assembly; bezel and purchased knob envelopes project beyond the front. Rounded 6 mm exterior corners, 2.4 mm walls, round M3 mounting bosses, rear ventilation and USB service opening. Colours applied in Fusion. Five printable components: front, shell, rear, bezel, loose tray. Knobs, switches and green screen are reference geometry only. Tray attachment, exact screen bracket and bolted USB adapter are still unfinished. STL parts retain their assembly coordinates; use Bambu Studio drop-to-bed and appropriate orientation. F3D is locally exported; the Fusion cloud document has not been saved.
