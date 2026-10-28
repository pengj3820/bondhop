import sys, concurrent.futures as cf
from gen import edit
T = ("Dress this exact same person in {g}. Keep everything else exactly identical to the input photo: same person, same face, "
     "same hair, same body shape and proportions, same pose with arms and legs in exactly the same positions, same camera framing "
     "and scale, same background and lighting. Do not move, resize or reposition anything. Only add the garment; any basewear it does "
     "not cover stays exactly as it is.")
ITEMS = {
 'tee':  'a plain white crew-neck cotton short-sleeve T-shirt worn untucked, hem at the hip',
 'jeans':'classic mid-blue straight-leg full-length jeans reaching the ankles, feet still barefoot',
 'trench':'a camel-colored double-breasted knee-length trench coat, worn open, sleeves to the wrists',
 'skirt':'a black pleated mini skirt sitting at the waist',
 'swim': 'a red one-piece swimsuit with scoop neckline, replacing the gray tank top and shorts',
 'sneakers':'white low-top leather sneakers on both feet',
}
if __name__ == '__main__':
    keys = sys.argv[1:] or list(ITEMS)
    def run(k):
        open(f'p_{k}.txt','w').write(T.format(g=ITEMS[k]))
        return k, edit('base.png', T.format(g=ITEMS[k]), f'd_{k}.png', 'medium', '1024x1536')
    with cf.ThreadPoolExecutor(6) as ex:
        for k, ok in ex.map(run, keys): print(k, ok)
