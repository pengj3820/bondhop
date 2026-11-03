"""Preview compositor (same rules as the web viewer): base -> bottom -> top -> coat, or tucked: top under bottom."""
import json
import sys
from pathlib import Path

from PIL import Image

from common import ASSETS

L = json.load(open(Path(__file__).with_name("landmarks.json")))
BG = (236, 234, 230, 255)


def compose(ids, tuck=False):
    lay = lambda g: Image.open(ASSETS / "layers" / f"{g}.png")  # noqa: E731
    by = {g.split("_")[0]: g for g in ids}
    out = Image.new("RGBA", (1024, 1536), BG)
    out.alpha_composite(lay("base"))
    order = ["dress"] + (["top", "bottom"] if tuck else ["bottom", "top"]) + ["coat"]
    for cat in order:
        if cat in by:
            out.alpha_composite(lay(by[cat]))
    return out.convert("RGB")


if __name__ == "__main__":
    combos = [s.split("+") for s in sys.argv[2:]]
    tiles = [compose(c, tuck=c[-1] == "tuck") for c in combos]
    sheet = Image.new("RGB", (len(tiles) * 400, 600), "white")
    for i, t in enumerate(tiles):
        sheet.paste(t.crop((112, 40, 912, 1240)).resize((400, 600)), (i * 400, 0))
    sheet.save(sys.argv[1])
