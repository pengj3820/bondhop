"""Step 5: layering metadata for the viewer.
  * clips/<bottom>_tuck.png : where a tucked-in top may show (above the bottom's waistband)
  * clips/<coat>_inner.png  : where inner layers may show under a coat (inside its outline, per row)
  * manifest.json           : catalog + QA + file paths
"""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from common import ASSETS, RAW

HERE = Path(__file__).parent
CAT = json.load(open(HERE / "catalog.json"))
L = json.load(open(HERE / "landmarks.json"))


def alpha(gid):
    return np.asarray(Image.open(ASSETS / "layers" / f"{gid}.png"))[..., 3] > 127


def save_mask(m, p):
    m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2)
    Image.fromarray((m * 255).astype(np.uint8), "L").save(p)


def tuck_clip(a):
    h, w = a.shape
    top_edge = np.full(w, -1)
    band = a.copy()
    band[: L["waist_y"] - 80] = False
    band[L["hip_y"] + 40:] = False  # waistband lives here
    cols = np.where(band.any(0))[0]
    top_edge[cols] = band[:, cols].argmax(0)
    waist = int(np.median(top_edge[cols])) if len(cols) else L["waist_y"]
    top_edge[top_edge < 0] = waist
    top_edge = cv2.GaussianBlur(top_edge.astype(np.float32)[None], (0, 0), 6)[0] + 6  # tuck just under the band
    yy = np.arange(h)[:, None]
    return yy < top_edge[None, :]


def coat_clip(a):
    h, w = a.shape
    m = np.ones((h, w), bool)
    rows = np.where(a.any(1))[0]
    hem = rows.max()
    for y in rows:
        xs = np.where(a[y])[0]
        m[y] = False
        m[y, xs.min():xs.max() + 1] = True
    m[: rows.min()] = True  # above the collar nothing to clip
    m[hem + 1:] = True
    return cv2.erode(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)


def main():
    (ASSETS / "clips").mkdir(exist_ok=True)
    items = []
    for c in CAT:
        it = dict(c)
        it["layer"] = f"layers/{c['id']}.png"
        qa = RAW / f"{c['id']}_qa.json"
        it["qa"] = json.load(open(qa)) if qa.exists() else None
        a = alpha(c["id"])
        if c["category"] == "bottom":
            save_mask(tuck_clip(a), ASSETS / "clips" / f"{c['id']}_tuck.png")
            it["tuckClip"] = f"clips/{c['id']}_tuck.png"
        if c["category"] == "coat":
            save_mask(coat_clip(a), ASSETS / "clips" / f"{c['id']}_inner.png")
            it["innerClip"] = f"clips/{c['id']}_inner.png"
        items.append(it)
    man = {"canvas": [1024, 1536], "base": "layers/base.png", "landmarks": L, "items": items,
           "order": ["dress", "bottom", "top", "coat"]}
    json.dump(man, open(ASSETS / "manifest.json", "w"), ensure_ascii=False, indent=1)
    print("manifest with", len(items), "items")


if __name__ == "__main__":
    main()
