"""Turn the display base's round-neck bodysuit into a strapless one without an image model
(image APIs refuse "less clothing" edits): the bodysuit straps and neckline above the bust line are
filled from the model's own surrounding skin (inpainting) and a soft tube-top edge is drawn at the cut. Silhouette is untouched, so every garment layer stays aligned."""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from common import ASSETS, save_rgba

L = json.load(open(Path(__file__).with_name("landmarks.json")))
CUT_Y = L["bust_y"] - 28          # strapless edge
X0, X1 = 398, 628                  # between the armholes (straps included)
Y0 = L["neck_y"] + 15


# bodysuit area above the strapless cut (straps + below the round neckline), traced once on the fixed model
SUIT_ABOVE_CUT = [(414, 364), (440, 354), (445, 357), (465, 385), (490, 405), (512, 414), (535, 407), (560, 387),
                  (575, 360), (580, 354), (607, 362), (616, CUT_Y + 2), (405, CUT_Y + 2)]


def main():
    rgb = np.asarray(Image.open(ASSETS / "model_photo.png").convert("RGB"))
    person = np.asarray(Image.open(ASSETS / "person_mask.png")) > 127
    hole = np.zeros(rgb.shape[:2], np.uint8)
    cv2.fillPoly(hole, [np.array(SUIT_ABOVE_CUT, np.int32)], 1)
    hole = cv2.dilate(hole, np.ones((7, 7), np.uint8))
    hole[CUT_Y:] = 0
    hole &= person.astype(np.uint8)
    # fill from the model's own surrounding skin only: first replace the backdrop by the nearest body pixel
    from scipy.ndimage import distance_transform_edt
    inner = cv2.erode(person.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    _, (iy, ix) = distance_transform_edt(~inner, return_indices=True)
    src = rgb[iy, ix]
    # inpaint at half resolution for smoother shading
    small = cv2.resize(src, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    hs = cv2.resize(hole, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
    hs = cv2.dilate(hs, np.ones((3, 3), np.uint8))
    filled = cv2.inpaint(small, hs * 255, 12, cv2.INPAINT_TELEA)
    filled = cv2.resize(filled, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    filled = cv2.GaussianBlur(filled, (0, 0), 2.0)
    rng = np.random.default_rng(0)
    grain = cv2.GaussianBlur(rng.normal(0, 2.0, rgb.shape[:2]).astype(np.float32), (0, 0), 0.7)[..., None]
    filled = filled + grain
    w = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 2.0)[..., None]
    res = filled * w + rgb.astype(np.float32) * (1 - w)
    # no drawn edge: low necklines (sweetheart corsets) dip below the cut and would reveal it
    res = np.clip(res, 0, 255) / 255
    Image.fromarray((res * 255).astype(np.uint8)).save(ASSETS / "model_display.png")
    m = np.asarray(Image.open(ASSETS / "person_mask.png")).astype(np.float32) / 255
    save_rgba(res, m, ASSETS / "layers" / "base.png")


if __name__ == "__main__":
    main()
