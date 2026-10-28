"""Build a real Spine 4.2 skeleton (JSON + atlas + PNG pages) from the AI outfit layers:
4 parts (upper body, lower body, two arms) as weighted meshes on a 16-bone rig; each outfit is a skin of linked meshes."""
import json, numpy as np, cv2
from PIL import Image
exec(open('pipeline.py').read().split("Bt = {t:")[0])
OUT = '../spine'
OUTFITS = {'o1': ['tee','jeans','sneakers'], 'o2': ['sweater','midi','boots'], 'o3': ['cami','dshorts','leather','boots'],
           'o4': ['sundress','sneakers'], 'o5': ['hoodie','cargo','trench','sneakers'], 'o6': ['shirt','wide','sneakers']}
ORDER = {'bottom': 0, 'full': 0, 'shoes': 1, 'top': 2, 'outer': 3}
person = np.clip(cv2.GaussianBlur((sB[...,0] < .5).astype(np.float32), (0,0), .8), 0, 1)
def composite(items):
    col = B.astype(np.float32).copy(); al = person.copy()
    for g in sorted(items, key=lambda g: ORDER[ITEMS[g]['cat']]):
        L = cv2.imread(f'L_{g}.png', cv2.IMREAD_UNCHANGED); D = cv2.cvtColor(L[...,:3], cv2.COLOR_BGR2RGB).astype(np.float32); a = L[...,3].astype(np.float32)/255
        col = D*a[...,None] + col*(1-a[...,None]); al = np.maximum(al, a)
    return col, al
# ---------- joints (image coords) ----------
P = lambda i: k[i].astype(np.float64)
hipC = (P(23)+P(24))/2; shC = (P(11)+P(12))/2
J = {'root': np.array([512., 1480.]), 'hip': hipC, 'spine': hipC + .45*(shC-hipC), 'neck': shC - np.array([0, 8.]),
     'head': np.array([shC[0], P(0)[1] + .62*(shC[1]-P(0)[1])]),
     'upperarm_A': P(12), 'forearm_A': P(14), 'hand_A': P(16), 'upperarm_B': P(11), 'forearm_B': P(13), 'hand_B': P(15),
     'thigh_A': P(24), 'shin_A': P(26), 'foot_A': P(28), 'thigh_B': P(23), 'shin_B': P(25), 'foot_B': P(27)}
PARENT = {'root': None, 'hip': 'root', 'spine': 'hip', 'neck': 'spine', 'head': 'neck',
          'upperarm_A': 'spine', 'forearm_A': 'upperarm_A', 'hand_A': 'forearm_A', 'upperarm_B': 'spine', 'forearm_B': 'upperarm_B', 'hand_B': 'forearm_B',
          'thigh_A': 'hip', 'shin_A': 'thigh_A', 'foot_A': 'shin_A', 'thigh_B': 'hip', 'shin_B': 'thigh_B', 'foot_B': 'shin_B'}
BONES = list(PARENT); BI = {b: i for i, b in enumerate(BONES)}
toS = lambda p: (float(p[0] - 512), float(1480 - p[1]))          # image -> spine coords (y up, origin at the feet)
# ---------- part masks ----------
def arm_mask(side):
    sh, tip = (P(12), P(20)) if side == 'A' else (P(11), P(19))
    sgn = -1 if side == 'A' else 1; occ = person > .5; gap = []
    for y in range(int(sh[1]), int(tip[1] + 75)):
        row = occ[y]; x = int(P(24 if side == 'A' else 23)[0])        # start inside the thigh/torso on this side, not on the centre line
        while 0 < x < W-1 and row[x]: x += sgn
        xt = x
        while 0 < x < W-1 and not row[x]: x += sgn
        if abs(xt - x) > 2 and 0 < x < W-1 and abs(x - sh[0]) < 160: gap.append((y, (xt + x)/2))
    T = (sh[0] - sgn*18, sh[1] - 65); edge = 0 if side == 'A' else W; bottom = int(tip[1] + 75)
    poly = [(edge, T[1]), T, (gap[0][1], gap[0][0])] + [(x, y) for y, x in gap[::6]] + [(gap[-1][1], bottom), (edge, bottom)]
    m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [np.array(poly, np.int32)], 255); return cv2.GaussianBlur(m, (0,0), 1.2)/255.
