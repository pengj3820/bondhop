"""Preview compositor (same rules as the web viewer): layers sorted by slot z; base body at z=0."""
import json
import sys
from pathlib import Path

from PIL import Image

from common import ASSETS

HERE = Path(__file__).parent
SLOTS = json.load(open(HERE / "slots.json"))
CAT = {c["id"]: c for c in json.load(open(HERE / "catalog.json"))}
BG = (236, 234, 230, 255)


def compose(ids, tuck=False):
    lay = lambda g: Image.open(ASSETS / "layers" / f"{g}.png")  # noqa: E731
    items = [("base", 0)] + [(g, SLOTS[CAT[g]["slot"]]["z"]) for g in ids if g in CAT]
    if tuck:  # tucked top goes under the bottom
        items = [(g, z if g == "base" or CAT[g]["slot"] != "top" else 29) for g, z in items]
    out = Image.new("RGBA", (1024, 1536), BG)
    for g, _ in sorted(items, key=lambda t: t[1]):
        out.alpha_composite(lay(g))
    return out.convert("RGB")


if __name__ == "__main__":
    combos = [s.split("+") for s in sys.argv[2:]]
    tiles = [compose([c for c in combo if c != "tuck"], tuck="tuck" in combo) for combo in combos]
    sheet = Image.new("RGB", (len(tiles) * 400, 600), "white")
    for i, t in enumerate(tiles):
        sheet.paste(t.crop((112, 40, 912, 1240)).resize((400, 600), Image.LANCZOS), (i * 400, 0))
    sheet.save(sys.argv[1])
