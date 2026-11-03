"""Step 4: pull the garment off the model as an aligned RGBA layer, then run the coverage check.

alpha rules (per pixel, inside the editable region only):
  * where the fixed model had green body  -> garment if the pixel is no longer chroma green
  * where the fixed model had background  -> garment if the pixel differs from the (re-estimated) background
  * head / hands / feet are never garment
coverage check: body pixels left uncovered in thin slivers along garment edges are filled
(garment grows over them); large uncovered areas in the category's must-cover zone fail QA.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from common import ASSETS, RAW, load_rgb, save_rgba
from regions import MUST_COVER, editable, masks

SLIVER = 21
CAT = {c["id"]: c for c in json.load(open(Path(__file__).with_name("catalog.json")))}


def greenness(img):
    return img[..., 1] - np.maximum(img[..., 0], img[..., 2])


def background_model(img):
    """Smooth, spatially varying background estimate of the generated image itself
    (image models re-light the backdrop): inpaint the figure out at low resolution."""
    import align
    from PIL import Image
    sil = align.silhouette(Image.fromarray((img * 255).astype(np.uint8))) > 0.2
    green = greenness(img) > 0.1
    fg = cv2.dilate((sil | green).astype(np.uint8), np.ones((31, 31), np.uint8))
    s = 4
    small = cv2.resize((img * 255).astype(np.uint8), None, fx=1 / s, fy=1 / s, interpolation=cv2.INTER_AREA)
    m = cv2.resize(fg, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
    bg = cv2.inpaint(small, m * 255, 9, cv2.INPAINT_TELEA)
    bg = cv2.GaussianBlur(bg, (0, 0), 3)
    return cv2.resize(bg, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255


def extract(gid):
    cat = CAT[gid]["category"]
    img = load_rgb(RAW / f"{gid}_onmodel.png")
    person, body, protect = masks()
    region = editable(cat)
    h, w = body.shape

    g = greenness(img)
    # shading-invariant key: how dominant green is relative to the pixel's own brightness
    gr = g / (img[..., 1] + 1e-3)
    a_body = np.clip((0.45 - gr) / (0.45 - 0.2), 0, 1) * (g > 0.03) + (g <= 0.03)
    import align
    from PIL import Image
    # foreground matte of the generated image (person + garment) from a matting model;
    # robust for white-on-light garments where colour difference to the backdrop is tiny
    fg = align.silhouette(Image.fromarray((img * 255).astype(np.uint8)), "birefnet-general-lite")
    bg = background_model(img)
    diff = np.abs(img - bg).max(-1)
    a_diff = np.clip((diff - 0.05) / (0.12 - 0.05), 0, 1)
    a_bg = np.maximum(fg, a_diff * (fg > 0.05))  # matte, sharpened by colour difference where matte is unsure
    a_bg = np.minimum(a_bg, np.clip((0.12 - g) / 0.08, 0, 1))  # green spill on background is not garment

    body_soft = cv2.dilate(body.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    # 1px choke on the backdrop side kills light halos from the matte
    a_bg = np.minimum(a_bg, cv2.GaussianBlur(cv2.erode(a_bg, np.ones((3, 3), np.uint8)), (0, 0), 0.7))
    alpha = np.where(body_soft, np.minimum(a_body, a_bg), a_bg)  # garment = not key green AND not backdrop
    alpha[~region | protect] = 0

    # cleanup: drop specks, fill pin-holes (but keep real openings like necklines / open coats)
    hard = (alpha > 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(hard)
    keep = np.zeros(n, bool)
    if n > 1:
        keep[1:] = st[1:, cv2.CC_STAT_AREA] >= max(400, 0.03 * st[1:, cv2.CC_STAT_AREA].max())
    alpha[~keep[lab]] = 0
    inv = (alpha <= 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(inv)
    small_holes = np.zeros(n, bool)
    small_holes[1:] = st[1:, cv2.CC_STAT_AREA] < 150
    alpha[small_holes[lab]] = 1

    # ---- coverage check (garment must not leave the body peeking out at its edges) ----
    garment = alpha > 0.5
    exposed = body & ~garment & region
    # body strips narrower than SLIVER px running along the garment edge = garment failed to cover the body
    # (e.g. a sleeve drawn a little off the arm). Wider exposed areas (forearms, necklines) are intentional.
    k = np.ones((SLIVER, SLIVER), np.uint8)
    opened = cv2.morphologyEx(exposed.astype(np.uint8), cv2.MORPH_OPEN, k).astype(bool)
    near = cv2.dilate(garment.astype(np.uint8), k).astype(bool)
    slivers = exposed & ~opened & near
    # fill slivers: alpha=1, colour pulled from the nearby garment
    fill_src = (img * 255).astype(np.uint8)
    hole = (slivers | ((alpha > 0.02) & (alpha < 0.98) & body)).astype(np.uint8) * 255
    filled = cv2.inpaint(fill_src, hole, 5, cv2.INPAINT_TELEA).astype(np.float32) / 255
    rgb = np.where(hole[..., None] > 0, filled, img)
    alpha[slivers] = 1
    alpha[(alpha > 0.02) & body & near] = np.maximum(alpha[(alpha > 0.02) & body & near], 0.98)

    # despill green from edges that sat on the key colour
    keyed = ((g > 0.03) & (gr > 0.2)).astype(np.uint8)  # pixels that are (partly) key green in the generated image
    edge = (cv2.dilate((alpha < 0.98).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
            | cv2.dilate(keyed, np.ones((13, 13), np.uint8)).astype(bool)) & (alpha > 0)
    mx = np.maximum(rgb[..., 0], rgb[..., 2])
    rgb[..., 1] = np.where(edge, np.minimum(rgb[..., 1], mx + 0.02), rgb[..., 1])

    qa = {"sliver_px_filled": int(slivers.sum()), "garment_px": int((alpha > 0.5).sum())}
    mc = MUST_COVER[cat]
    if mc:
        zone = body.copy()
        zone[:mc[0]] = False
        zone[mc[1]:] = False
        zone[:, :mc[2]] = False
        zone[:, mc[3]:] = False
        cov = float((alpha[zone] > 0.5).mean())
        qa["must_cover_ratio"] = round(cov, 4)
        qa["pass"] = cov >= 0.97
    else:
        qa["pass"] = True
    leak = body & ~(alpha > 0.5) & region
    qa["body_visible_in_region_px"] = int(leak.sum())

    (ASSETS / "layers").mkdir(exist_ok=True)
    save_rgba(rgb, alpha, ASSETS / "layers" / f"{gid}.png")
    vis = np.zeros((h, w, 3), np.float32) + 0.15
    vis[garment] = (0.6, 0.6, 0.6)
    vis[slivers] = (1, 0.2, 0.2)
    vis[leak] = np.maximum(vis[leak], (0.1, 0.4, 1))
    cv2.imwrite(str(RAW / f"{gid}_coverage.png"), (vis[..., ::-1] * 255).astype(np.uint8))
    json.dump(qa, open(RAW / f"{gid}_qa.json", "w"), indent=1)
    print(gid, qa, flush=True)
    return qa


if __name__ == "__main__":
    ids = sys.argv[1:] or list(CAT)
    if len(ids) == 1:
        extract(ids[0])
    else:  # one process per garment keeps peak memory low (two ONNX matting models on CPU)
        import subprocess
        for gid in ids:
            subprocess.run([sys.executable, __file__, gid], check=False)
