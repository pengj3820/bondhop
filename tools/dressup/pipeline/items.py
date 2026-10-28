# category: top / outer / bottom / full / shoes ; length decides the change zone ; replaces = basewear it takes off
ITEMS = {
 # --- first round ---
 'tee':      dict(name='白T恤',     cat='top',    length='short', replaces='tank',  desc='a plain white crew-neck cotton short-sleeve T-shirt worn untucked, hem at the hip'),
 'jeans':    dict(name='直筒牛仔裤', cat='bottom', length='long',  replaces='shorts', desc='classic mid-blue straight-leg full-length jeans reaching the ankles, feet still barefoot'),
 'trench':   dict(name='驼色风衣',   cat='outer',  length='long',  replaces=None,    desc='a camel-colored double-breasted knee-length trench coat, worn open, sleeves to the wrists'),
 'skirt':    dict(name='黑色百褶短裙', cat='bottom', length='short', replaces='shorts', desc='a black pleated mini skirt sitting at the waist'),
 'swim':     dict(name='红色连体泳衣', cat='full',   length='swim',  replaces='both',  desc='a red one-piece swimsuit with scoop neckline, replacing the gray tank top and shorts'),
 'sneakers': dict(name='小白鞋',     cat='shoes',  length='low',   replaces=None,    desc='white low-top leather sneakers on both feet'),
 # --- expansion ---
 'shirt':    dict(name='蓝白条纹衬衫', cat='top',  length='long',  replaces='tank',  desc='a blue-and-white striped button-up long-sleeve shirt worn untucked, sleeves to the wrists'),
 'hoodie':   dict(name='黑色连帽卫衣', cat='top',  length='long',  replaces='tank',  desc='a plain black pullover hoodie with the hood down, sleeves to the wrists, hem at the hip'),
 'sweater':  dict(name='米白麻花毛衣', cat='top',  length='long',  replaces='tank',  desc='a cream cable-knit crew-neck wool sweater, sleeves to the wrists, hem at the hip'),
 'cami':     dict(name='绿色缎面吊带', cat='top',  length='short', replaces='tank',  desc='an emerald green satin camisole with thin spaghetti straps, hem at the waist'),
 'denimjk':  dict(name='牛仔夹克',   cat='outer',  length='short', replaces=None,    desc='a classic light-blue denim jacket worn open, sleeves to the wrists, hem at the waist'),
 'leather':  dict(name='黑色皮夹克', cat='outer',  length='short', replaces=None,    desc='a black leather biker jacket worn open, sleeves to the wrists, hem at the waist'),
 'wide':     dict(name='卡其阔腿裤', cat='bottom', length='long',  replaces='shorts', desc='high-waisted khaki wide-leg trousers reaching the ankles, feet still barefoot'),
 'dshorts':  dict(name='牛仔短裤',   cat='bottom', length='short', replaces='shorts', desc='light-blue denim shorts with a frayed hem, high-waisted, short length'),
 'cargo':    dict(name='军绿工装裤', cat='bottom', length='long',  replaces='shorts', desc='olive green cargo pants with side pockets, full length to the ankles, feet still barefoot'),
 'midi':     dict(name='碎花半身长裙', cat='bottom', length='midi', replaces='shorts', desc='a flowing floral-print midi skirt falling to mid-calf'),
 'lbd':      dict(name='黑色小礼服', cat='full',   length='knee',  replaces='both',  desc='a simple black sleeveless knee-length sheath dress'),
 'sundress': dict(name='黄色碎花裙', cat='full',   length='midi',  replaces='both',  desc='a yellow floral sleeveless sundress falling to mid-calf'),
 'jumpsuit': dict(name='牛仔连体裤', cat='full', length='long', replaces='both', desc='a medium-blue denim boiler jumpsuit with short sleeves and full-length legs to the ankles, feet still barefoot'),
 'boots':    dict(name='黑色短靴',   cat='shoes',  length='ankle', replaces=None,    desc='black leather ankle boots on both feet'),
}
REPL = {'tank': ' It replaces the gray tank top.', 'shorts': ' It replaces the gray shorts.', 'both': '', None: ''}
