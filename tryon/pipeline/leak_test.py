"""Leak test: recolour the base body (neck to ankles, incl. hands/feet) to a loud colour, put each garment
layer on top, and measure how much of that colour shows inside the garment's own outline.
Anything that shows there is 'base showing through' that a similar-looking base would hide."""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from common import ASSETS
from regions import parts

HERE = Path(__file__).parent
CAT = {c["id"]: c for c in json.load(open(HERE / "catalog.json"))}
SLOTS = json.load(open(HERE / "slots.json"))
LOUD = np.array([1.0, 0.0, 0.85], np.float32)


def loud_base():
    base = np.asarray(Image.open(ASSETS / "layers" / "base.png")).astype(np.float32) / 255
    P = parts()
    body = P["body"] & ~P["face"]
    lum = base[..., :3] @ np.array([0.299, 0.587, 0.114], np.float32)
    out = base.copy()
    out[body, :3] = (LOUD * np.clip(lum / 0.8, 0.4, 1.1)[..., None])[body]
    return out, body


def envelope(alpha):
    """Where the garment claims to be: its solid area with small notches/slits closed."""
    g = (alpha > 0.5).astype(np.uint8)
    closed = cv2.morphologyEx(g, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(1 - closed)
    holes = np.zeros(n, bool)
    holes[1:] = st[1:, cv2.CC_STAT_AREA] < 4000
    return closed.astype(bool) | holes[lab]


def test(gid, out_png=None):
    lb, body = loud_base()
    L = np.asarray(Image.open(ASSETS / "layers" / f"{gid}.png")).astype(np.float32) / 255
    a = L[..., 3:4]
    comp = L[..., :3] * a + lb[..., :3] * (1 - a)
    if SLOTS[CAT[gid]["slot"]]["z"] < 0:  # behind the body
        comp = lb[..., :3] * lb[..., 3:4] + L[..., :3] * a * (1 - lb[..., 3:4])
    env = envelope(L[..., 3]) & body
    vis = (1 - L[..., 3]) * env  # how much base shows inside the outline
    sheer = CAT[gid].get("sheer", False)
    res = {"id": gid, "leak_px": int((vis > 0.5).sum()), "partial_px": int(((vis > 0.05) & (vis <= 0.5)).sum()),
           "sheer": sheer}
    if out_png:
        bg = np.full_like(comp, 0.92)
        m = lb[..., 3:4] if SLOTS[CAT[gid]["slot"]]["z"] >= 0 else np.maximum(lb[..., 3:4], a)
        m = np.maximum(m, a)
        img = comp * m + bg * (1 - m)
        Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(out_png)
    return res


if __name__ == "__main__":
    out_dir = Path(sys.argv[1])
    ids = sys.argv[2:] or list(CAT)
    for g in ids:
        if (ASSETS / "layers" / f"{g}.png").exists():
            print(test(g, out_dir / f"leak_{g}.png"))
