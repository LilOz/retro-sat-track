# Rev E CAD deliverables

- `ORBIT-RevE.f3d`: editable as-built Fusion design, complete enclosure visible.
- `ORBIT-RevE-inspection.f3d`: same design with shell/rear hidden for inspection.
- `ORBIT-RevE-assembly.step`: complete assembly including simplified purchased-part references.
- Seven numbered STL/STEP pairs: printable parts only; units millimetres, assembly coordinates retained.
- PNG previews, `validation.json`, `interference.json` and `mesh-validation.json`: exported-model evidence.

Import the complete F3D into Fusion to edit the checked design. Do not print the assembly STEP or electronic references. Physical fit and electrical testing remain outstanding; see the current [assembly guide](../../ASSEMBLY.md).

`BuildRevE.py.txt` is the consolidated Fusion Python generator; it creates a new document. `ExportRevE.py.txt` checks and exports the active Rev E design. Rename a copy to `.py` and use Fusion's script runner, or execute via the local Fusion MCP. Change `OUT` if a different export directory is needed. The live design was built in smaller MCP stages with corrections; the consolidated generator has been syntax-checked but not separately replayed end-to-end, so its timeline count can differ from the archived as-built model.

`CheckMeshes.py.txt` records the binary STL edge/dimension check. Run with Python from the parent of an `orbit-cad-reve` export directory. It checks seven files, repeated vertices, edge incidence and 256 mm bounding dimensions; it is not a self-intersection or physical-printability proof.

Manufacturer geometry: [Adafruit 2050 Eagle board](https://github.com/adafruit/3.5inch-TFT-Breakout-PCB) and [PowerBoost 1000C Rev B board](https://github.com/adafruit/Adafruit-PowerBoost-1000C), consulted 2026-10-13. TFT tab outline and electronic component volumes are simplified. The source dimensions and provisional values are listed in the assembly guide.
