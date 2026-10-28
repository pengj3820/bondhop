"""Pose-B (waving) assets: base, skin/person masks, garment layers + skin channels, and a forearm-swing rig."""
import json, numpy as np, cv2
from PIL import Image
exec(open('pipeline.py').read().split("only = sys.argv")[0])      # run inside raise/: B = waving base
OUT = '../../app/assets'; man = json.load(open(f'{OUT}/manifest.json'))
Image.fromarray(B).save(f'{OUT}/raise_base.webp', quality=86)
Image.fromarray((np.clip(cv2.GaussianBlur(skinB.astype(np.float32),(0,0),1.0),0,1)*255).astype(np.uint8),'L').save(f'{OUT}/raise_skin.webp', quality=92)
Image.fromarray((np.clip(cv2.GaussianBlur((sB[...,0] < .5).astype(np.float32),(0,0),1.0),0,1)*255).astype(np.uint8),'L').save(f'{OUT}/raise_person.webp', quality=92)
for g in ['tee','sundress','leather','trench','sweater']:
    L = cv2.imread(f'L_{g}.png', cv2.IMREAD_UNCHANGED); D = cv2.cvtColor(L[...,:3], cv2.COLOR_BGR2RGB); a = L[...,3]; sw = cv2.imread(f'S_{g}.png', 0)
    ys, xs = np.where(a > 3); x0, x1, y0, y1 = xs.min(), xs.max()+1, ys.min(), ys.max()+1
    Image.fromarray(np.dstack([D, a])[y0:y1, x0:x1], 'RGBA').save(f'{OUT}/raise_{g}.webp', quality=86, method=6)
    Image.fromarray(np.dstack([sw, sw, sw, a])[y0:y1, x0:x1], 'RGBA').save(f'{OUT}/raise_{g}_mask.webp', quality=90)
    man['items'][g]['raise'] = {'file': f'assets/raise_{g}.webp', 'mask': f'assets/raise_{g}_mask.webp', 'box': [int(x0), int(y0), int(x1-x0), int(y1-y0)]}
# forearm-swing rig: capsule around the raised arm (shoulder -> elbow -> fingertip)
S, E, Wr, T = k[12], k[14], k[16], k[20]
reg = np.zeros((H, W), np.uint8)
for p, q, r in [(S, E, 48), (E, Wr, 46), (Wr, T + (T - Wr)*0.5, 58)]:
    cv2.line(reg, tuple(int(v) for v in p), tuple(int(v) for v in q), 255, 2*r)
reg = cv2.GaussianBlur(reg, (0,0), 1.5); Image.fromarray(reg,'L').save(f'{OUT}/raise_arm_region.webp', quality=92)
ys, xs = np.where(reg > 10)
man['raise'] = {'base': 'assets/raise_base.webp', 'skin': 'assets/raise_skin.webp', 'person': 'assets/raise_person.webp',
                'arm': 'assets/raise_arm_region.webp', 'shoulder': [float(v) for v in S.round(1)], 'elbow': [float(v) for v in E.round(1)],
                'wrist': [float(v) for v in Wr.round(1)], 'tip': [float(v) for v in T.round(1)],
                'box': [int(xs.min()), int(ys.min()), int(xs.max()-xs.min()+1), int(ys.max()-ys.min()+1)]}
json.dump(man, open(f'{OUT}/manifest.json','w'), ensure_ascii=False, indent=1)
print(json.dumps(man['raise']))
