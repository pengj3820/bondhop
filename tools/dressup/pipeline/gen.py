"""OpenAI image calls (gpt-image-2). The session's network proxy adds the credential; no key is stored or sent here.

Every call is appended to calls.log in the working directory so each stage can report how many image calls it used.
Non-JSON responses (proxy timeouts, HTML error pages) are printed with their status code instead of crashing.

Requests are streamed (SSE, with partial images): the egress proxy answers 502 "upstream request failed" when no
response header arrives within ~30 s, and a non-streamed high-quality image takes longer than that.
"""
import sys, os, json, base64, time, requests
URL = 'https://api.openai.com/v1/images/'

def _log(kind, out, status, ok, secs):
    with open('calls.log', 'a') as f:
        f.write(json.dumps({'t': time.strftime('%H:%M:%S'), 'kind': kind, 'out': out, 'status': status, 'ok': ok, 'secs': round(secs)}) + '\n')

def _call(kind, out, send, retries=2):
    for attempt in range(retries + 1):
        t0 = time.time()
        try:
            r = send()
        except requests.RequestException as e:
            print('NETWORK', out, type(e).__name__, str(e)[:200]); _log(kind, out, None, False, time.time() - t0)
            time.sleep(5 * (attempt + 1)); continue
        try:
            d = _read(r)
        except ValueError:
            print('NON-JSON', out, r.status_code, r.headers.get('content-type'), r.text[:500])
            _log(kind, out, r.status_code, False, time.time() - t0)
            if r.status_code >= 500 or r.status_code == 429: time.sleep(10 * (attempt + 1)); continue
            return False
        if 'error' in d or r.status_code != 200:
            msg = (d.get('error') or {}).get('message', str(d)[:300])
            print('ERROR', out, r.status_code, msg); _log(kind, out, r.status_code, False, time.time() - t0)
            if r.status_code >= 500 or r.status_code == 429: time.sleep(10 * (attempt + 1)); continue
            return False   # 4xx (e.g. safety refusal) will not change on retry
        r.close(); open(out, 'wb').write(base64.b64decode(d['data'][0]['b64_json']))
        _log(kind, out, 200, True, time.time() - t0)
        print('saved', out, r.status_code, f'{time.time()-t0:.0f}s', d.get('usage', {}).get('total_tokens')); return True
    return False

def _read(r):
    """Return the final JSON payload of a streamed (SSE) or plain response."""
    if r.status_code != 200 or 'event-stream' not in r.headers.get('content-type', ''):
        return r.json()
    last = None
    for line in r.iter_lines(decode_unicode=True):
        if line and line.startswith('data:'):
            ev = json.loads(line[5:])
            if ev.get('type', '').endswith('.completed'): last = {'data': [{'b64_json': ev['b64_json']}], 'usage': ev.get('usage', {})}
            elif ev.get('type') == 'error' or 'error' in ev: return {'error': ev.get('error', ev)}
    if last is None: raise ValueError('stream ended without a completed image')
    return last

STREAM = {'stream': True, 'partial_images': 2}

def generate(prompt, out, quality='high', size='1024x1536'):
    return _call('gen', out, lambda: requests.post(URL + 'generations', timeout=900,
        stream=True,
        json={'model': 'gpt-image-2', 'prompt': prompt, 'size': size, 'quality': quality, 'n': 1, **STREAM}))

def edit(srcs, prompt, out, quality='medium', size='1024x1536', extra=None):
    """srcs: one path or a list of paths; with several images the prompt refers to them as image 1, image 2, ..."""
    srcs = [srcs] if isinstance(srcs, str) else list(srcs)
    data = {'model': 'gpt-image-2', 'prompt': prompt, 'size': size, 'quality': quality, 'stream': 'true', 'partial_images': '2'}
    data.update(extra or {})
    def send():
        fs = [open(s, 'rb') for s in srcs]
        try:
            return requests.post(URL + 'edits', timeout=900, data=data, stream=True,
                                 files=[('image[]', (f'img{i}.png', f, 'image/png')) for i, f in enumerate(fs)])
        finally:
            for f in fs: f.close()
    return _call('edit', out, send)

def count():
    if not os.path.exists('calls.log'): return 0, 0
    rows = [json.loads(l) for l in open('calls.log')]
    return len(rows), sum(r['ok'] for r in rows)

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'gen': generate(open(sys.argv[2]).read(), sys.argv[3], *(sys.argv[4:5] or []))
    elif cmd == 'edit': edit(sys.argv[2].split(','), open(sys.argv[3]).read(), sys.argv[4], *(sys.argv[5:6] or []))
    elif cmd == 'count': print('calls (total, ok):', count())
