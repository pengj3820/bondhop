"""Step 1: generate candidate base-model photos (fixed pose, fixed canvas)."""
import sys
from concurrent.futures import ThreadPoolExecutor

from common import RAW, generate

PROMPT = (
    "Full-body studio fashion photo, photorealistic, of a young East Asian woman standing straight, "
    "facing the camera directly, symmetric neutral pose, feet slightly apart, "
    "both arms hanging down and held about 20 degrees away from the torso so there is a clear gap of "
    "background between each arm and the body, hands relaxed, fingers together. "
    "Her hair is pulled back tightly into a neat high bun, no loose strands on the neck or shoulders. "
    "She wears only a plain nude-beige seamless fitted sleeveless bodysuit with a round neckline that ends "
    "at the top of the thighs, barefoot. Natural relaxed expression. "
    "Plain uniform light grey seamless studio background (#D9D9D9), soft even frontal lighting, minimal shadows. "
    "The entire body from the top of the head to the toes is in frame, centered, with a margin above the head "
    "and below the feet. Shot on 85mm, sharp focus, high detail."
)


def one(i):
    p = RAW / f"model_candidate_{i}.png"
    generate(PROMPT).save(p)
    print("saved", p, flush=True)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    with ThreadPoolExecutor(n) as ex:
        list(ex.map(one, range(n)))
