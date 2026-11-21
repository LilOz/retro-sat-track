# Power options

**Rev F is USB-powered:** one USB-A → USB-C data cable into the ESP32 board. Use an existing regulated 5 V supply (1 A minimum; 2 A preferred). Power the selected display from the board's USB-derived 5 V rail, with common ground. No internal battery, charger, boost converter or power-link circuit is required.

For programming, unplug the cable from the wall supply and connect that same cable to the PC. Do not connect a second USB supply simultaneously. See [assembly](ASSEMBLY.md).

[Rev E rechargeable documentation](revisions/reve/BATTERY.md) and [CAD](cad/generated-reve/) are retained as a separate historical build. Its battery, charger, cradle and extra wiring are **not included** in Rev F or its price. They cannot simply be wired into Rev F without revisiting the power path and mounts.
