"""Step 3: generate each garment ON the chroma model (masked edit), then hard paste-back outside the mask."""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from common import ASSETS, RAW, edit, load_rgb, save_rgb
from regions import editable, masks, BANDS
import align
import warp_fix
from warp_fix import L

# gpt-image-1.5 + input_fidelity=high keeps head/legs pixel-aligned; gpt-image-2 drifts more.
EDIT_MODEL = os.environ.get("TRYON_EDIT_MODEL", "gpt-image-1.5")
CAT = json.load(open(Path(__file__).with_name("catalog.json")))

PROMPT = (
    "Edit this studio photo: dress the woman in {desc}. "
    "IMPORTANT: the flat bright green is a chroma-key bodysuit, NOT clothing. Wherever the new garment does not "
    "cover the body (neck, arms, legs, any gap or opening), keep that area exactly the same flat bright green — "
    "never paint skin over the green. Only this one garment, no other clothes or accessories. "
    "The garment must fit this exact body and pose naturally and fully cover the body where it is worn, "
    "with no gaps at its edges. Keep the face, hair, hands, feet, pose, framing and the grey background unchanged; "
    "no cast shadows on the background. Neutral white studio light on the garment, true-to-life fabric colors, "
    "photorealistic fashion catalog quality."
)


def api_mask(region, path):
    a = np.where(region, 0, 255).astype(np.uint8)  # transparent = editable
    rgba = np.zeros(region.shape + (4,), np.uint8)
    rgba[..., 3] = a
    Image.fromarray(rgba, "RGBA").save(path)


def run(item):
    gid, cat = item["id"], item["category"]
    region = editable(cat)
    mpath = RAW / f"mask_{cat}.png"
    api_mask(region, mpath)
    # Measured: without an API mask gpt-image-1.5 keeps the figure aligned to ~1px (with a mask the arms drift
    # ~50px and large masks produce a dark glowing backdrop). The model is protected by our own
    # registration + hard paste-back instead. TRYON_API_MASK=top,... re-enables the API mask per category.
    use_mask = [c for c in os.environ.get("TRYON_API_MASK", "").split(",") if c]
    out = edit([ASSETS / "model_chroma.png"], PROMPT.format(desc=item["desc"]),
               mask=mpath if cat in use_mask else None,
               model=EDIT_MODEL, fidelity="high")
    out.save(RAW / f"{gid}_gen.png")
    finish(gid, cat)
    print("generated", gid, flush=True)


def anchor_mask(cat):
    person, body, protect = masks()
    y0, y1 = BANDS[cat]
    p = protect.copy()
    p[L["wrist_y"] - 20:L["crotch_y"] + 200, :L["hand_x_inner"][0] + 20] = False
    p[L["wrist_y"] - 20:L["crotch_y"] + 200, L["hand_x_inner"][1] - 20:] = False
    a = cv2.dilate(p.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    rows = np.ones_like(a)
    rows[y0 - 20:y1 + 20] = False
    return a | rows


def finish(gid, cat):
    region = editable(cat)
    person, _, _ = masks()
    gen_img = Image.open(RAW / f"{gid}_gen.png").convert("RGB")
    warp, before, after = align.estimate(gen_img, person.astype(np.float32), anchor_mask(cat))
    gen = align.apply(np.asarray(gen_img).astype(np.float32) / 255, warp, person.shape)
    gsil = align.silhouette(Image.fromarray((gen * 255).astype(np.uint8))) > 0.5
    aw = warp_fix.arm_warp(person, gsil, person.shape)
    arm_info = None
    if aw is not None:
        mx, my, arm_info = aw
        gen = cv2.remap(gen, mx, my, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    gsil2 = align.silhouette(Image.fromarray((np.clip(gen, 0, 1) * 255).astype(np.uint8))) > 0.5
    hands = cv2.dilate((masks()[2]).astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    hands[:L["wrist_y"]] = False
    hand_iou = float((gsil2 & person & hands).sum() / max(((gsil2 | person) & hands).sum(), 1))
    json.dump({"affine": warp.tolist(), "anchor_iou_before": before, "anchor_iou_after_affine": after,
               "arms": arm_info, "hand_iou_final": hand_iou}, open(RAW / f"{gid}_align.json", "w"), indent=1)
    print(f"  {gid}: anchor IoU {before:.3f} -> {after:.3f}; hand IoU after arm fix {hand_iou:.3f}; "
          f"arm shift {[round(v['shift_px'], 1) for v in arm_info.values()] if arm_info else None}", flush=True)
    base = load_rgb(ASSETS / "model_chroma.png")
    soft = cv2.GaussianBlur(cv2.erode(region.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 1.2)[..., None]
    save_rgb(gen * soft + base * (1 - soft), RAW / f"{gid}_onmodel.png")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--finish"]:
        for c in CAT:
            if c["id"] in sys.argv[2:]:
                finish(c["id"], c["category"])
        sys.exit()
    ids = set(sys.argv[1:])
    items = [c for c in CAT if not ids or c["id"] in ids]
    with ThreadPoolExecutor(4) as ex:
        for f in [ex.submit(run, it) for it in items]:
            try:
                f.result()
            except Exception as e:  # noqa: BLE001
                print("FAILED", repr(e)[:200], flush=True)
