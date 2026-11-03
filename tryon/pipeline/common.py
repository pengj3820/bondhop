"""Shared helpers for the try-on asset pipeline."""
import base64
import io
import os
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
RAW = ASSETS / "raw"
W, H = 1024, 1536
IMAGE_MODEL = os.environ.get("TRYON_IMAGE_MODEL", "gpt-image-2")


def client():
    from openai import OpenAI
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "sk-dummy"), max_retries=4, timeout=600)


def b64_to_img(b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")


def load_rgb(p) -> np.ndarray:
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255.0


def save_rgb(arr: np.ndarray, p):
    Image.fromarray((np.clip(arr, 0, 1) * 255).round().astype(np.uint8)).save(p)


def save_rgba(rgb: np.ndarray, alpha: np.ndarray, p):
    a = np.clip(alpha, 0, 1)[..., None]
    Image.fromarray((np.clip(np.concatenate([rgb, a], -1), 0, 1) * 255).round().astype(np.uint8), "RGBA").save(p)


def _collect(stream) -> Image.Image:
    final = None
    for ev in stream:
        t = getattr(ev, "type", "")
        if t.endswith("completed") and getattr(ev, "b64_json", None):
            final = ev.b64_json
        elif getattr(ev, "b64_json", None):
            final = final or None
    if final is None:
        raise RuntimeError("no completed image in stream")
    return b64_to_img(final)


def generate(prompt: str, quality="high", tries=3) -> Image.Image:
    last = None
    for _ in range(tries):
        try:
            s = client().images.generate(model=IMAGE_MODEL, prompt=prompt, size=f"{W}x{H}", quality=quality,
                                         stream=True, partial_images=2)
            return _collect(s)
        except Exception as e:  # noqa: BLE001 - transient upstream errors
            last = e
            print("retry after", repr(e)[:120], flush=True)
    raise last


def edit(images, prompt: str, mask=None, quality="high", tries=3, model=None, fidelity=None) -> Image.Image:
    last = None
    for _ in range(tries):
        try:
            files = [open(p, "rb") for p in images]
            kw = dict(model=model or IMAGE_MODEL, image=files if len(files) > 1 else files[0], prompt=prompt,
                      size=f"{W}x{H}", quality=quality, stream=True, partial_images=2)
            if fidelity:
                kw["input_fidelity"] = fidelity
            if mask is not None:
                kw["mask"] = open(mask, "rb")
            return _collect(client().images.edit(**kw))
        except Exception as e:  # noqa: BLE001
            last = e
            print("retry after", repr(e)[:160], flush=True)
    raise last
