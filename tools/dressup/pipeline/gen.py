import sys, os, json, base64, requests, time
H = {}   # the session's network proxy adds the OpenAI credential; no key is stored here
def save(resp, out):
    d = resp.json()
    if 'error' in d: print('ERROR', out, d['error'].get('message')); return False
    open(out, 'wb').write(base64.b64decode(d['data'][0]['b64_json']))
    print('saved', out, d.get('usage', {})); return True
def generate(prompt, out, quality='high', size='1024x1536'):
    r = requests.post('https://api.openai.com/v1/images/generations', headers=H, timeout=600,
        json={'model': 'gpt-image-2', 'prompt': prompt, 'size': size, 'quality': quality, 'n': 1})
    return save(r, out)
def edit(src, prompt, out, quality='medium', size='1024x1536', extra=None):
    data = {'model': 'gpt-image-2', 'prompt': prompt, 'size': size, 'quality': quality}
    data.update(extra or {})
    with open(src, 'rb') as f:
        r = requests.post('https://api.openai.com/v1/images/edits', headers=H, timeout=600,
            data=data, files=[('image[]', (os.path.basename(src), f, 'image/png'))])
    return save(r, out)
if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'gen': generate(open(sys.argv[2]).read(), sys.argv[3], *(sys.argv[4:5] or []))
    elif cmd == 'edit': edit(sys.argv[2], open(sys.argv[3]).read(), sys.argv[4], *(sys.argv[5:6] or []))
