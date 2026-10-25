# 用 edge-tts 为每句旁白生成配音，输出 build/audio/<scene>_<i>.mp3 和 build/timing.json
import asyncio, json, os, ssl, subprocess

import edge_tts
import edge_tts.communicate as communicate

from script import SCENES

# 走代理时需要信任代理的 CA；未设置时用默认证书
CA = os.environ.get("SSL_CERT_FILE") or "/root/.ccr/ca-bundle.crt"
if os.path.exists(CA):
    communicate._SSL_CTX = ssl.create_default_context(cafile=CA)

VOICE = "zh-CN-XiaoxiaoNeural"
OUT = "build/audio"


def duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", path])
    return float(out)


async def main():
    os.makedirs(OUT, exist_ok=True)
    timing = {}
    for key, _, lines in SCENES:
        timing[key] = []
        for i, text in enumerate(lines):
            path = f"{OUT}/{key}_{i}.mp3"
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                await edge_tts.Communicate(text, VOICE, rate="-8%").save(path)
            timing[key].append(duration(path))
            print(key, i, round(timing[key][-1], 2))
    with open("build/timing.json", "w") as f:
        json.dump(timing, f, indent=1)


asyncio.run(main())
