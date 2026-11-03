"""Slice approach, step 1: generate each item as a FULL photo of the fixed model wearing it (real skin, no
chroma key), registered to the canvas and pasted back outside the slot band. No matting: at runtime whole
pixels are taken from these photos (model included) and stitched where they agree."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import align
import warp_fix
from common import ASSETS, edit, load_rgb, save_rgb
from regions import SLOTS, editable, parts, y_of

HERE = Path(__file__).parent
CAT = {c["id"]: c for c in json.load(open(HERE / "catalog.json"))}
OUT = ASSETS / "slice"
OUT.mkdir(exist_ok=True)
BASE = ASSETS / "model_photo.png"  # the strapless display base gets refused by moderation

PROMPT = ("Edit this studio photo: dress the woman in {desc}. Only add this one item over what she is wearing; "
          "no other clothes, shoes or accessories. It must fit this exact body and pose naturally. Keep her face, "
          "skin, body, pose, framing, lighting and the plain light grey background exactly unchanged. "
          "Photorealistic fashion catalogue quality.")


def anchor_mask(slot, P):
    y0, y1 = (y_of(v) for v in SLOTS[slot]["band"])
    a = P["head"].copy()
    if "feet" not in SLOTS[slot]["allow"]:
        a |= P["feet"]
    a = cv2.dilate(a.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    rows = np.ones_like(a)
    rows[max(0, y0 - 20):y1 + 20] = False
    return a | rows


def run(gid):
    item = CAT[gid]
    slot = item["slot"]
    raw = OUT / f"{gid}_gen_{BASE.stem}.png"
    if not raw.exists():
        desc = item["desc"].split(". The flat bright green")[0]
        try:
            img = edit([BASE], PROMPT.format(desc=desc), model="gpt-image-1.5", fidelity="high")
        except Exception as e:  # noqa: BLE001
            if "safety" not in str(e):
                raise
            img = edit([BASE], PROMPT.format(desc=desc), model="gpt-image-2")
        img.save(raw)
    P = parts()
    person = P["person"]
    g = Image.open(raw).convert("RGB")
    warp, b, a = align.estimate(g, person.astype(np.float32), anchor_mask(slot, P))
    gen = align.apply(np.asarray(g).astype(np.float32) / 255, warp, person.shape)
    if "hands" not in SLOTS[slot]["allow"] and slot != "wings":
        gsil = align.silhouette(Image.fromarray((gen * 255).astype(np.uint8))) > 0.5
        aw = warp_fix.arm_warp(person, gsil, person.shape)
        if aw is not None and max(v["shift_px"] for v in aw[2].values()) < 90:
            gen = cv2.remap(gen, aw[0], aw[1], cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    region = editable(slot, P)
    base = load_rgb(BASE)
    w = cv2.GaussianBlur(cv2.erode(region.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 2)[..., None]
    save_rgb(gen * w + base * (1 - w), OUT / f"{gid}_full.png")
    print(gid, f"IoU {b:.3f}->{a:.3f}", flush=True)


if __name__ == "__main__":
    with ThreadPoolExecutor(4) as ex:
        for gid, f in [(g, ex.submit(run, g)) for g in sys.argv[1:]]:
            try:
                f.result()
            except Exception as e:  # noqa: BLE001
                print("FAILED", gid, repr(e)[:160], flush=True)
