"""Non-rigid correction: image models tend to move the arms a little while dressing the model.
We locate the hands (never covered by garments) in the generated image and on the fixed model,
then thin-plate-spline warp the generated image so hands return to place while shoulders, torso,
head and legs stay fixed. Sleeves move with the arms."""
import json
from pathlib import Path

import cv2
import numpy as np

L = json.load(open(Path(__file__).with_name("landmarks.json")))


def hand_points(sil: np.ndarray, side: str):
    """Fingertip + hand centroid from a person silhouette (bool HxW)."""
    h, w = sil.shape
    lo, hi = L["hand_x_inner"]
    reg = np.zeros_like(sil)
    y0, y1 = L["wrist_y"] - 10, min(h, L["crotch_y"] + 160)
    if side == "L":
        reg[y0:y1, :lo + 20] = True
    else:
        reg[y0:y1, hi - 20:] = True
    m = sil & reg
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8))
    if n <= 1:
        return None
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    ys, xs = np.nonzero(lab == k)
    tip_y = ys.max()
    tip_x = xs[ys >= tip_y - 3].mean()
    sel = ys >= tip_y - 90
    return [(float(tip_x), float(tip_y)), (float(xs[sel].mean()), float(ys[sel].mean()))]


def _tps_fit(src, dst):
    # maps src (base coords) -> displacement to dst (gen coords)
    n = len(src)
    d = np.linalg.norm(src[:, None] - src[None], axis=-1)
    K = np.where(d > 0, d * d * np.log(d + 1e-9), 0)
    P = np.hstack([np.ones((n, 1)), src])
    A = np.zeros((n + 3, n + 3))
    A[:n, :n] = K + np.eye(n) * 1e-3
    A[:n, n:] = P
    A[n:, :n] = P.T
    b = np.zeros((n + 3, 2))
    b[:n] = dst
    return np.linalg.solve(A, b)


def _tps_eval(coef, src, pts):
    d = np.linalg.norm(pts[:, None] - src[None], axis=-1)
    U = np.where(d > 0, d * d * np.log(d + 1e-9), 0)
    return U @ coef[:-3] + coef[-3] + pts @ coef[-2:]


def arm_warp(base_sil, gen_sil, shape):
    """Return (map_x, map_y, info) to remap gen -> base frame, or None if hands not found."""
    h, w = shape
    src, dst, info = [], [], {}
    for side in "LR":
        b, g = hand_points(base_sil, side), hand_points(gen_sil, side)
        if b is None or g is None:
            return None
        info[side] = {"base": b, "gen": g, "shift_px": float(np.hypot(g[0][0] - b[0][0], g[0][1] - b[0][1]))}
        src += b
        dst += g
    # fixed anchors: shoulders, neck, torso, legs, head, frame
    fixed = [(L["hand_x_inner"][0] + 25, L["shoulder_y"]), (L["hand_x_inner"][1] - 25, L["shoulder_y"]),
             (w / 2, L["chin_y"]), (w / 2, L["waist_y"]), (w / 2, L["crotch_y"]),
             (w / 2 - 90, L["knee_y"]), (w / 2 + 90, L["knee_y"]), (w / 2, L["ankle_y"]),
             (w / 2, 100), (0, 0), (w, 0), (0, h), (w, h), (0, h / 2), (w, h / 2),
             (w / 2 - 110, L["crotch_y"] + 100), (w / 2 + 110, L["crotch_y"] + 100)]
    src += fixed
    dst += fixed
    src, dst = np.array(src, float), np.array(dst, float)
    coef = _tps_fit(src, dst)
    step = 8
    gy, gx = np.mgrid[0:h + step:step, 0:w + step:step]
    pts = np.stack([gx.ravel(), gy.ravel()], 1).astype(float)
    m = _tps_eval(coef, src, pts).reshape(gy.shape + (2,)).astype(np.float32)
    mx = cv2.resize(m[..., 0], (w + step, h + step), interpolation=cv2.INTER_LINEAR)[:h, :w]
    my = cv2.resize(m[..., 1], (w + step, h + step), interpolation=cv2.INTER_LINEAR)[:h, :w]
    # resize of a grid sampled every `step` px is approximately aligned; good enough for smooth TPS fields
    return mx, my, info
