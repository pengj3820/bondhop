"""Method 2 assets: base skin mask + per-garment skin channel (gray = skin, alpha = garment coverage), plus the base skin mean in CIE Lab."""
import json, numpy as np, cv2
from PIL import Image
exec(open('pipeline.py').read().split("only = sys.argv")[0])
OUT = '../app/assets'; man = json.load(open(f'{OUT}/manifest.json'))
m = np.clip(cv2.GaussianBlur(skinB.astype(np.float32), (0,0), 1.0), 0, 1)
Image.fromarray((m*255).astype(np.uint8), 'L').save(f'{OUT}/base_skin.webp', quality=92)
def srgb_to_lab(c):                       # same formula as the shader (sRGB D65 -> CIE Lab)
    c = c/255.0; c = np.where(c > .04045, ((c+.055)/1.055)**2.4, c/12.92)
    M = np.array([[.4124564,.3575761,.1804375],[.2126729,.7151522,.0721750],[.0193339,.1191920,.9503041]])
    xyz = c @ M.T / np.array([.95047, 1.0, 1.08883])
    f = np.where(xyz > .008856, np.cbrt(xyz), 7.787*xyz + 16/116)
    return np.stack([116*f[...,1]-16, 500*(f[...,0]-f[...,1]), 200*(f[...,1]-f[...,2])], -1)
mu = srgb_to_lab(B[skinB > .8].astype(np.float64)).mean(0)
for g in man['items']:
    L = cv2.imread(f'L_{g}.png', cv2.IMREAD_UNCHANGED); a = L[...,3]; sw = cv2.imread(f'S_{g}.png', 0)
    x, y, w, h = man['items'][g]['box']
    rgba = np.dstack([sw, sw, sw, a])[y:y+h, x:x+w]
    Image.fromarray(rgba, 'RGBA').save(f'{OUT}/{g}_mask.webp', quality=90)
    man['items'][g]['mask'] = f'assets/{g}_mask.webp'
man['skin'] = {'mask': 'assets/base_skin.webp', 'mu_lab': [round(float(v),3) for v in mu]}
json.dump(man, open(f'{OUT}/manifest.json','w'), ensure_ascii=False, indent=1)
print('mu_lab', man['skin']['mu_lab'])
