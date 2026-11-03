"""Step 5: layering metadata + web assets for the viewer (tryon/web/).
  web/layers/<id>.webp        garment layers (lossless alpha, lossy colour)
  web/thumbs/<id>.webp        catalogue thumbnails
  web/clips/<bottom>_tuck.png where a tucked-in top may show (above that bottom's waistband)
  web/clips/<coat>_inner.png  where inner layers may show under that coat (inside its outline, per row)
  web/manifest.json
"""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from common import ASSETS, RAW
from regions import L, SLOTS

HERE = Path(__file__).parent
WEB = HERE.parent / "web"
CAT = json.load(open(HERE / "catalog.json"))


def alpha(gid):
    return np.asarray(Image.open(ASSETS / "layers" / f"{gid}.png"))[..., 3] > 127


def save_mask(m, p):
    """Clip masks are applied with canvas 'destination-in', which reads alpha: store the mask as alpha."""
    m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.5)
    rgba = np.zeros(m.shape + (4,), np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = (m * 255).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(p, optimize=True)


def tuck_clip(a):
    h, w = a.shape
    band = a.copy()
    band[: L["waist_y"] - 80] = False
    band[L["hip_y"] + 40:] = False
    cols = np.where(band.any(0))[0]
    top_edge = np.full(w, -1.0)
    top_edge[cols] = band[:, cols].argmax(0)
    waist = float(np.median(top_edge[cols])) if len(cols) else L["waist_y"]
    top_edge[top_edge < 0] = waist
    top_edge = cv2.GaussianBlur(top_edge.astype(np.float32)[None], (0, 0), 6)[0] + 8
    return np.arange(h)[:, None] < top_edge[None, :]


def coat_clip(a):
    h, w = a.shape
    m = np.ones((h, w), bool)
    rows = np.where(a.any(1))[0]
    for y in rows:
        xs = np.where(a[y])[0]
        m[y] = False
        m[y, xs.min():xs.max() + 1] = True
    m[: rows.min()] = True
    m[rows.max() + 1:] = True
    return cv2.erode(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)


def to_webp(src: Image.Image, dst, q=88):
    src.save(dst, "WEBP", quality=q, alpha_quality=100, method=6)


def main():
    for d in ("layers", "thumbs", "clips"):
        (WEB / d).mkdir(parents=True, exist_ok=True)
    to_webp(Image.open(ASSETS / "layers" / "base.png"), WEB / "layers" / "base.webp")
    items = []
    for c in CAT:
        p = ASSETS / "layers" / f"{c['id']}.png"
        qa_p = RAW / f"{c['id']}_qa.json"
        if not p.exists() or not qa_p.exists():
            continue
        qa = json.load(open(qa_p))
        if not qa.get("pass"):
            continue
        im = Image.open(p)
        to_webp(im, WEB / "layers" / f"{c['id']}.webp")
        bb = im.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
        th = Image.new("RGBA", im.size, (244, 242, 238, 255))
        th.alpha_composite(im)
        th = th.crop(bb)
        th.thumbnail((180, 180), Image.LANCZOS)
        canvas = Image.new("RGB", (180, 180), (244, 242, 238))
        canvas.paste(th.convert("RGB"), ((180 - th.width) // 2, (180 - th.height) // 2))
        to_webp(canvas, WEB / "thumbs" / f"{c['id']}.webp", q=85)
        it = {k: c[k] for k in ("id", "slot", "name")}
        it.update(layer=f"layers/{c['id']}.webp", thumb=f"thumbs/{c['id']}.webp", sheer=c.get("sheer", False))
        a = alpha(c["id"])
        if c["slot"] == "bottom":
            save_mask(tuck_clip(a), WEB / "clips" / f"{c['id']}_tuck.png")
            it["tuckClip"] = f"clips/{c['id']}_tuck.png"
        if c["slot"] == "coat":
            save_mask(coat_clip(a), WEB / "clips" / f"{c['id']}_inner.png")
            it["innerClip"] = f"clips/{c['id']}_inner.png"
        items.append(it)
    slots = {k: {"z": v["z"], "label": v["label"]} for k, v in SLOTS.items()}
    man = {"canvas": [1024, 1536], "base": "layers/base.webp", "slots": slots, "items": items,
           "rules": {"tuckSlot": "top", "tuckZ": 29, "innerUnderCoat": ["top", "dress", "arms", "neck"],
                     "exclusive": [["dress", "top"], ["dress", "bottom"]]}}
    json.dump(man, open(WEB / "manifest.json", "w"), ensure_ascii=False, indent=1)
    print("manifest with", len(items), "items")


if __name__ == "__main__":
    main()
