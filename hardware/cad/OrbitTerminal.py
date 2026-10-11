"""Fusion prototype generator. Run in Fusion, not ordinary Python."""

from __future__ import annotations

import traceback

import adsk.core
import adsk.fusion

W, H, D, WALL = 120, 150, 95, 2.4


def run(context: object) -> None:
    app = adsk.core.Application.get()
    try:
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent

        def component(name: str) -> adsk.fusion.Component:
            c = root.occurrences.addNewComponent(adsk.core.Matrix3D.create()).component
            c.name = name
            return c

        def plane(c: adsk.fusion.Component, z: float) -> adsk.fusion.ConstructionPlane:
            i = c.constructionPlanes.createInput()
            i.setByOffset(
                c.xYConstructionPlane, adsk.core.ValueInput.createByReal(z / 10)
            )
            return c.constructionPlanes.add(i)

        def rect(
            c: adsk.fusion.Component,
            name: str,
            x: float,
            y: float,
            z: float,
            w: float,
            h: float,
            depth: float,
            cut: bool = False,
            join: bool = False,
        ) -> adsk.fusion.ExtrudeFeature:
            sk = c.sketches.add(plane(c, z))
            sk.name = name
            sk.sketchCurves.sketchLines.addTwoPointRectangle(
                adsk.core.Point3D.create(x / 10, y / 10, 0),
                adsk.core.Point3D.create((x + w) / 10, (y + h) / 10, 0),
            )
            op = (
                adsk.fusion.FeatureOperations.CutFeatureOperation
                if cut
                else (
                    adsk.fusion.FeatureOperations.JoinFeatureOperation
                    if join
                    else adsk.fusion.FeatureOperations.NewBodyFeatureOperation
                )
            )
            inp = c.features.extrudeFeatures.createInput(sk.profiles.item(0), op)
            inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(depth / 10))
            return c.features.extrudeFeatures.add(inp)

        def hole(
            c: adsk.fusion.Component,
            x: float,
            y: float,
            z: float,
            r: float,
            depth: float,
        ) -> None:
            sk = c.sketches.add(plane(c, z))
            sk.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(x / 10, y / 10, 0), r / 10
            )
            inp = c.features.extrudeFeatures.createInput(
                sk.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation
            )
            inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(depth / 10))
            c.features.extrudeFeatures.add(inp)

        front = component("Ivory front panel")
        rect(front, "Panel", 0, 0, 0, W, H, 3)
        rect(front, "Screen aperture", 31, 78, 0, 58, 44, 3, True)
        for x, y, r in [(32, 35, 3.7), (88, 35, 3.7), (18, 65, 3.2), (102, 65, 3.2)]:
            hole(front, x, y, 0, r, 3)
        rect(front, "Decorative disk recess", 44, 17, 0, 32, 2, 1, True)
        shell = component("Ivory open backed shell")
        rect(shell, "Outer shell", 0, 0, 3, W, H, D - 3)
        rect(
            shell, "Open cavity", WALL, WALL, 3, W - 2 * WALL, H - 2 * WALL, D - 3, True
        )
        # Short corner bosses with accessible nuts behind each face.
        for x, y in [(5, 5), (115, 5), (5, 145), (115, 145)]:
            for z in [3, D - 8]:
                rect(shell, "Screw boss", x - 3, y - 3, z, 6, 6, 8, join=True)
                hole(shell, x, y, z, 1.7, 8)
            hole(front, x, y, 0, 1.7, 3)
        rear = component("Ivory removable rear")
        rect(rear, "Rear cover", 0, 0, D, W, H, 3)
        for x, y in [(5, 5), (115, 5), (5, 145), (115, 145)]:
            hole(rear, x, y, D, 1.7, 3)
        rect(rear, "USB service opening", 45, 12, D, 30, 15, 3, True)
        for x in range(30, 91, 10):
            rect(rear, "Vent", x, 125, D, 3, 12, 3, True)
        tray = component("Charcoal electronics tray - drill to board")
        # Separate part shown outside assembly for accessible export.
        rect(tray, "Tray", 140, 0, 0, 100, 65, 3)
        for x in [148, 226]:
            rect(tray, "Mount slot", x, 8, 0, 4, 45, 3, True)
        bezel = component("Charcoal screen bezel")
        rect(bezel, "Bezel", 27, 74, -2, 66, 52, 2)
        rect(bezel, "View window", 31, 78, -2, 58, 44, 2, True)
        app.activeViewport.fit()
        app.userInterface.messageBox(
            "Prototype created. Verify screen/USB mounts and fasteners before printing. Save F3D and export parts manually."
        )
    except Exception:
        app.userInterface.messageBox(traceback.format_exc())
