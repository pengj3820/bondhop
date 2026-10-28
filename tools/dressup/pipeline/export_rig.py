"""Rig assets for the wave demo: clean background plate, person mask, arm region (image-left arm) and joint positions."""
import json, numpy as np, cv2
from PIL import Image
exec(open('pipeline.py').read().split("only = sys.argv")[0])
OUT = '../app/assets'; man = json.load(open(f'{OUT}/manifest.json'))
person = sB[...,0] < .5
# 1) background plate: fill the person area row by row with a linear fit of that row's background
hole = cv2.dilate(person.astype(np.uint8), np.ones((13,13),np.uint8))
fill = cv2.inpaint(B, hole, 9, cv2.INPAINT_TELEA).astype(np.float32)
# smooth only inside the hole so the fill keeps the local background tone at the boundary
blur = cv2.GaussianBlur(fill, (0,0), 5)
w = cv2.GaussianBlur(cv2.erode(hole, np.ones((9,9),np.uint8)).astype(np.float32), (0,0), 3)[...,None]
plate = blur*w + fill*(1-w)
Image.fromarray(np.clip(plate,0,255).astype(np.uint8)).save(f'{OUT}/plate.webp', quality=88)
Image.fromarray((np.clip(cv2.GaussianBlur((sB[...,0] < .5).astype(np.float32),(0,0),1.0),0,1)*255).astype(np.uint8),'L').save(f'{OUT}/base_person.webp', quality=92)
# 2) arm region for the image-left arm (landmarks 12 shoulder, 14 elbow, 16 wrist, 20 index tip)
J0, J1, J2, TIP = k[12], k[14], k[16], k[20]
cxm = (k[23,0] + k[24,0]) / 2
gap = []
for y in range(int(J0[1]), int(TIP[1] + 75)):
    row = person[y]; x = int(cxm)
    while x > 0 and row[x]: x -= 1          # walk out of the torso
    xt = x
    while x > 0 and not row[x]: x -= 1      # cross the background gap
    if xt - x > 2 and x > 0 and x < J0[0] + 40: gap.append((y, (xt + x) / 2))
armpit = gap[0]; bottom = int(TIP[1] + 75)
T = (J0[0] + 18, J0[1] - 65)                 # shoulder-top end of the seam
poly = [(0, T[1]), T, (armpit[1], armpit[0])] + [(x, y) for y, x in gap[::6]] + [(gap[-1][1], bottom), (0, bottom)]
reg = np.zeros((H, W), np.uint8); cv2.fillPoly(reg, [np.array(poly, np.int32)], 255)
reg = cv2.GaussianBlur(reg, (0,0), 1.5)
Image.fromarray(reg, 'L').save(f'{OUT}/arm_region.webp', quality=92)
man['rig'] = {'plate': 'assets/plate.webp', 'person': 'assets/base_person.webp', 'arm': 'assets/arm_region.webp',
              'shoulder': [round(float(v),1) for v in J0], 'elbow': [round(float(v),1) for v in J1],
              'wrist': [round(float(v),1) for v in J2], 'tip': [round(float(v),1) for v in TIP],
              'box': [0, int(T[1] - 10), int(max(x for x, _ in poly) + 10), int(bottom - T[1] + 20)]}
json.dump(man, open(f'{OUT}/manifest.json','w'), ensure_ascii=False, indent=1)
print(json.dumps(man['rig']))
# preview of the arm region
pv = B.copy(); pv[reg > 128] = (pv[reg > 128]*.5 + np.array([230,40,90])*.5).astype(np.uint8)
for p in (J0, J1, J2, TIP): cv2.circle(pv, (int(p[0]), int(p[1])), 7, (40,70,200), -1)
Image.fromarray(pv).resize((512,768)).save('rig_preview.png'); Image.fromarray(np.clip(plate,0,255).astype(np.uint8)).resize((512,768)).save('plate_preview.png')