def tight(m):
    core = ((m > .5) & (person > .5)).astype(np.uint8)
    return cv2.GaussianBlur(cv2.dilate(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (45, 45))).astype(np.float32), (0,0), 2.0)
armA, armB = tight(arm_mask('A')), tight(arm_mask('B')); notArm = 1 - np.maximum(armA, armB)
split = int(hipC[1]); yy = np.arange(H)[:, None]
upperM = np.maximum(np.clip((split + 30 - yy)/6, 0, 1), np.maximum(armA, armB)); lowerM = notArm * np.clip((yy - (split - 30))/6, 0, 1)
PARTS = {'lower': lowerM, 'upper': upperM}
armBlur = {s: cv2.GaussianBlur(m.astype(np.float32), (0,0), 18) for s, m in (('A', armA), ('B', armB))}
comps = {o: composite(items) for o, items in OUTFITS.items()}
# fixed region per part = union of all outfits (same size for every skin -> linked meshes share UVs)
boxes = {}
for pn, pm in PARTS.items():
    u = np.zeros((H, W), bool)
    for o, (c, a) in comps.items(): u |= (a*pm) > .02
    ys, xs = np.where(u); boxes[pn] = [int(xs.min())-2, int(ys.min())-2, int(xs.max()-xs.min())+5, int(ys.max()-ys.min())+5]
# ---------- atlas pages (one per outfit, identical layout) ----------
layout = {}; x = 0
for pn in PARTS: layout[pn] = (x, 0); x += boxes[pn][2] + 2
PW, PH = x, max(b[3] for b in boxes.values())
atlas = []
for o, (c, a) in comps.items():
    page = np.zeros((PH, PW, 4), np.uint8)
    for pn, pm in PARTS.items():
        bx, by, bw, bh = boxes[pn]; px, py = layout[pn]
        rgba = np.dstack([c, a*pm*255])[by:by+bh, bx:bx+bw]
        page[py:py+bh, px:px+bw] = np.clip(rgba, 0, 255).astype(np.uint8)
    Image.fromarray(page, 'RGBA').save(f'{OUT}/{o}.png', optimize=True)
    atlas.append(f'{o}.png\nsize:{PW},{PH}\nfilter:Linear,Linear\n' + ''.join(f'{o}/{pn}\nbounds:{layout[pn][0]},{layout[pn][1]},{boxes[pn][2]},{boxes[pn][3]}\n' for pn in PARTS))
open(f'{OUT}/skeleton.atlas', 'w').write('\n'.join(atlas))
# ---------- weights ----------
ss = lambda e0, e1, v: np.clip((v-e0)/(e1-e0), 0, 1)**2*(3-2*np.clip((v-e0)/(e1-e0), 0, 1))
def segd(p, a, b):
    ab = b-a; t = np.clip(((p-a)@ab)/(ab@ab), 0, 1); return np.linalg.norm(p - (a + t[:,None]*ab), axis=1)
def chain_w(p, j0, j1, j2, tip):     # upper / mid / end segment weights along a limb
    d0, d1, d2 = segd(p, j0, j1), segd(p, j1, j2), segd(p, j2, tip)
    w1 = ss(-22, 22, d0 - d1); w2 = ss(-14, 14, np.minimum(d0, d1) - d2)
    return np.stack([(1-w1)*(1-w2), w1*(1-w2), w2], 1)
