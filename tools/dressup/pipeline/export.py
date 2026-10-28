"""Export the dress-up asset set: per skin tone, a base image + one cropped RGBA layer per garment, plus a manifest."""
import json, os, numpy as np, cv2
from PIL import Image
exec(open('pipeline.py').read().split("only = sys.argv")[0])
OUT = '../app/assets'; os.makedirs(OUT, exist_ok=True)
Z = {'shoes': 20, 'bottom': 30, 'full': 30, 'top': 40, 'outer': 50}
TONE_LIST = {'orig': None, **TONES}
man = {'canvas': [W, H], 'tones': {}, 'items': {}}
for t, tone in TONE_LIST.items():
    base = B if tone is None else Bt[t]
    Image.fromarray(np.clip(base,0,255).astype(np.uint8)).save(f'{OUT}/base_{t}.webp', quality=86)
    man['tones'][t] = f'assets/base_{t}.webp'
for g, it in ITEMS.items():
    L = cv2.imread(f'L_{g}.png', cv2.IMREAD_UNCHANGED); D = cv2.cvtColor(L[...,:3], cv2.COLOR_BGR2RGB); a = L[...,3]
    sw = cv2.imread(f'S_{g}.png', 0).astype(np.float32)/255
    ys, xs = np.where(a > 3); x0, x1, y0, y1 = xs.min(), xs.max()+1, ys.min(), ys.max()+1
    files = {}
    for t, tone in TONE_LIST.items():
        col = D if tone is None else np.clip(recolor(D, sw, tone),0,255).astype(np.uint8)
        rgba = np.dstack([col, a])[y0:y1, x0:x1]
        fn = f'{g}_{t}.webp'; Image.fromarray(rgba, 'RGBA').save(f'{OUT}/{fn}', quality=86, method=6)
        files[t] = f'assets/{fn}'
    # thumbnail: the garment alone on a light card
    th = np.dstack([D, a])[y0:y1, x0:x1]; im = Image.fromarray(th, 'RGBA')
    card = Image.new('RGBA', im.size, (240,240,236,255)); card.alpha_composite(im)
    card.thumbnail((140, 180)); card.convert('RGB').save(f'{OUT}/{g}_thumb.webp', quality=80)
    man['items'][g] = {'name': it['name'], 'cat': it['cat'], 'z': Z[it['cat']],
                       'box': [int(x0), int(y0), int(x1-x0), int(y1-y0)], 'files': files, 'thumb': f'assets/{g}_thumb.webp'}
json.dump(man, open(f'{OUT}/manifest.json','w'), ensure_ascii=False, indent=1)
tot = sum(os.path.getsize(f'{OUT}/{f}') for f in os.listdir(OUT))
print('files', len(os.listdir(OUT)), 'total MB', round(tot/1e6,2))
print('example', g, man['items'][g]['box'], 'layer KB', round(os.path.getsize(f'{OUT}/{g}_dark.webp')/1e3,1))
