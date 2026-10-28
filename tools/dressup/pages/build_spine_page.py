import json
css = open('player.css', encoding='utf-8').read()
M = [  # key, name, group, amplitude, verdict [short sleeve, long sleeve/long skirt, long coat], problem, fix
 ['idle','待机呼吸','头与躯干','躯干缩放 1.2%，头 ±2°',['安全','安全','安全'],'看不出变形。','—'],
 ['head_tilt','歪头','头与躯干','头 ±12°，脖子 ±3°',['安全','安全','安全'],'脖子有轻微拉伸，不明显。','调脖子权重即可。'],
 ['lean','身体侧弯','头与躯干','躯干 ±12°',['安全','可用','勉强'],'短袖没问题；长外套在腰部上下两块网格的接缝处会断开。','外套衣身做成独立插槽、权重覆盖整段躯干；或在躯干多加一根骨骼。'],
 ['wave_small','小幅抬手','手臂','上臂 12°，前臂 75°',['安全','可用','可用'],'长袖手肘内侧轻微被挤。','手肘处加变形关键帧修形。'],
 ['hands_hips','叉腰','手臂','上臂 38°，前臂 72°',['安全','可用','可用'],'效果较好，手肘有轻微挤压。','手肘变形关键帧。'],
 ['arms_45','双臂外展','手臂','上臂 45°',['安全','可用','勉强'],'长袖肩部开始被拉长；风衣两侧衣片被划进手臂，抬手时被带走。','外套衣身侧片单独切出来，不跟手臂走；肩部加权重过渡。'],
 ['wave_hi','举手打招呼','手臂','上臂 30°，前臂折 150°',['可用','勉强','勉强'],'手肘被折扁，长袖肘部像被压扁的管子。','变形关键帧大量修形，或在终点换成真实姿势图。'],
 ['arms_front','手放身前','手臂','前臂 118° 横过腹部',['可用','可用','勉强'],'手臂压在身前是对的（手臂插槽在上层），但肘部被挤；风衣袖子过粗。','手肘变形关键帧；风衣袖子单独切。'],
 ['arms_90','双臂平举','手臂','上臂 88°',['可用','勉强','勉强'],'肩膀和腋下被拉开，长袖整条被拉长，肩线变形明显。','平举姿势用真实关键姿势图；网格只做过渡。'],
 ['arms_up','双手举过头','手臂','上臂 160°',['不建议','不建议','不建议'],'肩部和腋下严重变形，袖子被拉成长条，看起来已经不像人。','必须用真实关键姿势图（举手素模 + 每件衣服的举手图）。'],
 ['leg_side','侧抬腿','腿','大腿 28°',['可用','不建议','不建议'],'裤子还行；长裙和风衣下摆被腿带着撕开。','裙摆、衣摆单独插槽，挂独立骨骼 + 物理约束，不直接跟腿。'],
 ['march','原地踏步','腿','大腿纵向压缩 22%',['可用','勉强','勉强'],'正面视角只能把大腿“缩短”来表示抬膝，看起来像在下沉；裙子跟着腿变形。','正面踏步只能接受这个效果；要自然需要侧面或 3/4 视角素模。'],
 ['kick','踢腿','腿','大腿 70°，小腿 35°',['不建议','做不到','做不到'],'裆部被撕开，裤腿被拉长；长裙、风衣被拉成扇形。','不做，或用真实姿势图 / 视频生成。'],
 ['jump','跳跃','全身','整体上移，双臂抬起',['安全','可用','可用'],'整体位移本身没问题，问题只来自手臂抬起的幅度。','—'],
 ['bow','鞠躬','全身','躯干纵向压缩 18%',['做不到','做不到','做不到'],'正面视角无法表现向前弯腰，只能把身体压扁。','视频生成，或侧面素模。'],
 ['turn','转身','全身','水平翻转',['做不到','做不到','做不到'],'只能把人压成一张纸再翻面，翻过来还是正面图。','视频生成，或多角度素模（正面、侧面、背面各一套）。'],
]
OUT = [['default','T恤 + 牛仔裤',0],['o2','毛衣 + 碎花长裙',1],['o3','吊带 + 短裤 + 皮夹克',1],['o4','碎花连衣裙',1],['o5','卫衣 + 工装裤 + 风衣',2],['o6','衬衫 + 阔腿裤',1]]
counts = {}
for col in range(3):
    c = {}
    for m in M: c[m[4][col]] = c.get(m[4][col], 0) + 1
    counts[col] = c
