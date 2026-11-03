"""Direct-garment approach, step 2: fit the generated garment onto the fixed model.

  geometry  <- the 'worn' render (garment drawn on our dress form; the form is known pixel-for-pixel, so the
               garment region is simply where the render differs from the form: a yes/no decision, no alpha)
  pixels    <- the 'ghost' render (garment alone on a transparent background; its alpha is the generator's own)
  fit       <- ghost is registered onto the worn garment region (affine + dense non-rigid flow on signed
               distance fields), parts the generator invented (e.g. the form's torso, coat lining in the
               opening) are trimmed to the worn region, and finally the no-base-visible contract is enforced
               against the model's body.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import align
from common import ASSETS, save_rgba
from extract import enforce_cover, base_visible, envelope, CAT
from regions import SLOTS, editable, parts, protect, y_of

OUT = ASSETS / "direct"


def lab(img):
    return cv2.cvtColor((np.clip(img, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)


def worn_region(worn, form, slot, P):
    """Garment region in the worn render = pixels that are no longer the dress form / backdrop."""
    d = np.linalg.norm(lab(worn) - lab(form), axis=-1)
    d = cv2.GaussianBlur(d, (0, 0), 1.5)
    g = (d > 14).astype(np.uint8)
    g = cv2.morphologyEx(g, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    g = cv2.morphologyEx(g, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab_, st, _ = cv2.connectedComponentsWithStats(g)
    keep = np.zeros(n, bool)
    if n > 1:
        keep[1:] = st[1:, cv2.CC_STAT_AREA] >= 0.03 * st[1:, cv2.CC_STAT_AREA].max()
    g = keep[lab_]
    # fill pin-holes
    inv = (~g).astype(np.uint8)
    n, lab_, st, _ = cv2.connectedComponentsWithStats(inv)
    small = np.zeros(n, bool)
    small[1:] = st[1:, cv2.CC_STAT_AREA] < 300
    g |= small[lab_]
    return g & editable(slot, P)


def sdf(mask):
    m = mask.astype(np.uint8)
    return (cv2.distanceTransform(1 - m, cv2.DIST_L2, 5) - cv2.distanceTransform(m, cv2.DIST_L2, 5)).astype(np.float32)


def register(ghost_rgba, target):
    """Warp the ghost garment so its silhouette matches the target region."""
    h, w = target.shape
    ga = ghost_rgba[..., 3] > 0.5
    # affine on blurred masks
    t = cv2.GaussianBlur(target.astype(np.float32), (0, 0), 6)
    s = cv2.GaussianBlur(ga.astype(np.float32), (0, 0), 6)
    warp = np.eye(2, 3, dtype=np.float32)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6)
    for sc in (0.25, 0.5):
        ts, ss = cv2.resize(t, None, fx=sc, fy=sc), cv2.resize(s, None, fx=sc, fy=sc)
        ww = warp.copy()
        ww[:, 2] *= sc
        try:
            _, ww = cv2.findTransformECC(ts, ss, ww, cv2.MOTION_AFFINE, crit, None, 5)
            ww[:, 2] /= sc
            warp = ww
        except cv2.error:
            pass
    g = cv2.warpAffine(ghost_rgba, warp, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
    # dense non-rigid: optical flow between clipped signed distance fields
    def norm(x):
        return ((np.clip(x, -40, 40) + 40) / 80 * 255).astype(np.uint8)
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    flow = dis.calc(norm(sdf(target)), norm(sdf(g[..., 3] > 0.5)), None)
    flow = cv2.GaussianBlur(flow, (0, 0), 6)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    g = cv2.remap(g, xx + flow[..., 0], yy + flow[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    return g, warp


def fit(gid):
    slot = CAT[gid]["slot"]
    P = parts()
    form = np.asarray(Image.open(ASSETS / "mannequin.png").convert("RGB")).astype(np.float32) / 255
    worn_img = Image.open(OUT / f"{gid}_worn.png").convert("RGB")
    fm = np.asarray(Image.open(ASSETS / "mannequin_mask.png")).astype(np.float32) / 255
    # the worn render may drift a little: register it to the form first (silhouette outside the slot band)
    y0, y1 = (y_of(v) for v in SLOTS[slot]["band"])
    anchor = np.ones(fm.shape, bool)
    anchor[max(0, y0 - 20):y1 + 20] = False
    worn = np.asarray(worn_img).astype(np.float32) / 255
    try:
        wa, b, a = align.estimate(worn_img, fm, anchor)
        if a >= b:
            worn = align.apply(worn, wa, fm.shape)
    except cv2.error:  # edits on the form are already ~pixel aligned; registration is only a safety net
        pass
    target = worn_region(worn, form, slot, P)

    ghost = np.asarray(Image.open(OUT / f"{gid}_ghost.png").convert("RGBA")).astype(np.float32) / 255
    g, _ = register(ghost, target)
    rgb, alpha = g[..., :3], g[..., 3]
    # trim what the generator invented outside the worn garment region (soft 1.5px edge where trimmed)
    keep = cv2.GaussianBlur(cv2.dilate(target.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 1.0)
    alpha = alpha * np.clip(keep * 1.6 - 0.3, 0, 1)
    # areas of the worn region the ghost lacks (e.g. the ghost shrank): fill from the worn render itself
    lack = target & (alpha < 0.5) & cv2.erode(target.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    rgb = np.where(lack[..., None], worn, rgb)
    alpha = np.where(lack, 1.0, alpha)

    prot = protect(slot, P)
    alpha = alpha * (~prot)
    m_base = np.asarray(Image.open(ASSETS / "person_mask.png")).astype(np.float32) / 255
    s_dummy = np.zeros_like(alpha)
    stats = {"lack_filled_px": int(lack.sum()), "worn_iou": round(float(((alpha > 0.5) & target).sum() / max(((alpha > 0.5) | target).sum(), 1)), 3)}
    for it in range(4):
        rgb, alpha, c = enforce_cover(rgb, alpha, None, prot, s_dummy, s_dummy, m_base)
        stats["cover_filled_px"] = stats.get("cover_filled_px", 0) + c["filled_px"]
        stats["cover_grown_px"] = stats.get("cover_grown_px", 0) + c["grown_px"]
        if not (base_visible(alpha, prot, m_base) > 0.01).any():
            break
    stats["base_visible_px"] = int((base_visible(alpha, prot, m_base) > 0.01).sum())
    save_rgba(np.clip(rgb, 0, 1), np.clip(alpha, 0, 1), OUT / f"{gid}_layer.png")
    Image.fromarray(target.astype(np.uint8) * 255).save(OUT / f"{gid}_target.png")
    print(gid, stats, flush=True)


if __name__ == "__main__":
    for gid in sys.argv[1:]:
        fit(gid)