def torso_w(p): return weights('torso', p)
def weights(pn, p):
    n = len(p); Wt = np.zeros((n, len(BONES)))
    if pn == 'upper':
        Wt = torso_w(p)
        xi = np.clip(p[:,0].astype(int), 0, W-1); yi = np.clip(p[:,1].astype(int), 0, H-1)
        for s in ('A', 'B'):
            j0, j1, j2 = J['upperarm_'+s], J['forearm_'+s], J['hand_'+s]; tip = P(20 if s == 'A' else 19); tip = tip + (tip - j2)*.6
            cw = chain_w(p, j0, j1, j2, tip); d = (j1-j0)/np.linalg.norm(j1-j0); along = (p - j0) @ d
            inside = (armA if s == 'A' else armB)[yi, xi]
            near = np.clip(armBlur[s][yi, xi]*1.6, 0, 1)
            shoulder_zone = ss(-80, 0, along) * (1 - ss(15, 70, along))
            wa = inside*ss(-80, 45, along) + (1-inside)*near*shoulder_zone*.6   # torso only bends with the arm near the shoulder
            Wa = np.zeros_like(Wt); Wa[:, BI['upperarm_'+s]], Wa[:, BI['forearm_'+s]], Wa[:, BI['hand_'+s]] = cw[:,0], cw[:,1], cw[:,2]
            Wt = Wt*(1-wa[:,None]) + Wa*wa[:,None]
        Wt[Wt < .01] = 0; return Wt / Wt.sum(1, keepdims=True)
    if pn == 'torso':
        y = p[:,1]; head_y, chin = J['head'][1], P(0)[1] + 55; neck_y, sp_y, hip_y = J['neck'][1], J['spine'][1], J['hip'][1]
        wh = 1 - ss(chin - 5, neck_y + 5, y); wn = (1 - wh) * (1 - ss(neck_y, sp_y, y)); rest = 1 - wh - wn
        wsp = rest * (1 - ss(sp_y, hip_y + 20, y)); whp = rest - wsp
        Wt[:, BI['head']], Wt[:, BI['neck']], Wt[:, BI['spine']], Wt[:, BI['hip']] = wh, wn, wsp, whp
    elif pn.startswith('arm'):
        s = pn[-1]; j0, j1, j2 = J['upperarm_'+s], J['forearm_'+s], J['hand_'+s]; tip = P(20 if s == 'A' else 19); tip = tip + (tip - j2)*.6
        cw = chain_w(p, j0, j1, j2, tip); d = (j1-j0)/np.linalg.norm(j1-j0); along = (p - j0) @ d
        wa = ss(-50, 20, along)                                            # shoulder seam blends into the chest
        Wt[:, BI['upperarm_'+s]], Wt[:, BI['forearm_'+s]], Wt[:, BI['hand_'+s]] = cw[:,0]*wa, cw[:,1]*wa, cw[:,2]*wa
        Wt[:, BI['spine']] = 1 - wa
    else:  # lower: both legs, blended across the centre line (skirts stretch between the legs)
        side = ss(-28, 28, hipC[0] - p[:,0])                             # 1 = image-left leg (A)
        for s, ws in (('A', side), ('B', 1-side)):
            j0, j1, j2 = J['thigh_'+s], J['shin_'+s], J['foot_'+s]; toe = j2 + np.array([0, 70.])
            cw = chain_w(p, j0, j1, j2, toe); along = (p[:,1] - j0[1])
            wl = ss(-25, 35, along)                                        # top of the thighs blends into the pelvis
            Wt[:, BI['thigh_'+s]] += ws*cw[:,0]*wl; Wt[:, BI['shin_'+s]] += ws*cw[:,1]*wl; Wt[:, BI['foot_'+s]] += ws*cw[:,2]*wl
            Wt[:, BI['hip']] += ws*(1-wl)
    Wt[Wt < .01] = 0; return Wt / Wt.sum(1, keepdims=True)