page = """<title>Spine 动作幅度验证</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@600;700&family=Noto+Sans+SC:wght@400;500;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>/* spine-player 4.2.119 stylesheet (inlined) */
__CSS__</style>
<style>
/* Layout: a rigging bench - the live Spine player stays on the left, the motion ladder (small to large) on the right */
:root{
  --bg:#EEF0EC; --panel:#FFFFFF; --stage:#E4E7E1; --fg:#1B201E; --muted:#59625D; --line:#D2D8D2; --accent:#1F6F68; --accent-soft:#DCEDEA;
  --ok:#2E7D4F; --ok-bg:#DFF1E5; --use:#2C5EAA; --use-bg:#E1EAF7; --meh:#9A6A0B; --meh-bg:#F6EBCF; --no:#B4532A; --no-bg:#F8E3D8; --never:#8E2C2C; --never-bg:#F3DCDC;
  --f-display:"Noto Serif SC","Songti SC",serif; --f-body:"Noto Sans SC","PingFang SC","Microsoft YaHei",system-ui,sans-serif; --f-mono:"JetBrains Mono",ui-monospace,Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#131716; --panel:#1B201E; --stage:#242A28; --fg:#E6EAE7; --muted:#9AA39E; --line:#323A37; --accent:#6FC7BD; --accent-soft:#1E3633;
  --ok:#6FCB94; --ok-bg:#183326; --use:#8DB2F0; --use-bg:#1B2840; --meh:#E6B652; --meh-bg:#3A2F14; --no:#EE9A72; --no-bg:#3D2318; --never:#F08C8C; --never-bg:#3E1C1C; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#131716; --panel:#1B201E; --stage:#242A28; --fg:#E6EAE7; --muted:#9AA39E; --line:#323A37; --accent:#6FC7BD; --accent-soft:#1E3633;
  --ok:#6FCB94; --ok-bg:#183326; --use:#8DB2F0; --use-bg:#1B2840; --meh:#E6B652; --meh-bg:#3A2F14; --no:#EE9A72; --no-bg:#3D2318; --never:#F08C8C; --never-bg:#3E1C1C; color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:var(--f-body);font-size:15px;line-height:1.7}
.wrap{max-width:1160px;margin:0 auto;padding-block:36px 72px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:48px}
h1,h2,h3{font-family:var(--f-display);margin:0;line-height:1.3;text-wrap:balance}
h1{font-size:clamp(28px,4vw,40px)} h2{font-size:23px} h3{font-size:16px}
p{margin:0}
.eyebrow{font-family:var(--f-mono);font-size:12px;letter-spacing:.08em;color:var(--accent)}
.lede{color:var(--muted);max-width:70ch;margin-top:10px}
section{display:grid;gap:18px;min-width:0}
.wrap>*,section>*{min-width:0}
.sec-head{display:grid;gap:6px;max-width:72ch}
.sec-head p{color:var(--muted)}
.legend{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:13px;color:var(--muted);align-items:center}
.pill{display:inline-block;font-size:12px;line-height:1;padding:5px 8px;border-radius:99px;white-space:nowrap;font-weight:500}
.v-安全{color:var(--ok);background:var(--ok-bg)} .v-可用{color:var(--use);background:var(--use-bg)} .v-勉强{color:var(--meh);background:var(--meh-bg)}
.v-不建议{color:var(--no);background:var(--no-bg)} .v-做不到{color:var(--never);background:var(--never-bg)}
.lab{display:grid;grid-template-columns:minmax(0,420px) minmax(0,1fr);gap:28px;align-items:start}
.bench{position:sticky;top:calc(env(safe-area-inset-top,0px) + 12px);display:flex;flex-direction:column;gap:12px;min-width:0}
.player-box{width:100%;aspect-ratio:1120/1760;background:var(--stage);border-radius:12px;overflow:hidden;position:relative}
#player{position:absolute;inset:0}
.now{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;display:grid;gap:6px;font-size:14px}
.now h3{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.now .amp{font-family:var(--f-mono);font-size:12.5px;color:var(--muted);font-weight:400}
.now dl{margin:0;display:grid;grid-template-columns:auto 1fr;gap:4px 10px}
.now dt{color:var(--muted)} .now dd{margin:0}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font:inherit;font-size:13px;padding:6px 12px;border-radius:99px;border:1px solid var(--line);background:var(--panel);color:var(--fg);cursor:pointer}
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--bg)}
.chip:focus-visible,.mv:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.speed{display:flex;gap:8px;align-items:center;font-size:13px;color:var(--muted)}
.ladder{display:grid;gap:18px;min-width:0}
.grp-title{font-size:13px;color:var(--muted);font-family:var(--f-mono);letter-spacing:.06em;display:grid;grid-template-columns:1fr repeat(3,74px);gap:8px;align-items:end;padding:0 12px}
.grp-title span{text-align:center;font-family:var(--f-body);letter-spacing:0;font-size:12px}
.grp-title span.on{color:var(--accent);font-weight:700}
.mv{width:100%;font:inherit;text-align:left;display:grid;grid-template-columns:1fr repeat(3,74px);gap:8px;align-items:center;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--panel);color:var(--fg);cursor:pointer}
.mv + .mv{margin-top:6px}
.mv:hover{border-color:var(--accent)}
.mv[aria-pressed="true"]{border-color:var(--accent);box-shadow:0 0 0 1.5px var(--accent)}
.mv b{display:block;font-size:14.5px} .mv small{display:block;font-family:var(--f-mono);font-size:12px;color:var(--muted)}
.mv .pill{justify-self:center}
.mv .pill.dim{opacity:.38}
.strip{overflow-x:auto;border-radius:10px;background:var(--stage)}
.strip img{display:block;height:320px;width:auto;max-width:none}
.strip-cap{font-size:13px;color:var(--muted)}
.order{font-family:var(--f-mono);font-size:12px;color:var(--muted);overflow-x:auto;white-space:nowrap}
.cols{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;display:grid;gap:8px;align-content:start;min-width:0}
.card ul{margin:0;padding-left:20px;display:grid;gap:5px;font-size:14.5px}
.tbl-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
table{border-collapse:collapse;width:100%;min-width:640px;font-size:14px}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--stage)} tr:last-child td{border-bottom:none}
.note{font-size:13px;color:var(--muted);max-width:75ch}
@media (max-width:820px){.lab{grid-template-columns:1fr}.bench{position:static;max-width:420px;width:100%;justify-self:center}.cols{grid-template-columns:1fr}}
@media (max-width:480px){.grp-title,.mv{grid-template-columns:1fr repeat(3,52px)}.pill{font-size:11px;padding:4px 6px}}
</style>

<div class="wrap">
  <header>
    <div class="eyebrow">SPINE 4.2 官方运行时 · 实测</div>
    <h1>Spine 动作幅度验证</h1>
    <p class="lede">左边是 Spine 官方 Web 播放器（spine-player 4.2.119）实时播放。骨骼由脚本自动生成：17 根骨骼，4 块带权重的网格（上半身、下半身、左右手臂），6 套服装通过链接网格共用同一套网格。16 个动作从小到大排列，点一下就能播放；右侧按三类衣服分别给出判定。</p>
  </header>

  <section id="lab">
    <div class="legend"><b>判定：</b><span class="pill v-安全">安全</span>直接可用 <span class="pill v-可用">可用</span>动画师微调后可用 <span class="pill v-勉强">勉强</span>能看出变形 <span class="pill v-不建议">不建议</span>变形明显 <span class="pill v-做不到">做不到</span>2D 正面无法表现</div>
    <div class="lab">
      <div class="bench">
        <div class="player-box"><div id="player"></div></div>
        <div class="chips" id="outfits"></div>
        <div class="speed"><span>速度</span><span class="chips" id="speeds"></span></div>
        <div class="now" id="now"></div>
      </div>
      <div class="ladder" id="ladder"></div>
    </div>
    <p class="note">说明：权重由脚本自动计算，没有经过动画师手工修形、没有变形关键帧，也没有物理约束，所以这里展示的是效果的<b>下限</b>。“可用”“勉强”两档经过专业修形能明显改善；“做不到”一档是 2D 单一正面视角的限制，Spine 本身解决不了。</p>
  </section>

  <section>
    <div class="sec-head">
      <div class="eyebrow">最大幅度截图</div>
      <h2>每个动作做到最大时的样子</h2>
      <p>同一组动作，分别用短袖、长袖加长裙、长外套三套衣服，截取幅度最大的那一帧。可以左右滑动。</p>
    </div>
    <p class="order">顺序：待机呼吸 · 歪头 · 侧弯 · 小幅抬手 · 举手打招呼 · 双臂外展 · 双臂平举 · 双手举过头 · 叉腰 · 手放身前 · 侧抬腿 · 踢腿 · 原地踏步 · 跳跃 · 鞠躬 · 转身</p>
    <p class="strip-cap"><b>短袖 + 牛仔裤</b></p>
    <div class="strip"><img src="img/peaks_short.jpg" alt="短袖搭配的 16 个动作最大幅度" width="2880" height="319"></div>
    <p class="strip-cap"><b>长袖毛衣 + 碎花长裙</b></p>
    <div class="strip"><img src="img/peaks_long.jpg" alt="长袖长裙搭配的 16 个动作最大幅度" width="2880" height="319"></div>
    <p class="strip-cap"><b>风衣 + 卫衣 + 工装裤</b></p>
    <div class="strip"><img src="img/peaks_coat.jpg" alt="长外套搭配的 16 个动作最大幅度" width="2880" height="319"></div>
  </section>

  <section id="seam">
    <div class="sec-head">
      <div class="eyebrow">肩膀切割问题</div>
      <h2>两种做法都不理想，问题出在素材本身</h2>
      <p>每组上排是 v1（在肩膀处把手臂切开，播放器里用的就是这一版），下排是 v2（上半身和手臂做成一整块网格连续变形）。动作依次是：叉腰、小幅抬手、双臂外展、双臂平举、举手打招呼、手放身前、双手举过头。可以左右滑动。</p>
    </div>
    <p class="strip-cap"><b>T 恤</b>：v1 肩膀有明显切口；v2 没有切口，但腋下和衣身两侧被拉出细纹</p>
    <div class="strip"><img src="img/cmp_tee.jpg" alt="T 恤两种做法对比" width="1540" height="440" style="height:300px"></div>
    <p class="strip-cap"><b>毛衣</b>：v2 袖子和衣身贴在一起的地方被扯成条纹</p>
    <div class="strip"><img src="img/cmp_sweater.jpg" alt="毛衣两种做法对比" width="1540" height="440" style="height:300px"></div>
    <p class="strip-cap"><b>风衣</b>：v1 衣身侧片被划进手臂、跟着手走；v2 衣身被大面积拉扯</p>
    <div class="strip"><img src="img/cmp_coat.jpg" alt="风衣两种做法对比" width="1540" height="440" style="height:300px"></div>
    <div class="cols">
      <div class="card">
        <h3>为什么怎么切都不对</h3>
        <ul>
          <li>衣服是在 A 字站姿上生成的，袖子和衣身贴得很近</li>
          <li>腋下、身体侧面被袖子挡住，在图里根本不存在</li>
          <li>手臂一抬，要么露出缺口（切开），要么被拉伸成条纹（连续变形）</li>
          <li>专业 Spine / Live2D 角色会由画师把被挡住的部分补画完整，再分层绑定</li>
        </ul>
      </div>
      <div class="card">
        <h3>建议：用 T 字姿势作为绑定姿势</h3>
        <ul>
          <li>在双臂平举的素模上生成衣服，袖子和衣身完全分开，腋下、侧面、肩线都完整可见</li>
          <li>沿袖子缝线分成“袖子”“衣身”两层，不会切到衣身</li>
          <li>平时的 A 字站姿由动画把手臂放下得到：放下是“遮挡”，不会露出缺口</li>
          <li>举手、平举离绑定姿势更近，变形更小</li>
          <li>配套：袖子顶部做圆弧袖山盖住肩膀；长外套衣身、下摆单独分层</li>
        </ul>
      </div>
    </div>
  </section>

  <section>
    <div class="sec-head">
      <div class="eyebrow">结论</div>
      <h2>Spine 能做到多大的幅度</h2>
    </div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>衣服类型</th><th>安全</th><th>可用</th><th>勉强</th><th>不建议</th><th>做不到</th></tr></thead>
      <tbody>__COUNTS__</tbody>
    </table></div>
    <div class="cols">
      <div class="card">
        <h3>放心做的</h3>
        <ul>
          <li>待机呼吸、歪头、身体小幅侧弯</li>
          <li>手臂在 45° 以内的动作：小幅抬手、叉腰</li>
          <li>整体位移：跳跃、上下弹动</li>
          <li>短袖、无袖衣服的大部分手臂动作</li>
        </ul>
      </div>
      <div class="card">
        <h3>需要动画师修形的</h3>
        <ul>
          <li>手肘弯曲超过 90°（举手打招呼、手放身前）：用变形关键帧修肘部</li>
          <li>手臂外展 45°–90°：长袖肩部、腋下要修</li>
          <li>侧弯、侧抬腿：长外套、长裙的接缝处要处理</li>
        </ul>
      </div>
      <div class="card">
        <h3>靠网格变形做不好的</h3>
        <ul>
          <li>手臂举过头、平举（尤其长袖）：改用真实关键姿势图</li>
          <li>抬腿、踢腿（尤其长裙、长外套）：裙摆要单独绑骨骼 + 物理，大幅度仍然不行</li>
          <li>原地踏步：正面只能“缩短”大腿，像下沉</li>
          <li>手臂抬起时肩膀、腋下出现缺口或切线：原图里被手臂挡住的衣身不存在，需要补画（见下表）</li>
        </ul>
      </div>
      <div class="card">
        <h3>Spine 做不到的</h3>
        <ul>
          <li>转身、鞠躬、走路前进：需要另一个视角的画面</li>
          <li>解决办法：视频生成，或做正面、侧面、背面多套素模</li>
        </ul>
      </div>
    </div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>问题</th><th>Spine 里的改进手段</th></tr></thead>
      <tbody>
        <tr><td>手肘、肩膀被挤压或拉伸</td><td>更平滑的权重；关键帧上用网格变形（Deform）手工修形</td></tr>
        <tr><td>长裙、风衣下摆被腿撕开</td><td>下摆做成独立插槽，挂自己的骨骼，用物理约束（Physics Constraint）跟随，不直接绑在腿上</td></tr>
        <tr><td>风衣侧片被手臂带走</td><td>外套衣身和袖子分开切图，衣身侧片留在躯干插槽</td></tr>
        <tr><td>上下半身接缝在弯腰时断开</td><td>躯干多加骨骼，长外套衣身单独一块网格、权重覆盖整段</td></tr>
        <tr><td>大角度姿势（举手、平举）</td><td>附件切换时间轴：终点换成该姿势的真实图片，网格只负责过渡</td></tr>
        <tr><td>抬手时腋下出现缺口、肩膀有切线（如毛衣平举、叉腰）</td><td>衣身补画被手臂挡住的腋下和侧面（可让 AI 在去掉手臂的素模上生成，或局部重绘）；袖子顶部做成圆弧袖山盖在肩上并留重叠；肩部顶点同时受手臂和躯干骨骼影响</td></tr>
        <tr><td>手臂挡在身前</td><td>手臂插槽在上层；需要时用绘制顺序（Draw Order）时间轴调整前后</td></tr>
      </tbody>
    </table></div>
    <p class="note">本页的人物和衣服都是 AI 生成的，人物不是真实存在的人。</p>
  </section>
</div>

<script src="https://cdn.jsdelivr.net/npm/@esotericsoftware/spine-player@4.2.119/dist/iife/spine-player.min.js"></script>
<script>
(function(){
  const M = __M__, OUT = __OUT__, COLS = ['短袖','长袖/长裙','长外套'], GROUPS = ['头与躯干','手臂','腿','全身'];
  let cur = 'idle', skin = 'default', speed = 1, player = null;
  try { const s = JSON.parse(localStorage.getItem('spine-lab')||'null'); if (s) { cur = s.cur || cur; skin = s.skin || skin; speed = s.speed || speed; } } catch(e) {}
  if (!M.find(m => m[0] === cur)) cur = 'idle'; if (!OUT.find(o => o[0] === skin)) skin = 'default';
  const col = () => OUT.find(o => o[0] === skin)[2];
  const pill = (v, dim) => `<span class="pill v-${v}${dim ? ' dim' : ''}">${v}</span>`;
  function renderLadder(){
    const c = col();
    document.getElementById('ladder').innerHTML = GROUPS.map(g => `<div><div class="grp-title"><b>${g}</b>${COLS.map((n,i) => `<span class="${i===c?'on':''}">${n}</span>`).join('')}</div>` +
      M.filter(m => m[2] === g).map(m => `<button class="mv" data-k="${m[0]}" aria-pressed="${m[0]===cur}"><span><b>${m[1]}</b><small>${m[3]}</small></span>${m[4].map((v,i) => pill(v, i !== c)).join('')}</button>`).join('') + `</div>`).join('');
    const m = M.find(x => x[0] === cur);
    document.getElementById('now').innerHTML = `<h3>${m[1]} <span class="amp">${m[3]}</span></h3>
      <dl><dt>当前衣服</dt><dd>${OUT.find(o => o[0] === skin)[1]}　${pill(m[4][c])}</dd><dt>问题</dt><dd>${m[5]}</dd><dt>改进</dt><dd>${m[6]}</dd></dl>`;
    document.querySelectorAll('#outfits .chip').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.s === skin)));
    document.querySelectorAll('#speeds .chip').forEach(b => b.setAttribute('aria-pressed', String(+b.dataset.v === speed)));
    try { localStorage.setItem('spine-lab', JSON.stringify({cur, skin, speed})); } catch(e) {}
  }
  document.getElementById('outfits').innerHTML = OUT.map(o => `<button class="chip" data-s="${o[0]}">${o[1]}</button>`).join('');
  document.getElementById('speeds').innerHTML = [[.5,'0.5×'],[1,'1×']].map(([v,n]) => `<button class="chip" data-v="${v}">${n}</button>`).join('');
  function apply(){
    if (!player || !player.skeleton) return;
    player.skeleton.setSkinByName(skin); player.skeleton.setSlotsToSetupPose(); player.skeleton.setToSetupPose();
    player.speed = speed; player.setAnimation(cur, true); player.play();
  }
  document.getElementById('ladder').addEventListener('click', e => { const b = e.target.closest('.mv'); if (!b) return; cur = b.dataset.k; renderLadder(); apply(); });
  document.getElementById('outfits').addEventListener('click', e => { const b = e.target.closest('.chip'); if (!b) return; skin = b.dataset.s; renderLadder(); apply(); });
  document.getElementById('speeds').addEventListener('click', e => { const b = e.target.closest('.chip'); if (!b) return; speed = +b.dataset.v; renderLadder(); apply(); });
  renderLadder();
  if (!window.spine) { document.getElementById('player').textContent = 'Spine 播放器加载失败，请检查网络后刷新。'; return; }
  new spine.SpinePlayer('player', {
    jsonUrl: 'skeleton.json', atlasUrl: 'skeleton.atlas', animation: cur, skin: skin,
    premultipliedAlpha: false, alpha: true, backgroundColor: '#00000000', showControls: false, showLoading: true,
    viewport: { x: -560, y: -40, width: 1120, height: 1760, padLeft: 0, padRight: 0, padTop: 0, padBottom: 0, transitionTime: 0 },
    success: p => { player = p; window.__player = p; apply(); },
    error: (p, msg) => { document.getElementById('player').textContent = 'Spine 加载失败：' + msg; }
  });
})();
</script>
"""
rows = ''.join(f"<tr><td>{n}</td>" + ''.join(f"<td>{counts[i].get(v,0)}</td>" for v in ['安全','可用','勉强','不建议','做不到']) + "</tr>" for i, n in enumerate(['短袖 + 裤子','长袖 / 长裙','长外套']))
page = page.replace('__CSS__', css).replace('__M__', json.dumps(M, ensure_ascii=False)).replace('__OUT__', json.dumps(OUT, ensure_ascii=False)).replace('__COUNTS__', rows)
open('index.html', 'w', encoding='utf-8').write(page); print('ok', len(page))
