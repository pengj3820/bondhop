"""Batch production of garment parts (offline):  generate -> register -> extract -> QA, retrying a part whose
QA fails (base body visible, part cut at its slot limit, empty result) up to --retries times.

    python batch.py                    all catalogue items without a passing layer
    python batch.py --force id1 id2    regenerate these even if they already pass
"""
import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import RAW

HERE = Path(__file__).parent
CAT = json.load(open(HERE / "catalog.json"))


def passing(gid):
    p = RAW / f"{gid}_qa.json"
    return p.exists() and json.load(open(p)).get("pass")


def produce(item, retries):
    gid = item["id"]
    for attempt in range(1 + retries):
        g = subprocess.run([sys.executable, str(HERE / "gen_garment.py"), gid], capture_output=True, text=True)
        if not (RAW / f"{gid}_onmodel.png").exists() or "FAILED" in g.stdout:
            reason = "generation refused/failed" if "safety" not in g.stdout else "refused by safety system"
            print(f"[{gid}] attempt {attempt + 1}: {reason}", flush=True)
            continue
        subprocess.run([sys.executable, str(HERE / "extract.py"), gid], capture_output=True, text=True)
        qa = json.load(open(RAW / f"{gid}_qa.json"))
        print(f"[{gid}] attempt {attempt + 1}: {'PASS' if qa['pass'] else 'FAIL'} {qa}", flush=True)
        if qa["pass"]:
            return gid, True
    return gid, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    items = [c for c in CAT if (not a.ids or c["id"] in a.ids) and (a.force or not passing(c["id"]))]
    print(f"producing {len(items)} parts", flush=True)
    with ThreadPoolExecutor(a.workers) as ex:
        results = list(ex.map(lambda it: produce(it, a.retries), items))
    bad = [g for g, ok in results if not ok]
    print("done; failed:", bad or "none")
    subprocess.run([sys.executable, str(HERE / "build_manifest.py")])


if __name__ == "__main__":
    main()
