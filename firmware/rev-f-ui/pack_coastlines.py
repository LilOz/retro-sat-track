"""Pack the bundled Natural Earth 1:110m land rings into centidegrees."""

import json
import sys
from pathlib import Path


def main(source: Path, destination: Path) -> None:
    data = json.loads(source.read_text(encoding="utf-8"))
    points = []
    sizes = []
    for feature in data["features"]:
        geometry = feature["geometry"]
        polygons = geometry["coordinates"]
        if geometry["type"] == "Polygon":
            polygons = [polygons]
        elif geometry["type"] != "MultiPolygon":
            raise ValueError(f"Unsupported land geometry: {geometry['type']}")
        for polygon in polygons:
            for ring in polygon:
                packed = [(round(lat * 100), round(lon * 100)) for lon, lat in ring]
                sizes.append(len(packed))
                points.extend(packed)

    with destination.open("w", encoding="utf-8") as output:
        output.write(
            "// Generated from the bundled public-domain Natural Earth land data.\n"
        )
        output.write("struct CoastPoint { int16_t latitude; int16_t longitude; };\n")
        output.write("constexpr CoastPoint coastPoints[] = {\n")
        for i in range(0, len(points), 6):
            row = ", ".join(f"{{{lat}, {lon}}}" for lat, lon in points[i : i + 6])
            output.write(f"    {row},\n")
        output.write("};\nconstexpr uint16_t coastRingSizes[] = {\n")
        for i in range(0, len(sizes), 12):
            output.write("    " + ", ".join(map(str, sizes[i : i + 12])) + ",\n")
        output.write("};\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
