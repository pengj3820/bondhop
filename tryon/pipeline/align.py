"""Register a generated image back onto the fixed model canvas.

Image models re-render the whole frame, so the figure drifts by a few pixels / percent of scale.
We estimate an affine warp from the silhouette of parts no garment ever covers (head, hands, feet,
and everything outside the edited band) and warp the generated image back before paste-back.
"""
import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

_SESSIONS = {}


def silhouette(img: Image.Image, model: str = "isnet-general-use") -> np.ndarray:
    """Foreground matte. isnet is fast (registration); birefnet-general-lite is cleaner on
    low-contrast garments such as white stripes on a light backdrop (extraction)."""
    if model not in _SESSIONS:
        _SESSIONS[model] = new_session(model)
    return np.asarray(remove(img, session=_SESSIONS[model], only_mask=True)).astype(np.float32) / 255


def estimate(gen_img: Image.Image, base_sil: np.ndarray, anchor: np.ndarray):
    """Return (2x3 warp mapping base coords -> gen coords, anchor IoU before, after)."""
    gsil = silhouette(gen_img)
    t = cv2.GaussianBlur(base_sil, (0, 0), 4)
    s = cv2.GaussianBlur(gsil, (0, 0), 4)
    warp = np.eye(2, 3, dtype=np.float32)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-6)
    for scale in (0.25, 0.5, 1.0):  # coarse-to-fine
        ts = cv2.resize(t, None, fx=scale, fy=scale)
        ss = cv2.resize(s, None, fx=scale, fy=scale)
        ms = cv2.resize(anchor.astype(np.uint8), None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
        w = warp.copy()
        w[:, 2] *= scale
        _, w = cv2.findTransformECC(ts, ss, w, cv2.MOTION_AFFINE, crit, ms, 5)
        w[:, 2] /= scale
        warp = w
    h, wd = base_sil.shape
    warped = cv2.warpAffine(gsil, warp, (wd, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)

    def iou(a):
        a, b = a[anchor] > 0.5, base_sil[anchor] > 0.5
        return float((a & b).sum() / max((a | b).sum(), 1))

    return warp, iou(gsil), iou(warped)


def apply(arr: np.ndarray, warp, shape):
    h, w = shape
    return cv2.warpAffine(arr, warp, (w, h), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_REPLICATE)
