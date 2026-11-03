"""Step 2: from the chosen model photo build masks and chroma variants.

  person_mask.png         person silhouette
  part_*.png              head / hair / face / hands / feet / body masks
  model_chroma_<key>.png  everything from the neck down (incl. hands and feet) painted in the key colour,
                          keeping the original shading -> generation input for most categories
  model_chroma_<key>_hair.png  same + hair keyed -> generation input for head accessories
  layers/base.png         the display layer (original photo, background transparent)
"""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

from common import ASSETS, load_rgb, save_rgb, save_rgba
from keys import KEYS

L = json.load(open(Path(__file__).with_name("landmarks.json")))


def save_mask(m, name):
    Image.fromarray(m.astype(np.uint8) * 255).save(ASSETS / f"{name}.png")


def main():
    src = Image.open(ASSETS / "model_photo.png").convert("RGB")
    rgb = load_rgb(ASSETS / "model_photo.png")
    h, w = rgb.shape[:2]
    pm = ASSETS / "person_mask.png"
    if pm.exists():
        m = np.asarray(Image.open(pm)).astype(np.float32) / 255
    else:
        m = np.asarray(remove(src, session=new_session("isnet-general-use"), only_mask=True)).astype(np.float32) / 255
        Image.fromarray((m * 255).astype(np.uint8)).save(pm)
    person = m > 0.5
    yy, xx = np.mgrid[0:h, 0:w]
    lo, hi = L["hand_x_inner"]

    head = person & (yy < L["neck_y"])
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    hair = head & (lum < 0.38) & (yy < L["hair_bottom_y"])
    hair = cv2.morphologyEx(hair.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)).astype(bool)
    n, lab, st, _ = cv2.connectedComponentsWithStats(hair.astype(np.uint8))
    if n > 1:  # biggest blob = hair; drops eyes / brows
        hair = lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    face = head & ~hair
    hands = person & (yy > L["wrist_y"]) & ((xx < lo) | (xx > hi))
    feet = person & (yy > L["ankle_y"])
    body = person & (yy >= L["neck_y"])  # neck down, incl. hands & feet
    for k, v in dict(part_head=head, part_hair=hair, part_face=face, part_hands=hands, part_feet=feet,
                     body_mask=body).items():
        save_mask(v, k)

    shade_ref = np.percentile(lum[body], 90)
    for key, col in KEYS.items():
        for suffix, keyed in (("", body), ("_hair", body | hair)):
            shade = np.clip(lum / shade_ref, 0.35, 1.05)[..., None]
            if suffix:  # hair is dark: lift it so the key colour stays saturated
                shade = np.where(hair[..., None], np.clip(lum / 0.3, 0.55, 1.0)[..., None], shade)
            soft = cv2.GaussianBlur(keyed.astype(np.float32), (0, 0), 1.0)[..., None]
            save_rgb(rgb * (1 - soft) + col * shade * soft, ASSETS / f"model_chroma_{key}{suffix}.png")

    (ASSETS / "layers").mkdir(exist_ok=True)
    save_rgba(rgb, m, ASSETS / "layers" / "base.png")
    print({k: int(v.sum()) for k, v in dict(hair=hair, face=face, hands=hands, feet=feet, body=body).items()})


if __name__ == "__main__":
    main()
