import sys, os, base64, requests, concurrent.futures as cf
KEY = open('.key').read().strip()
from items import ITEMS
P = ("Image 1 is the model in a waving pose. Image 2 shows the SAME model wearing {g}. Dress the model in image 1 in exactly that "
     "same garment from image 2: identical colour, print, pattern scale, fabric, details, length and fit. Keep everything else in image 1 "
     "exactly identical: same face, hair, raised waving arm, the other arm, legs, framing, scale, background and lighting. "
     "Any basewear the garment does not cover stays as it is.")
def run(k):
    with open('raise/base.png','rb') as a, open(f'd_{k}.png','rb') as b:
        r = requests.post('https://api.openai.com/v1/images/edits', headers={'Authorization': f'Bearer {KEY}'}, timeout=600,
            data={'model':'gpt-image-2','prompt':P.format(g=ITEMS[k]['desc']),'size':'1024x1536','quality':'medium'},
            files=[('image[]', ('pose.png', a, 'image/png')), ('image[]', ('ref.png', b, 'image/png'))])
    d = r.json()
    if 'error' in d: return k, 'ERROR ' + d['error'].get('message','')[:120]
    open(f'raise/d_{k}.png','wb').write(base64.b64decode(d['data'][0]['b64_json'])); return k, 'OK'
with cf.ThreadPoolExecutor(5) as ex:
    for k, s in ex.map(run, sys.argv[1:]): print(k, s)
