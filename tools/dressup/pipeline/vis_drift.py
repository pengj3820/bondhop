import json, numpy as np, cv2
exec(open('pipeline.py').read().split("only = sys.argv")[0])
qa = json.load(open('qa.json')); idx = list(NAMES)
for g in qa:
    a = cv2.imread(f'L_{g}.png', cv2.IMREAD_UNCHANGED)[...,3]
    cover = dil(a > 128, 21)
    kD = kps(load(f'd_{g}.png'))
    vis = [i for i in idx if not cover[int(np.clip(k[i,1],0,H-1)), int(np.clip(k[i,0],0,W-1))]]
    d = np.linalg.norm(kD[vis]-k[vis], axis=1)
    qa[g]['vis_drift_max'] = round(float(d.max()),1); qa[g]['vis_worst'] = NAMES[vis[int(d.argmax())]]; qa[g]['vis_joints'] = len(vis)
    fails = [f for f in qa[g]['fails'] if f != '姿势漂移']
    if qa[g]['vis_drift_max'] > 15: fails.append('姿势漂移')
    qa[g]['fails'] = fails; qa[g]['pass'] = not fails
    print(f"{g:9s} all-joints max {qa[g]['pose_max']:5.1f}  visible-joints({len(vis):2d}) max {qa[g]['vis_drift_max']:5.1f} ({qa[g]['vis_worst']})  {'PASS' if qa[g]['pass'] else 'FAIL'}")
json.dump(qa, open('qa.json','w'), ensure_ascii=False, indent=1)
