import sys, os, concurrent.futures as cf
from gen import edit
from dress import T
from items import ITEMS, REPL
keys = [k for k in (sys.argv[1:] or ITEMS) if not os.path.exists(f'd_{k}.png')]
def run(k):
    it = ITEMS[k]; p = T.format(g=it['desc']) + REPL[it['replaces']]
    return k, edit('base.png', p, f'd_{k}.png', 'medium')
with cf.ThreadPoolExecutor(7) as ex:
    for k, ok in ex.map(run, keys): print(k, 'OK' if ok else 'FAILED')
