"""Direct-garment approach, step 0: a headless grey dress form with EXACTLY the fixed model's body shape and
pose (neck down, incl. arms, hands, legs), so the image model draws garments already in our pose/proportions."""
import cv2
import numpy as np
from PIL import Image

from common import ASSETS, load_rgb, save_rgb
from regions import L

GREY = np.array([0.72, 0.72, 0.73], np.float32)


def main():
    rgb = load_rgb(ASSETS / "model_photo.png")
    m = np.asarray(Image.open(ASSETS / "person_mask.png")).astype(np.float32) / 255
    h, w = m.shape
    body = m.copy()
    body[: L["neck_y"] - 6] = 0  # headless: cut at the neck
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    shade = np.clip(lum / np.percentile(lum[body > 0.5], 90), 0.45, 1.05)[..., None]
    bg = np.full_like(rgb, 0.93)
    soft = cv2.GaussianBlur(body, (0, 0), 0.7)[..., None]
    out = GREY * shade * soft + bg * (1 - soft)
    # flat neck top like a dress form
    y = L["neck_y"] - 6
    out[y - 1:y + 2] = np.where(body[y + 3, :, None] > 0.5, GREY * 0.8, out[y - 1:y + 2])
    save_rgb(out, ASSETS / "mannequin.png")
    Image.fromarray((body * 255).astype(np.uint8)).save(ASSETS / "mannequin_mask.png")


if __name__ == "__main__":
    main()
