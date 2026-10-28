# regenerate a garment N times and keep the candidate whose pose drifts least from the base model
import sys, numpy as np, cv2, concurrent.futures as cf
from gen import edit
from dress import T, ITEMS
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
g, n = sys.argv[1], int(sys.argv[2])
extra = (" The coat hangs straight down and stays open; the legs underneath must remain exactly where they are in the input photo.")
prompt = T.format(g=ITEMS[g]) + extra
with cf.ThreadPoolExecutor(n) as ex:
    list(ex.map(lambda i: edit('base.png', prompt, f'cand_{g}_{i}.png', 'medium'), range(n)))
pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path='models/pose.task')))
def kps(p):
    a = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB); r = pose.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=a))
    return np.array([[l.x*a.shape[1], l.y*a.shape[0]] for l in r.pose_landmarks[0]])
idx = [0,7,8,11,12,13,14,15,16,23,24,25,26,27,28]
kb = kps('base.png')
cands = [f'd_{g}.png'] + [f'cand_{g}_{i}.png' for i in range(n)]
scores = []
for c in cands:
    try: d = np.linalg.norm(kps(c)[idx] - kb[idx], axis=1); scores.append((d.max(), d.mean(), c))
    except Exception as e: print('skip', c, e)
for s in sorted(scores): print(f'{s[2]}: max {s[0]:.1f}px mean {s[1]:.1f}px')
best = sorted(scores)[0][2]; print('BEST', best)
import shutil; shutil.copy(best, f'd_{g}.png') if best != f'd_{g}.png' else None
