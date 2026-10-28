# wear several layers at once: bottom -> shoes -> top -> outer, each layer carries its own skin channel
import numpy as np, cv2
exec(open('pipeline.py').read().split("only = sys.argv")[0])
ORDER = {'bottom': 0, 'full': 0, 'shoes': 1, 'top': 2, 'outer': 3}
OUTFITS = [['tee','jeans','sneakers'], ['sweater','midi','boots'], ['cami','dshorts','leather','boots'],
           ['hoodie','cargo','trench','sneakers'], ['shirt','wide','denimjk'], ['lbd','leather','boots']]
def wear(items, tone):
    comp = Bt[tone].copy()
    for g in sorted(items, key=lambda g: ORDER[ITEMS[g]['cat']]):
        L = cv2.imread(f'L_{g}.png', cv2.IMREAD_UNCHANGED); D = cv2.cvtColor(L[...,:3], cv2.COLOR_BGR2RGB).astype(np.float32)
        a = L[...,3].astype(np.float32)/255; sw = cv2.imread(f'S_{g}.png', 0).astype(np.float32)/255
        Dt = recolor(D.astype(np.uint8), sw, TONES[tone])          # client-side: recolour the layer's skin pixels
        comp = Dt*a[...,None] + comp*(1-a[...,None])
    return comp.astype(np.uint8)
from PIL import Image
rows = []
for tone in ['light','medium','dark']:
    ims = [Image.fromarray(wear(o, tone)).crop((150,0,874,1536)) for o in OUTFITS]
    s = .3; w, h = int(724*s), int(1536*s); row = Image.new('RGB', (w*len(ims), h), 'white')
    for j, im in enumerate(ims): row.paste(im.resize((w,h)), (j*w, 0))
    rows.append(row)
O = Image.new('RGB', (rows[0].width, rows[0].height*3), 'white')
for i, r in enumerate(rows): O.paste(r, (0, i*rows[0].height))
O.save('combos.jpg', quality=85); print(O.size)
