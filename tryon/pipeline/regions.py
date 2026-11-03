"""Per-category editable regions on the fixed canvas (y-bands derived from landmarks.json)."""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from common import ASSETS

L = json.load(open(Path(__file__).with_name("landmarks.json")))
FLOOR_Y = 1460

BANDS = {  # (y_top, y_bottom)
    "top": (L["chin_y"] + 8, L["crotch_y"] + 30),
    "bottom": (L["waist_y"] - 50, FLOOR_Y),
    "dress": (L["chin_y"] + 8, FLOOR_Y),
    "coat": (L["chin_y"] + 8, FLOOR_Y),
}
# zone that a garment of this category must cover (coverage check): (y0, y1), body pixels only
MUST_COVER = {
    "top": (L["bust_y"] - 40, L["waist_y"], 420, 605),
    "bottom": (L["hip_y"], L["crotch_y"] + 40, 390, 635),
    "dress": (L["bust_y"], L["crotch_y"] + 40, 420, 605),
    "coat": None,  # open coats intentionally show the front
}


def masks():
    person = np.asarray(Image.open(ASSETS / "person_mask.png")) > 127
    body = np.asarray(Image.open(ASSETS / "body_mask.png")) > 127
    protect = person & ~body  # head, neck-above-chin, hands, feet: never part of a garment
    protect = cv2.dilate(protect.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~body
    return person, body, protect


def editable(category):
    person, body, protect = masks()
    h, w = body.shape
    y0, y1 = BANDS[category]
    m = np.zeros((h, w), bool)
    m[y0:y1] = True
    return m & ~protect
