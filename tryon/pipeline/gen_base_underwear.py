"""Swap the display base's round-neck bodysuit for minimal strapless nude underwear, so low necklines,
strapless corsets and slip dresses don't reveal the bodysuit. Only the torso is replaced (registered and
pasted back), the silhouette stays identical, so every extracted layer remains valid."""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import align
from common import ASSETS, RAW, edit, load_rgb, save_rgb, save_rgba
from regions import L, parts

PROMPT = ("Edit this photo: change the neckline of her nude-beige dance leotard to a strapless straight-across "
          "tube neckline, like a strapless ballet leotard: the leotard now starts at the bust line, so her shoulders, "
          "collarbones and the top of the chest are bare skin. Everything else about the leotard stays the same. "
          "Keep the face, hair, arms, hands, legs, feet, body shape, pose, framing, lighting and the grey "
          "background exactly the same. Photorealistic.")


def main():
    raw = RAW / "base_underwear_gen.png"
    if not raw.exists():
        edit([ASSETS / "model_photo.png"], PROMPT, model="gpt-image-1.5", fidelity="high").save(raw)
    P = parts()
    person = P["person"]
    gen_img = Image.open(raw).convert("RGB")
    anchor = P["head"] | P["feet"] | P["hands"]
    anchor = cv2.dilate(anchor.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    warp, b, a = align.estimate(gen_img, person.astype(np.float32), anchor)
    gen = align.apply(np.asarray(gen_img).astype(np.float32) / 255, warp, person.shape)
    print(f"anchor IoU {b:.3f} -> {a:.3f}")
    torso = np.zeros_like(person)
    torso[L["neck_y"] - 5:L["crotch_y"] + 40] = True
    torso &= cv2.erode(person.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)  # keep our outline
    torso &= ~P["hands"]
    w = cv2.GaussianBlur(torso.astype(np.float32), (0, 0), 3)[..., None]
    orig = load_rgb(ASSETS / "model_photo.png")
    out = gen * w + orig * (1 - w)
    save_rgb(out, ASSETS / "model_display.png")
    m = np.asarray(Image.open(ASSETS / "person_mask.png")).astype(np.float32) / 255
    save_rgba(out, m, ASSETS / "layers" / "base.png")
    json.dump({"affine": warp.tolist(), "iou_before": b, "iou_after": a}, open(RAW / "base_underwear_align.json", "w"))


if __name__ == "__main__":
    main()
