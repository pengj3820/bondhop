import json, numpy as np, cv2, mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path='models/pose.task')))
seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(base_options=BaseOptions(model_asset_path='models/seg.tflite'), output_confidence_masks=True))
def load(p): return cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)
def mpimg(a): return mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(a))
def kps(a):
    r = pose.detect(mpimg(a)); h, w = a.shape[:2]
    return np.array([[l.x*w, l.y*h] for l in r.pose_landmarks[0]])
def segm(a):
    r = seg.segment(mpimg(a)); return np.stack([np.squeeze(m.numpy_view()) for m in r.confidence_masks], -1)  # bg,hair,body,face,clothes,other
def lab(a): return cv2.cvtColor(a.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
def dE(a, b): return np.linalg.norm(lab(a) - lab(b), axis=-1)
NAMES = {0:'鼻子',7:'左耳',8:'右耳',11:'左肩',12:'右肩',13:'左肘',14:'右肘',15:'左腕',16:'右腕',23:'左髋',24:'右髋',25:'左膝',26:'右膝',27:'左踝',28:'右踝'}
B = load('base.png'); H, W = B.shape[:2]
kB = kps(B); sB = segm(B)
skinB = (sB[...,2] + sB[...,3])
baseClothes = sB[...,4] > .5
def box(pts, pad, y0=None, y1=None):
    m = np.zeros((H, W), bool); x0, x1 = int(pts[:,0].min()-pad), int(pts[:,0].max()+pad)
    ya = int(pts[:,1].min()-pad) if y0 is None else int(y0); yb = int(pts[:,1].max()+pad) if y1 is None else int(y1)
    m[max(ya,0):min(yb,H), max(x0,0):min(x1,W)] = True; return m
k = kB
face = box(k[[0,1,2,3,4,5,6,7,8,9,10]], 40)
# zone where each garment is allowed to change pixels
ZONE = {
 'tee':    box(k[[11,12,13,14,23,24]], 70, y0=k[0,1]+40),
 'jeans':  box(k[[23,24,25,26,27,28]], 70, y0=(k[11,1]+k[23,1])/2),
 'trench': box(k[[11,12,13,14,15,16,25,26]], 90, y0=k[0,1]+40),
 'skirt':  box(k[[23,24,25,26]], 60, y0=(k[11,1]+k[23,1])/2, y1=(k[23,1]+k[25,1])/2+120),
 'swim':   box(k[[11,12,23,24,25,26]], 60, y0=k[0,1]+40, y1=(k[23,1]+k[25,1])/2+40),
 'sneakers': box(k[[27,28,29,30,31,32]], 60),
}
# base-wear that the garment must hide (tank = upper clothes, shorts = lower clothes)
mid = (k[23,1] + k[11,1]) / 2 + 0.35*(k[23,1]-k[11,1])
tank = baseClothes.copy(); tank[int(mid):] = False
shorts = baseClothes.copy(); shorts[:int(mid)] = False
MUST = {'tee': tank, 'jeans': shorts, 'skirt': None, 'swim': tank | shorts, 'trench': None, 'sneakers': None}
def recolor(img, skinmask, target=(96,65,52)):
    L = lab(img); t = lab(np.array([[target]],np.uint8))[0,0]
    m = skinmask > .5
    if m.sum() == 0: return img
    mean = L[m].mean(0); out = L.copy()
    out[...,0] = (L[...,0]-mean[0])*0.8 + t[0]; out[...,1] = L[...,1]-mean[1]+t[1]; out[...,2] = L[...,2]-mean[2]+t[2]
    a = cv2.GaussianBlur(skinmask.astype(np.float32), (0,0), 1.5)[...,None]
    rgb = cv2.cvtColor(np.clip(out,0,255).astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)
    return (rgb*a + img*(1-a)).astype(np.uint8)
Bdark = recolor(B, skinB)
report = {}
for g in ZONE:
    D = load(f'd_{g}.png'); kD = kps(D); sD = segm(D)
    disp = np.linalg.norm(kD - kB, axis=1)
    idx = list(NAMES)
    d = dE(cv2.GaussianBlur(B,(0,0),1.2), cv2.GaussianBlur(D,(0,0),1.2))
    bgmask = (sB[...,0] > .9) & (sD[...,0] > .9)
    changed = d > 14
    changed = cv2.morphologyEx(changed.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5,5),np.uint8)).astype(bool)
    zone = ZONE[g]
    out_zone = changed & ~zone & ~bgmask
    # garment layer: changed pixels inside the zone, feathered
    a = (changed & zone).astype(np.float32)
    a = cv2.morphologyEx(a, cv2.MORPH_CLOSE, np.ones((9,9),np.uint8))
    a = cv2.GaussianBlur(a, (0,0), 1.0)
    cv2.imwrite(f'layer_{g}.png', cv2.cvtColor(np.dstack([D, (a*255).astype(np.uint8)]), cv2.COLOR_RGBA2BGRA))
    comp = (D*a[...,None] + B*(1-a[...,None])).astype(np.uint8)
    recon = dE(comp, D)
    leak = None
    if MUST[g] is not None:
        req = MUST[g] & (sD[...,4] > .5) if g!='swim' else MUST[g]
        leak = int((MUST[g] & (a < .5)).sum())
    # halo: composite on dark-skin base vs "ideal" (dressed photo with its own skin recolored)
    ideal = recolor(D, sD[...,2]+sD[...,3])
    compDark = (D*a[...,None] + Bdark*(1-a[...,None])).astype(np.uint8)
    edge = (a > .02) & (a < .98)
    band = cv2.dilate(edge.astype(np.uint8), np.ones((7,7),np.uint8)).astype(bool) & ((skinB>.5)|(sD[...,2]+sD[...,3]>.5))
    he = dE(compDark, ideal)[band]
    cv2.imwrite(f'dark_{g}.png', cv2.cvtColor(compDark, cv2.COLOR_RGB2BGR))
    cv2.imwrite(f'ideal_{g}.png', cv2.cvtColor(ideal, cv2.COLOR_RGB2BGR))
    report[g] = {
      'pose_mean_px': round(float(disp[idx].mean()),1), 'pose_max_px': round(float(disp[idx].max()),1),
      'pose_worst': NAMES[idx[int(disp[idx].argmax())]],
      'face_changed_pct': round(100*float((changed & face).sum())/face.sum(),1),
      'face_dE_mean': round(float(d[face].mean()),1),
      'bg_dE_median': round(float(np.median(d[bgmask])),1),
      'changed_outside_zone_px': int(out_zone.sum()),
      'recon_dE_p99': round(float(np.percentile(recon[a>0.5],99)),1) if (a>0.5).any() else None,
      'basewear_leak_px': leak,
      'halo_band_px': int(band.sum()),
      'halo_dE_mean': round(float(he.mean()),1) if he.size else None,
      'halo_pct_dE_gt15': round(100*float((he>15).mean()),1) if he.size else None,
    }
    print(g, report[g])
json.dump(report, open('report.json','w'), ensure_ascii=False, indent=1)
cv2.imwrite('dark_base.png', cv2.cvtColor(Bdark, cv2.COLOR_RGB2BGR))
