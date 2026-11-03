"""Step 2: from the chosen model photo build
  - person_mask.png   : person silhouette (rembg)
  - body_mask.png     : skin/bodysuit area from neck to ankle, hands excluded  (where garments may sit)
  - model_chroma.png  : same photo with body_mask painted chroma green (keeps shading) -> used for generation
  - layers/base.png   : the display layer (original photo, background transparent)
"""
import json

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

from common import ASSETS, load_rgb, save_rgb, save_rgba

L = json.load(open(__file__.replace("prep_model.py", "landmarks.json")))
GREEN = np.array([0.0, 0.85, 0.25], np.float32)


def main():
    src = Image.open(ASSETS / "model_photo.png").convert("RGB")
    rgb = load_rgb(ASSETS / "model_photo.png")
    h, w = rgb.shape[:2]
    m = np.asarray(remove(src, session=new_session("isnet-general-use"), only_mask=True)).astype(np.float32) / 255
    Image.fromarray((m * 255).astype(np.uint8)).save(ASSETS / "person_mask.png")

    yy, xx = np.mgrid[0:h, 0:w]
    body = (m > 0.5) & (yy >= L["neck_y"]) & (yy <= L["ankle_y"])
    lo, hi = L["hand_x_inner"]
    body &= ~((yy > L["wrist_y"]) & ((xx < lo) | (xx > hi)))
    body = cv2.morphologyEx(body.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    Image.fromarray(body.astype(np.uint8) * 255).save(ASSETS / "body_mask.png")

    # chroma version: green with original luminance so folds/shading stay readable to the model
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    shade = np.clip(lum / np.percentile(lum[body], 90), 0.35, 1.05)[..., None]
    soft = cv2.GaussianBlur(body.astype(np.float32), (0, 0), 1.0)[..., None]
    chroma = rgb * (1 - soft) + (GREEN * shade) * soft
    save_rgb(chroma, ASSETS / "model_chroma.png")

    (ASSETS / "layers").mkdir(exist_ok=True)
    save_rgba(rgb, m, ASSETS / "layers" / "base.png")
    print("body px", body.sum(), "person px", (m > 0.5).sum())


if __name__ == "__main__":
    main()