# ---------- meshes ----------
union_alpha = {pn: np.max([a*pm for (c, a) in comps.values()], axis=0) for pn, pm in PARTS.items()}
def mesh(pn, step=14):
    bx, by, bw, bh = boxes[pn]; al = cv2.dilate((union_alpha[pn] > .02).astype(np.uint8), np.ones((9,9),np.uint8))
    xs = np.linspace(bx, bx+bw, max(2, int(bw/step))+1); ys = np.linspace(by, by+bh, max(2, int(bh/step))+1)
    gx, gy = np.meshgrid(xs, ys); pts = np.stack([gx.ravel(), gy.ravel()], 1); nx = len(xs)
    tris = []
    for j in range(len(ys)-1):
        for i in range(nx-1):
            q = [j*nx+i, j*nx+i+1, (j+1)*nx+i, (j+1)*nx+i+1]
            cx_, cy_ = int(min(W-1, (xs[i]+xs[i+1])/2)), int(min(H-1, (ys[j]+ys[j+1])/2))
            x0, x1, y0, y1 = int(xs[i]), int(min(W-1, xs[i+1])), int(ys[j]), int(min(H-1, ys[j+1]))
            if al[y0:y1+1, x0:x1+1].any(): tris += [q[0], q[1], q[2], q[1], q[3], q[2]]
    used = sorted(set(tris)); remap = {v: n for n, v in enumerate(used)}; pts = pts[used]; tris = [remap[t] for t in tris]
    Wt = weights(pn, pts); verts = []
    if pn == 'upper':
        armness = Wt[:, [BI[b] for b in BI if b.startswith(('upperarm','forearm','hand'))]].sum(1)
        tri3 = np.array(tris).reshape(-1, 3); order = np.argsort(armness[tri3].mean(1), kind='stable'); tris = tri3[order].ravel().tolist()
    for p_, w in zip(pts, Wt):
        nz = np.nonzero(w)[0]; verts.append(len(nz))
        for b in nz:
            sx, sy = toS(p_); bxw, byw = toS(J[BONES[b]]); verts += [int(b), round(sx - bxw, 2), round(sy - byw, 2), round(float(w[b]), 4)]
    uvs = []
    for p_ in pts: uvs += [round(float((p_[0]-bx)/bw), 5), round(float((p_[1]-by)/bh), 5)]
    return {'type': 'mesh', 'path': f'o1/{pn}', 'uvs': uvs, 'triangles': tris, 'vertices': verts, 'hull': 0, 'width': bw, 'height': bh}, len(pts)
bones = []
for b in BONES:
    e = {'name': b}
    if PARENT[b]: e['parent'] = PARENT[b]
    x, y = toS(J[b]); px, py = toS(J[PARENT[b]]) if PARENT[b] else (0., 0.)
    if PARENT[b]: e['x'], e['y'] = round(x - px, 2), round(y - py, 2)
    bones.append(e)
slots = [{'name': pn, 'bone': 'root', 'attachment': pn} for pn in ['lower', 'upper']]
default = {}; nverts = {}
for pn in PARTS: m, n = mesh(pn); default[pn] = {pn: m}; nverts[pn] = n
skins = [{'name': 'default', 'attachments': default}]
for o in list(OUTFITS)[1:]:
    skins.append({'name': o, 'attachments': {pn: {pn: {'type': 'linkedmesh', 'skin': 'default', 'parent': pn, 'path': f'{o}/{pn}', 'width': boxes[pn][2], 'height': boxes[pn][3]}} for pn in PARTS}})
skel = {'skeleton': {'hash': 'dressup', 'spine': '4.2.40', 'x': -512, 'y': -60, 'width': 1024, 'height': 1540, 'images': './', 'audio': ''},
        'bones': bones, 'slots': slots, 'skins': skins}
json.dump({'skel': skel, 'joints': {b: toS(J[b]) for b in BONES}}, open(f'{OUT}/rig_base.json', 'w'))
print('bones', len(bones), 'vertices', nverts, 'page', (PW, PH))
