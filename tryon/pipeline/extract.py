"""Step 4 (offline): pull a garment part off the chroma model as an aligned, soft-edged RGBA layer.

Opaque parts   alpha = "not key colour" on the keyed body  ∧  "not backdrop" (BiRefNet matte) elsewhere.
Sheer parts    the colour underneath is known (key colour or backdrop), so per pixel
               C = a*F + (1-a)*B is solved for the smallest a that keeps F a valid colour, then
               dense areas are pushed to opaque. F (true fabric colour) is un-mixed from B.
Edges          guided filter on alpha (follows real image edges -> no stair-stepping), soft fall-off where the
               part meets face / hands / band limits, green/magenta despill.
No base leak   body strips narrower than SLIVER px left between garment edge and body edge get covered;
               the slot's must-cover zone must be >= 97% covered; parts cut by the band limit are flagged.
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import align
from common import ASSETS, RAW, load_rgb, save_rgba
from keys import KEYS, despill, keyness
from regions import SLOTS, editable, keyed_area, must_cover, parts, protect, y_of

CAT = {c["id"]: c for c in json.load(open(Path(__file__).with_name("catalog.json")))}
SLIVER = 21


def box(x, r):
    return cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))


def guided(guide, src, r=3, eps=2e-3):
    mi, mp = box(guide, r), box(src, r)
    a = (box(guide * src, r) - mi * mp) / (box(guide * guide, r) - mi * mi + eps)
    b = mp - a * mi
    return box(a, r) * guide + box(b, r)


def lowres_inpaint(img, hole, s=4, blur=3):
    small = cv2.resize((img * 255).astype(np.uint8), None, fx=1 / s, fy=1 / s, interpolation=cv2.INTER_AREA)
    m = cv2.resize(hole.astype(np.uint8), (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
    out = cv2.GaussianBlur(cv2.inpaint(small, m * 255, 9, cv2.INPAINT_TELEA), (0, 0), blur)
    return cv2.resize(out, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255


def min_alpha(C, B):
    """Smallest alpha such that F = B + (C - B) / alpha stays inside the RGB cube."""
    up = np.where(C > B, (C - B) / np.maximum(1 - B, 1e-3), 0)
    dn = np.where(C < B, (B - C) / np.maximum(B, 1e-3), 0)
    return np.clip(np.maximum(up, dn).max(-1), 0, 1)


def soft(mask, sigma=1.2):
    """Binary mask -> anti-aliased weight (masks multiply alpha instead of hard-zeroing it: no stair-steps)."""
    return np.clip(cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigma) * 2 - 0.5, 0, 1) if sigma else mask


def solve_alpha(C, B, steps=12, bias=0.5, key="green"):
    """Pick alpha in [alpha_min, 1] whose un-mixed fabric colour F is least saturated (fabrics are far less
    saturated than key colours), with a mild preference for transparency."""
    a0 = np.maximum(min_alpha(C, B), 0.02)
    best_a, best_c = np.ones_like(a0), np.full_like(a0, 1e9)
    for t in np.linspace(0, 1, steps):
        a = a0 + (1 - a0) * t
        F = np.clip(B + (C - B) / a[..., None], 0, 1)
        # over-subtracting the key leaves its complementary tint (purple for green): penalise it
        anti = (np.minimum(F[..., 0], F[..., 2]) - F[..., 1]) if key == "green" else (
            F[..., 1] - np.maximum(F[..., 0], F[..., 2]))
        cost = F.max(-1) - F.min(-1) + bias * (a - a0) + 2.0 * np.clip(anti - 0.04, 0, None)
        better = cost < best_c
        best_a = np.where(better, a, best_a)
        best_c = np.where(better, cost, best_c)
    return np.where(min_alpha(C, B) < 0.02, 0, best_a)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def extract(gid):
    item = CAT[gid]
    slot, key, sheer = item["slot"], item.get("key", "green"), item.get("sheer", False)
    img = load_rgb(RAW / f"{gid}_onmodel.png")
    P = parts()
    region, prot, keyed = editable(slot, P), protect(slot, P), keyed_area(slot, P)
    h, w = region.shape
    keyed_soft = cv2.dilate(keyed.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)

    s, r = keyness(img, key)
    clean_key = (r > 0.45) & (s > 0.08)
    a_key = np.where(s > 0.03, np.clip((0.45 - r) / 0.25, 0, 1), 1.0)

    fg = align.silhouette(Image.fromarray((img * 255).astype(np.uint8)), "birefnet-general-lite")
    bgf = lowres_inpaint(img, cv2.dilate(((fg > 0.2) | (s > 0.05)).astype(np.uint8), np.ones((31, 31), np.uint8)) > 0)
    diff = np.abs(img - bgf).max(-1)
    a_bg = np.maximum(fg, np.clip((diff - 0.05) / 0.07, 0, 1) * (fg > 0.05))
    a_bg = np.minimum(a_bg, np.where(s > 0.03, np.clip((0.3 - r) / 0.2, 0, 1), 1.0))  # key spill isn't garment
    a_bg = np.minimum(a_bg, cv2.GaussianBlur(cv2.erode(a_bg, np.ones((3, 3), np.uint8)), (0, 0), 0.7))
    alpha = np.where(keyed_soft, np.minimum(a_key, a_bg), a_bg)

    rgb = img.copy()
    if sheer:
        # colour under the fabric = the chroma input we sent (already pixel-aligned, carries the body's own
        # shading), times a smooth gain field for the model's re-lighting. Using the input instead of the
        # generated image keeps body shading from being mistaken for dark sheer fabric.
        src = load_rgb(ASSETS / f"model_chroma_{key}{'_hair' if 'hair' in SLOTS[slot]['allow'] else ''}.png")
        ratio = img / np.maximum(src, 0.02)
        lumr = ratio.mean(-1)
        good = clean_key & keyed & (lumr > 0.75) & (lumr < 1.6)
        gain = np.ones_like(img)
        if good.sum() > 500:
            med = np.median(ratio[good], axis=0)
            rf = np.where(good[..., None], ratio, med)
            gain = cv2.GaussianBlur(rf.astype(np.float32), (0, 0), 25)
            wgt = cv2.GaussianBlur(good.astype(np.float32), (0, 0), 25)[..., None]
            gain = (gain * 0 + cv2.GaussianBlur((rf * good[..., None]).astype(np.float32), (0, 0), 25)
                    / np.maximum(wgt, 1e-3)) * (wgt > 0.02) + med * (wgt <= 0.02)
        B = np.where(keyed_soft[..., None], np.clip(src * gain, 0, 1), bgf)
        am = solve_alpha(img, B, key=key)
        # around the body outline the generated body may sit 1-3px off ours: take the most transparent
        # explanation (under = key colour or under = backdrop) and treat key-tinted pixels as body
        outline = cv2.morphologyEx(keyed.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((9, 9), np.uint8)).astype(bool)
        am = np.where(outline, np.minimum(am, solve_alpha(img, bgf, key=key)), am)
        am *= np.where(outline & (r > 0.25) & (s > 0.02), 0.0, 1.0)
        am = np.clip((am - 0.06) / 0.94, 0, 1)
        # where the generated image shows plain backdrop (e.g. the model drew the body slightly slimmer
        # than our input) there is no fabric, whatever the input had underneath
        backdrop_like = (fg < 0.3) & (diff < 0.06) & (s < 0.05)
        am[backdrop_like] = 0
        # key colour outside the fixed body = the model drew the body a bit wider: body, not fabric
        am *= np.where(~keyed_soft & (s > 0.05), np.clip((0.3 - r) / 0.15, 0, 1), 1.0)
        am = am + (1 - am) * smoothstep(0.6, 0.85, am)  # dense lace / seams / opaque parts -> solid
        cand = cv2.morphologyEx((am > 0.15).astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(cand)
        big = np.zeros(n, bool)
        big[1:] = st[1:, cv2.CC_STAT_AREA] > 1500
        support = big[lab] | cv2.dilate((alpha > 0.5).astype(np.uint8) * (~keyed_soft), np.ones((15, 15), np.uint8)).astype(bool)
        support = cv2.dilate(support.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        alpha = np.where(keyed_soft, am, np.maximum(am, alpha * (am > 0.02))) * soft(support, 2.0)
        alpha *= np.where(~keyed_soft & (s > 0.05), np.clip((0.3 - r) / 0.15, 0, 1), 1.0)
        F = np.clip(B + (img - B) / np.maximum(alpha, 0.05)[..., None], 0, 1)
        # dark sheer fabric (black tulle / lace) un-mixes with a residual colour cast: neutralise it
        lumF = (F @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
        chromaF = (F.max(-1) - F.min(-1))[..., None]
        F = np.where((lumF < 0.25) & (chromaF < 0.18), F * 0.2 + lumF * 0.8, F)
        rgb = np.clip(np.where(alpha[..., None] > 0.02, F, img), 0, 1)
        # no backdrop gap between a garment and the body outline: continue the garment up to the body
        # edge on the outside of the body (inside, the body is drawn by the base layer anyway)
        band = outline & ~keyed
        a_near = cv2.dilate((alpha * ~outline).astype(np.float32), np.ones((9, 9), np.uint8))
        grow = band & (a_near > alpha)
        if grow.any():
            src8 = (rgb * 255).astype(np.uint8)
            fill = cv2.inpaint(src8, (outline * 255).astype(np.uint8), 4, cv2.INPAINT_TELEA).astype(np.float32) / 255
            rgb = np.where(grow[..., None], fill, rgb)
            alpha = np.where(grow, a_near, alpha)

    alpha = alpha * soft(region & ~prot)
    # drop specks, fill pin-holes (keep real openings)
    hard = (alpha > 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(hard)
    keep = np.zeros(n, bool)
    if n > 1:
        keep[1:] = st[1:, cv2.CC_STAT_AREA] >= max(300, 0.02 * st[1:, cv2.CC_STAT_AREA].max())
    near_keep = cv2.dilate(keep[lab].astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    alpha = alpha * soft(near_keep, 2.0)
    if not sheer:
        inv = (alpha <= 0.5).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(inv)
        small = np.zeros(n, bool)
        small[1:] = st[1:, cv2.CC_STAT_AREA] < 150
        alpha[small[lab]] = 1

    # ---- no base leak: cover thin body strips along garment edges (opaque parts only) ----
    body = P["body"] & ~prot
    garment = alpha > 0.5
    slivers = np.zeros_like(garment)
    if not sheer and slot != "wings":
        exposed = body & ~garment & region
        k = np.ones((SLIVER, SLIVER), np.uint8)
        opened = cv2.morphologyEx(exposed.astype(np.uint8), cv2.MORPH_OPEN, k).astype(bool)
        near = cv2.dilate(garment.astype(np.uint8), k).astype(bool)
        slivers = exposed & ~opened & near
        hole = slivers | ((alpha > 0.02) & (alpha < 0.98) & keyed_soft)
        # colour from the nearest solid garment pixel only (inpainting would pull in backdrop / body colours)
        from scipy.ndimage import distance_transform_edt
        solid_g = (alpha > 0.95) & (s < 0.03) | ((alpha > 0.95) & (r < 0.2))
        _, (iy, ix) = distance_transform_edt(~solid_g, return_indices=True)
        nearest = rgb[iy, ix]
        nearest = cv2.GaussianBlur(nearest, (0, 0), 1.5)
        rgb = np.where(hole[..., None], nearest, rgb)
        alpha[slivers] = 1
        # on the body a garment edge is a fabric edge against the body: make it solid, the outline comes from
        # the body silhouette of the base layer (already anti-aliased)
        inner = (alpha > 0.15) & body & cv2.dilate(garment.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        alpha[inner] = np.maximum(alpha[inner], 0.99)

    # ---- edges: guided filter + soft limits ----
    guide = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    refined = np.clip(guided(guide, alpha.astype(np.float32), r=2, eps=1e-3), 0, 1)
    solid = cv2.erode((alpha > 0.97).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    empty = cv2.erode((alpha < 0.03).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    if sheer:  # keep lace detail: lighter, edge-aware smoothing
        refined = np.clip(guided(guide, alpha.astype(np.float32), r=1, eps=4e-3), 0, 1)
    alpha = np.where(solid, 1.0, np.where(empty, 0.0, refined))
    alpha = alpha * soft(region & ~prot)
    alpha[alpha < 0.01] = 0

    edge = (cv2.dilate((alpha < 0.98).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
            | cv2.dilate((s > 0.03).astype(np.uint8) * (r > 0.2), np.ones((13, 13), np.uint8)).astype(bool)) & (alpha > 0)
    rgb = np.where(edge[..., None], despill(rgb, key), rgb)

    # ---- QA ----
    qa = {"sheer": sheer, "key": key, "sliver_px_filled": int(slivers.sum()), "garment_px": int((alpha > 0.5).sum())}
    ok = qa["garment_px"] > 1500
    mc = must_cover(slot)
    if mc and not sheer:
        zone = P["body"].copy()
        zone[:mc[0]] = False
        zone[mc[1]:] = False
        zone[:, :mc[2]] = False
        zone[:, mc[3]:] = False
        qa["must_cover_ratio"] = round(float((alpha[zone] > 0.5).mean()), 4)
        ok &= qa["must_cover_ratio"] >= 0.97
    y0, y1 = (y_of(v) for v in SLOTS[slot]["band"])
    cut = 0
    for yb in (y0, y1 - 1):
        if 0 < yb < h - 1:
            cut += int((alpha[yb] > 0.5).sum())
    qa["cut_at_band_px"] = cut
    ok &= cut < 25
    qa["pass"] = bool(ok)

    (ASSETS / "layers").mkdir(exist_ok=True)
    save_rgba(rgb, alpha, ASSETS / "layers" / f"{gid}.png")
    vis = np.zeros((h, w, 3), np.float32) + 0.15
    vis += alpha[..., None] * 0.5
    vis[slivers] = (1, 0.2, 0.2)
    cv2.imwrite(str(RAW / f"{gid}_coverage.png"), (np.clip(vis, 0, 1)[..., ::-1] * 255).astype(np.uint8))
    json.dump(qa, open(RAW / f"{gid}_qa.json", "w"), indent=1)
    print(gid, qa, flush=True)
    return qa


if __name__ == "__main__":
    ids = sys.argv[1:] or list(CAT)
    if len(ids) == 1:
        extract(ids[0])
    else:  # one process per part keeps peak memory low (ONNX matting on CPU); 3 in parallel
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(3) as ex:
            list(ex.map(lambda g: subprocess.run([sys.executable, __file__, g], check=False), ids))
