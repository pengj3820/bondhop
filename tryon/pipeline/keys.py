"""Chroma key colours. Garments are generated on a body painted in a key colour that the garment
itself doesn't contain (green by default, magenta for green garments)."""
import numpy as np

KEYS = {
    "green": np.array([0.0, 0.85, 0.25], np.float32),
    "magenta": np.array([0.85, 0.05, 0.80], np.float32),
}


def keyness(img, key):
    """(strength, ratio): how much the key dominates a pixel, absolute and relative to brightness."""
    if key == "green":
        s = img[..., 1] - np.maximum(img[..., 0], img[..., 2])
        ref = img[..., 1]
    else:  # magenta
        s = np.minimum(img[..., 0], img[..., 2]) - img[..., 1]
        ref = np.minimum(img[..., 0], img[..., 2])
    return s, s / (ref + 1e-3)


def despill(rgb, key):
    """Remove key-colour cast: limit the key channel(s) to the level of the other channel(s)."""
    out = rgb.copy()
    if key == "green":
        out[..., 1] = np.minimum(out[..., 1], np.maximum(out[..., 0], out[..., 2]) + 0.02)
    else:  # magenta = red+blue over green
        excess = np.clip(np.minimum(out[..., 0], out[..., 2]) - out[..., 1] - 0.02, 0, None)
        out[..., 0] -= excess
        out[..., 2] -= excess
    return out
