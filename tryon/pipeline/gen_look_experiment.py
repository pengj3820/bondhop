import sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from concurrent.futures import ThreadPoolExecutor
from common import ASSETS, RAW, edit
KEEP = (" Keep the exact same woman: identical face, identity, hairstyle color, body shape, skin tone, standing pose, "
        "camera framing, scale and the plain light grey studio background. Photorealistic fashion photo.")
LOOKS = {
 "look_gothic": "Dress this woman in a gothic lolita costume: a black and deep crimson lace corset bodice with lacing, "
   "long sheer black lace puff sleeves, a layered ruffled high-low skirt of crimson and black tulle and lace that is "
   "short in front and floor length at the back, sheer black thigh-high stockings, black chunky platform lace-up boots, "
   "a black lace choker and a dark red rose hair clip in her bun.",
 "look_angel": "Dress this woman in a dark angel costume: huge black feathered wings spreading out behind her back, "
   "a black corset bodice, a long sheer black tulle skirt open at the front over black shorts, black lace fingerless "
   "arm gloves, black platform boots, a black feather hair ornament.",
}
def run(k):
    try:
        edit([ASSETS / "model_photo.png"], LOOKS[k] + KEEP, model="gpt-image-1.5", fidelity="high").save(RAW / f"{k}.png")
        print("ok", k, flush=True)
    except Exception as e:
        print("ERR", k, repr(e)[:200], flush=True)
with ThreadPoolExecutor(2) as ex: list(ex.map(run, LOOKS))
