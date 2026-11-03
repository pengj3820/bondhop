"""Slot geometry on the fixed canvas (from landmarks.json + slots.json)."""
import json
import re
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from common import ASSETS

HERE = Path(__file__).parent
L = json.load(open(HERE / "landmarks.json"))
SLOTS = {k: v for k, v in json.load(open(HERE / "slots.json")).items() if not k.startswith("_")}


def y_of(v):
    if isinstance(v, (int, float)):
        return int(v)
    m = re.fullmatch(r"(\w+?)([+-]\d+)?", v)
    return int(L[m.group(1) + "_y"] + int(m.group(2) or 0))


def _m(name):
    return np.asarray(Image.open(ASSETS / f"{name}.png").convert("L")) > 127


def parts():
    return {k: _m(f) for k, f in dict(person="person_mask", body="body_mask", head="part_head", hair="part_hair",
                                       face="part_face", hands="part_hands", feet="part_feet").items()}


def protect(slot, P=None):
    """Pixels that can never belong to a garment of this slot."""
    P = P or parts()
    allow = set(SLOTS[slot]["allow"])
    p = P["face"] | (P["head"] & ~P["hair"])
    if "hair" not in allow:
        p |= P["hair"]
    if "hands" not in allow:
        p |= P["hands"]
    if "feet" not in allow:
        p |= P["feet"]
    return cv2.dilate(p.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~(P["body"] & ~(P["hands"] | P["feet"]))


def editable(slot, P=None):
    P = P or parts()
    y0, y1 = (y_of(v) for v in SLOTS[slot]["band"])
    m = np.zeros(P["body"].shape, bool)
    m[max(0, y0):y1] = True
    return m & ~protect(slot, P)


def keyed_area(slot, P=None):
    """Pixels that were key colour in the generation input."""
    P = P or parts()
    k = P["body"].copy()
    if "hair" in SLOTS[slot]["allow"]:
        k |= P["hair"]
    return k


def must_cover(slot):
    mc = SLOTS[slot].get("must_cover")
    return None if not mc else (y_of(mc[0]), y_of(mc[1]), mc[2], mc[3])
