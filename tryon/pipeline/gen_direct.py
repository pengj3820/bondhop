"""Direct-garment approach, step 1: the image model draws the garment on our grey dress form (same body shape
and pose as the fixed model) and returns ONLY the garment on a transparent background (ghost-mannequin style).
No matting: the garment's alpha comes from the generator."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import ASSETS, edit

HERE = Path(__file__).parent
CAT = {c["id"]: c for c in json.load(open(HERE / "catalog.json"))}
OUT = ASSETS / "direct"
OUT.mkdir(exist_ok=True)

WEAR = (
    "Dress this grey dress form in {desc}. Only this one garment. It must fit this exact body shape and pose "
    "naturally. Keep the dress form, its pose, the framing and the light grey background unchanged. "
    "Photorealistic fabric, neutral studio light, true-to-life colours."
)
GHOST = (
    "Make the grey dress form invisible, ghost-mannequin style: output ONLY the garment exactly as it is in this "
    "photo - same position, size, shape, folds and colours, pixel-aligned - on a fully transparent background. "
    "Remove the dress form, its arms, legs and neck, and the background completely. Where the dress form was "
    "visible through an opening of the garment, show transparency (not the garment's inside)."
)
PROMPT = (
    "Ghost-mannequin product photo. Dress this grey dress form in {desc}. The garment must fit this exact body "
    "shape and pose: follow the shoulders, arm angle, waist and hips of the form precisely, keep the same "
    "framing, scale and position in the image. Then make the dress form completely invisible: output ONLY the "
    "garment on a fully transparent background, nothing else (no body, no skin, no mannequin, no shadow, no "
    "background). Where the garment is open (neckline, cuffs, hem) show the inside of the garment as a "
    "ghost-mannequin photo would. Photorealistic fabric, neutral studio light, true-to-life colours."
)


def run2(gid):
    """Two-step: wear on the form (keeps placement), then remove the form with a transparent output."""
    desc = CAT[gid]["desc"].split(". The flat bright green")[0]
    worn = OUT / f"{gid}_worn.png"
    if not worn.exists():
        try:
            im = edit([ASSETS / "mannequin.png"], WEAR.format(desc=desc), model="gpt-image-1.5", fidelity="high")
        except Exception as e:  # noqa: BLE001
            if "safety" not in str(e):
                raise
            im = edit([ASSETS / "mannequin.png"], WEAR.format(desc=desc), model="gpt-image-2")
        im.save(worn)
    img = edit([worn], GHOST, model="gpt-image-1.5", fidelity="high", background="transparent")
    img.save(OUT / f"{gid}_ghost.png")
    print(gid, "done", flush=True)


def run(gid):
    desc = CAT[gid]["desc"].split(". The flat bright green")[0]
    img = edit([ASSETS / "mannequin.png"], PROMPT.format(desc=desc), model="gpt-image-1.5", fidelity="high",
               background="transparent")
    img.save(OUT / f"{gid}_raw.png")
    a = img.getchannel("A")
    print(gid, "alpha range", a.getextrema(), "opaque px", sum(1 for v in a.getdata() if v > 128), flush=True)


MODE = "2"

if __name__ == "__main__":
    with ThreadPoolExecutor(4) as ex:
        for gid, f in [(g, ex.submit(run2 if MODE == "2" else run, g)) for g in sys.argv[1:]]:
            try:
                f.result()
            except Exception as e:  # noqa: BLE001
                print("FAILED", gid, repr(e)[:200], flush=True)
