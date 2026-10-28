"""Garment layer extraction + 3-skin-tone composite + automatic QA for every item in items.py."""
import sys, json, numpy as np, cv2, mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
from items import ITEMS
pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path='models/pose.task')))
seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(base_options=BaseOptions(model_asset_path='models/seg.tflite'), output_confidence_masks=True))
def load(p): return cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)
def mpimg(a): return mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(a))
def kps(a):
    r = pose.detect(mpimg(a)); h, w = a.shape[:2]; return np.array([[l.x*w, l.y*h] for l in r.pose_landmarks[0]])
def segm(a): return np.stack([np.squeeze(m.numpy_view()) for m in seg.segment(mpimg(a)).confidence_masks], -1)
def lab(a): return cv2.cvtColor(np.clip(a,0,255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
def rgb(L): return cv2.cvtColor(np.clip(L,0,255).astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)
def dE(a, b): return np.linalg.norm(lab(a) - lab(b), axis=-1)
def dil(m, k): return cv2.dilate(m.astype(np.uint8), np.ones((k,k),np.uint8)).astype(bool)
def ero(m, k): return cv2.erode(m.astype(np.uint8), np.ones((k,k),np.uint8)).astype(bool)

B = load('base.png'); H, W = B.shape[:2]; k = kps(B); sB = segm(B)
skinB = sB[...,2] + sB[...,3]; baseClothes = sB[...,4] > .5
LB = lab(B); core = skinB > .8; mu = LB[core].mean(0); icov = np.linalg.inv(np.cov(LB[core].T) + np.eye(3)*4)
bwcore = cv2.erode(baseClothes.astype(np.uint8), np.ones((9,9),np.uint8)).astype(bool)
mu_b = LB[bwcore].mean(0); icov_b = np.linalg.inv(np.cov(LB[bwcore].T) + np.eye(3)*2)
def basewear_prob(L):
    d = L - mu_b; return np.exp(-0.5*np.clip(np.einsum('...i,ij,...j->...', d, icov_b, d),0,60)/4.0)
mid = (k[23,1] + k[11,1]) / 2 + 0.35*(k[23,1]-k[11,1])
tank = baseClothes.copy(); tank[int(mid):] = False
shorts = baseClothes.copy(); shorts[:int(mid)] = False
MUST = {'tank': tank, 'shorts': shorts, 'both': tank | shorts, None: None}
def box(idx, pad, y0=None, y1=None):
    p = k[idx]; m = np.zeros((H,W), bool)
    ya = int(p[:,1].min()-pad) if y0 is None else int(y0); yb = int(p[:,1].max()+pad) if y1 is None else int(y1)
    m[max(ya,0):min(yb,H), max(int(p[:,0].min()-pad),0):min(int(p[:,0].max()+pad),W)] = True; return m
neck = k[0,1] + 40; hip = (k[23,1]+k[24,1])/2; knee = (k[25,1]+k[26,1])/2; ankle = (k[27,1]+k[28,1])/2
UPPER = [11,12,13,14,15,16,23,24]
def zone(it):
    c, l = it['cat'], it['length']
    if c == 'top':   return box(UPPER, 70, y0=neck, y1=hip+100)
    if c == 'outer': return box(UPPER+([25,26] if l=='long' else []), 90, y0=neck, y1=(knee+90 if l=='long' else hip+110))
    if c == 'bottom':
        y1 = {'long': ankle+50, 'short': (hip+knee)/2+130, 'midi': ankle-10}[l]
        return box([23,24,25,26,27,28], 80, y0=mid-40, y1=y1)
    if c == 'full':
        y1 = {'swim': (hip+knee)/2+40, 'knee': knee+70, 'midi': ankle-10, 'long': ankle+50}[l]
        return box(UPPER+[25,26], 80, y0=neck, y1=y1)
    if c == 'shoes': return box([27,28,29,30,31,32], 60, y0=(ankle-140 if l=='ankle' else None))
face = box([0,1,2,3,4,5,6,7,8,9,10], 40)
NAMES = {0:'鼻子',7:'左耳',8:'右耳',11:'左肩',12:'右肩',13:'左肘',14:'右肘',15:'左腕',16:'右腕',23:'左髋',24:'右髋',25:'左膝',26:'右膝',27:'左踝',28:'右踝'}
TONES = {'light': (238,214,190), 'medium': (160,126,86), 'dark': (96,65,52)}
def recolor(img, w, tone):
    """Same transform for body and garment skin; highlights compressed more for darker targets."""
    L = lab(img); t = lab(np.array([[tone]],np.uint8))[0,0]; out = L.copy(); r = t[0]/mu[0]
    kp, kn = np.clip(0.3+0.7*r, .4, 1.0), np.clip(0.5+0.5*r, .6, 1.0); d = L[...,0]-mu[0]
    out[...,0] = np.where(d>0, kp*d, kn*d) + t[0]
    out[...,1] = (L[...,1]-mu[1])*0.6 + t[1]; out[...,2] = (L[...,2]-mu[2])*0.6 + t[2]
    w = np.clip(w,0,1)[...,None]; return rgb(out)*w + img.astype(np.float32)*(1-w)
def skin_prob(L):
    d = L - mu; return np.exp(-0.5*np.clip(np.einsum('...i,ij,...j->...', d, icov, d),0,60)/4.0)
Bt = {t: recolor(B, cv2.GaussianBlur(skinB.astype(np.float32),(0,0),1.2), TONES[t]) for t in TONES}
bodyref = core & ~face
def seam_outliers(comp, skinmask, edge_band):
    """thin lines / patches: skin pixels that differ sharply from their local skin neighbourhood"""
    Lc = lab(comp); S = skinmask.astype(np.float32)
    num = cv2.GaussianBlur(Lc*S[...,None], (0,0), 6); den = cv2.GaussianBlur(S, (0,0), 6)[...,None] + 1e-4
    dev = np.linalg.norm(Lc - num/den, axis=-1)
    return int(((dev > 14) & skinmask & edge_band).sum())

only = sys.argv[1:] or list(ITEMS); report = {}
for g in only:
    it = ITEMS[g]; D = load(f'd_{g}.png'); sD = segm(D)
    kD = kps(D); idx = list(NAMES); disp = np.linalg.norm(kD[idx]-k[idx], axis=1)
    d = dE(cv2.GaussianBlur(B,(0,0),1.2), cv2.GaussianBlur(D,(0,0),1.2))
    changed = cv2.morphologyEx((d > 14).astype(np.uint8), cv2.MORPH_OPEN, np.ones((5,5),np.uint8)).astype(bool)
    Z = zone(it)
    clothD = ((sD[...,4] + sD[...,5]) > .5) & (d > 5)   # clothing that actually changed; untouched basewear stays out of the layer
    a = cv2.GaussianBlur(cv2.morphologyEx(((changed | clothD) & Z).astype(np.float32), cv2.MORPH_CLOSE, np.ones((9,9),np.uint8)), (0,0), 1.0)
    must = MUST[it['replaces']]
    kept = int((must & (d < 6) & (sD[...,4] > .5)).sum()) if must is not None else 0   # basewear the AI left in place
    if must is not None:
        a = np.maximum(a, cv2.GaussianBlur(dil(must, 17).astype(np.float32), (0,0), 2.0))
    skinSeg = sD[...,2] + sD[...,3]; cloth = sD[...,4] + sD[...,5]
    LD = lab(D); p = skin_prob(LD); layer = a > .01
    skin_core = layer & (cloth < .45) & (((skinSeg > .6) & (p > .05)) | ((p > .5) & (cloth < .3) & dil(skinSeg > .5, 13)))
    skin_core = cv2.morphologyEx(skin_core.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3,3),np.uint8)).astype(bool)
    garm_core = ero(layer & (((cloth > .5) & (p < .02)) | (cloth > .85)), 3)
    # skin may only come from the garment image where the base model wore basewear
    allowed = dil(baseClothes, 29)
    drop = cv2.GaussianBlur(((skin_core | (layer & (skinSeg > .3) & (cloth < .45) & ~garm_core)) & ~allowed).astype(np.float32), (0,0), 2.0)
    a = a * (1 - np.clip(drop*1.5, 0, 1)); layer = a > .01; skin_core &= layer; garm_core &= layer
    if skin_core.any():   # colour-match newly revealed skin to the base skin beside it
        ring = dil(skin_core, 31) & ~layer & (skinB > .7); inner = skin_core & dil(ring, 31)
        if ring.sum() > 50 and inner.sum() > 50:
            w = cv2.GaussianBlur(skin_core.astype(np.float32),(0,0),2.0)[...,None]
            D = rgb(LD + w*(LB[ring].mean(0) - LD[inner].mean(0))).astype(np.uint8); LD = lab(D)
    band = layer & ~skin_core & ~garm_core & dil(skin_core, 15)
    region = dil(layer, 9)
    Fg = cv2.inpaint(D, (region & ~garm_core).astype(np.uint8), 5, cv2.INPAINT_TELEA).astype(np.float32)
    Sk = cv2.inpaint(D, (region & ~skin_core).astype(np.uint8), 5, cv2.INPAINT_TELEA).astype(np.float32)
    I = D.astype(np.float32); v = Fg - Sk
    alpha = np.clip(((I-Sk)*v).sum(-1)/((v*v).sum(-1)+1e-3), 0, 1)
    gshare = np.where(skin_core, 0., np.where(garm_core, 1., np.where(band, alpha, 1.)))
    # a layer must never carry basewear: strip pixels that look like the grey basewear near where the basewear is
    pb = basewear_prob(lab(D))
    if it['cat'] == 'outer':   # open jackets: whatever basewear shows through the opening is never part of the jacket
        bw = (pb > .3) & dil(baseClothes, 41) & ~skin_core
    else:
        bw = (((pb > .5) & (d < 12)) | (pb > .9)) & dil(baseClothes, 41) & ~skin_core
    bw = cv2.morphologyEx(bw.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3,3),np.uint8)).astype(bool)
    res_bw = int((bw & (a > .5)).sum())
    a = a * (1 - cv2.GaussianBlur(dil(bw, 3).astype(np.float32), (0,0), 1.0)); layer = a > .01
    sw = np.where(layer, 1-gshare, 0.)                      # skin channel shipped with the layer
    cv2.imwrite(f'L_{g}.png', cv2.cvtColor(np.dstack([D, (a*255).astype(np.uint8)]), cv2.COLOR_RGBA2BGRA))
    cv2.imwrite(f'S_{g}.png', (sw*255).astype(np.uint8))
    edge = dil((a > .02) & (a < .98), 25)
    res = {'name': it['name'], 'cat': it['cat'],
           'pose_mean': round(float(disp.mean()),1), 'pose_max': round(float(disp.max()),1), 'pose_worst': NAMES[idx[int(disp.argmax())]],
           'face_pct': round(100*float((changed & face).sum())/face.sum(),2), 'basewear_kept_px': kept, 'basewear_stripped_px': res_bw, 'seam': {}}
    for t in TONES:
        Skt = recolor(np.clip(Sk,0,255).astype(np.uint8), np.ones((H,W)), TONES[t])
        Lt = np.clip(I - sw[...,None]*Sk + sw[...,None]*Skt, 0, 255)
        comp = (Lt*a[...,None] + Bt[t]*(1-a[...,None])).astype(np.uint8)
        cv2.imwrite(f'C_{t}_{g}.png', cv2.cvtColor(comp, cv2.COLOR_RGB2BGR))
        skinmask = ((skinB > .5) & (a < .5)) | ((sw > .5) & (a > .5))
        res['seam'][t] = seam_outliers(comp, skinmask & ~face, edge)
    fails = []
    if res['pose_max'] > 20: fails.append('姿势漂移')
    if res['face_pct'] > 2: fails.append('脸被改动')
    if kept > 800: fails.append('AI保留了打底衣')
    res['fails'] = fails; res['pass'] = not fails
    report[g] = res; print(g, json.dumps(res, ensure_ascii=False))
prev = json.load(open('qa.json')) if len(sys.argv) > 1 else {}
prev.update(report); json.dump(prev, open('qa.json','w'), ensure_ascii=False, indent=1)
