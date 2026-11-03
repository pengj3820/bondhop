"""Step 3 (offline): generate each garment part ON the chroma model, then register it back to the fixed
canvas and hard-paste everything outside the slot's editable region.

    python gen_garment.py [ids...]          generate + finish
    python gen_garment.py --finish [ids...] redo registration / paste-back only
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import align
import warp_fix
from common import ASSETS, RAW, edit, load_rgb, save_rgb
from regions import L, SLOTS, editable, keyed_area, parts, y_of

# Measured: without an API mask gpt-image-1.5 (+input_fidelity=high) keeps the figure aligned to ~1px;
# with a mask the arms drift ~50px and large masks produce a dark glowing backdrop.
EDIT_MODEL = os.environ.get("TRYON_EDIT_MODEL", "gpt-image-1.5")
FALLBACK_MODEL = os.environ.get("TRYON_FALLBACK_MODEL", "gpt-image-2")
CAT = json.load(open(Path(__file__).with_name("catalog.json")))

PROMPT = (
    "Edit this studio photo: dress the woman in {desc}. "
    "IMPORTANT: the flat bright {keyname} is a chroma-key bodysuit, NOT clothing. Wherever the new item does not "
    "cover the body (neck, arms, hands, legs, feet, any gap, opening or see-through part), keep that area the same "
    "flat bright {keyname} — never paint skin over it. Only this one item, no other clothes, shoes or accessories. "
    "It must fit this exact body and pose naturally and fully cover the body where it is worn, with no gaps at its "
    "edges. Keep the face, pose, body proportions, framing and the plain light grey background unchanged; "
    "no cast shadows on the background. Neutral white studio light, true-to-life colours, photorealistic "
    "fashion catalogue quality."
)


def chroma_input(item):
    key = item.get("key", "green")
    hair = "_hair" if "hair" in SLOTS[item["slot"]]["allow"] else ""
    return key, ASSETS / f"model_chroma_{key}{hair}.png"


def run(item):
    key, src = chroma_input(item)
    prompt = PROMPT.format(desc=item["desc"], keyname=key)
    try:
        out = edit([src], prompt, model=EDIT_MODEL, fidelity="high" if EDIT_MODEL.startswith("gpt-image-1") else None)
    except Exception as e:  # noqa: BLE001
        if "safety" not in str(e) or EDIT_MODEL == FALLBACK_MODEL:
            raise
        # moderation differs per model (e.g. sheer stockings pass on gpt-image-2); registration absorbs its drift
        print(f"  {item['id']}: refused by {EDIT_MODEL}, falling back to {FALLBACK_MODEL}", flush=True)
        out = edit([src], prompt, model=FALLBACK_MODEL)
    out.save(RAW / f"{item['id']}_gen.png")
    finish(item)
    print("generated", item["id"], flush=True)


def anchor_mask(slot, P):
    """Where to measure drift: head and (unless the slot changes them) feet, plus rows outside the band."""
    y0, y1 = (y_of(v) for v in SLOTS[slot]["band"])
    a = P["head"].copy()
    if "feet" not in SLOTS[slot]["allow"]:
        a |= P["feet"]
    a = cv2.dilate(a.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    rows = np.ones_like(a)
    rows[max(0, y0 - 20):y1 + 20] = False
    return a | rows


def finish(item):
    gid, slot = item["id"], item["slot"]
    key, src = chroma_input(item)
    P = parts()
    person = P["person"]
    region = editable(slot, P)
    gen_img = Image.open(RAW / f"{gid}_gen.png").convert("RGB")
    warp, before, after = align.estimate(gen_img, person.astype(np.float32), anchor_mask(slot, P))
    gen = align.apply(np.asarray(gen_img).astype(np.float32) / 255, warp, person.shape)
    arm_info = None
    if "hands" not in SLOTS[slot]["allow"] and slot != "wings":  # hands must still look like hands
        gsil = align.silhouette(Image.fromarray((gen * 255).astype(np.uint8))) > 0.5
        aw = warp_fix.arm_warp(person, gsil, person.shape)
        if aw is not None and max(v["shift_px"] for v in aw[2].values()) < 90:
            mx, my, arm_info = aw
            gen = cv2.remap(gen, mx, my, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    json.dump({"affine": warp.tolist(), "anchor_iou_before": before, "anchor_iou_after_affine": after,
               "arms": arm_info}, open(RAW / f"{gid}_align.json", "w"), indent=1)
    print(f"  {gid}: anchor IoU {before:.3f} -> {after:.3f}; arm fix "
          f"{[round(v['shift_px'], 1) for v in arm_info.values()] if arm_info else '-'}", flush=True)
    base = load_rgb(src)
    soft = cv2.GaussianBlur(cv2.erode(region.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32),
                            (0, 0), 1.2)[..., None]
    save_rgb(gen * soft + base * (1 - soft), RAW / f"{gid}_onmodel.png")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--finish"]:
        for c in CAT:
            if c["id"] in args[1:] or len(args) == 1:
                finish(c)
        sys.exit()
    items = [c for c in CAT if not args or c["id"] in args]
    with ThreadPoolExecutor(4) as ex:
        for it, f in [(it, ex.submit(run, it)) for it in items]:
            try:
                f.result()
            except Exception as e:  # noqa: BLE001
                print("FAILED", it["id"], repr(e)[:200], flush=True)
