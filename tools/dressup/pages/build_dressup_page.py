import json
man = json.load(open('app/assets/manifest.json', encoding='utf-8'))
style = open('parts_style.html', encoding='utf-8').read()
r1 = open('parts_r1.html', encoding='utf-8').read(); r2 = open('parts_r2.html', encoding='utf-8').read()
ex = json.dumps({'id':'shirt', **{k: man['items']['shirt'][k] for k in ('cat','z','box')},
                 'files': {'orig': 'shirt_orig.webp', 'dark': 'shirt_dark.webp', '…': '…'}}, ensure_ascii=False, indent=2)
app_css = """
<style>
.app{display:grid;grid-template-columns:minmax(0,400px) minmax(0,1fr);gap:28px;align-items:start}
.stage2{position:sticky;top:calc(env(safe-area-inset-top,0px) + 12px);display:flex;flex-direction:column;gap:10px;min-width:0}
.canvas{position:relative;width:100%;height:auto;flex:none;aspect-ratio:1024/1536;background:var(--stage);border-radius:12px;overflow:hidden}
.canvas img{position:absolute;display:block;max-width:none;user-select:none;-webkit-user-drag:none;pointer-events:none}
.canvas img.base{left:0;top:0;width:100%;height:100%}
.canvas .busy{position:absolute;right:10px;top:10px;font-size:12px;padding:3px 10px;border-radius:99px;background:var(--panel);color:var(--muted);border:1px solid var(--line)}
.stage-note{font-size:13px;color:var(--muted)}
.picker{display:grid;gap:22px;min-width:0}
.grp{display:grid;gap:10px}
.grp-head{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.grp-head b{font-size:15px}
.grp-head span{font-size:12.5px;color:var(--muted)}
.items{display:grid;grid-template-columns:repeat(auto-fill,minmax(86px,1fr));gap:8px}
.item{border:1px solid var(--line);border-radius:10px;background:var(--panel);padding:6px 6px 8px;display:grid;gap:5px;justify-items:center;cursor:pointer;font:inherit;font-size:12.5px;line-height:1.3;color:var(--fg);text-align:center}
.item img{width:100%;aspect-ratio:3/4;object-fit:contain;border-radius:6px;background:#EFEFEB}
.item.none{align-content:center;min-height:100%;color:var(--muted)}
.item:hover{border-color:var(--accent)}
.item[aria-pressed="true"]{border-color:var(--accent);box-shadow:0 0 0 1.5px var(--accent);color:var(--fg)}
.item:focus-visible,.tone:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.tones{display:flex;flex-wrap:wrap;gap:8px}
.tone{display:flex;align-items:center;gap:8px;font:inherit;font-size:14px;padding:6px 14px 6px 6px;border-radius:99px;border:1px solid var(--line);background:var(--panel);color:var(--fg);cursor:pointer}
.tone i{width:24px;height:24px;border-radius:50%;display:block;border:1px solid rgba(0,0,0,.12)}
.tone[aria-pressed="true"]{border-color:var(--accent);box-shadow:0 0 0 1.5px var(--accent)}
.worn{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;display:grid;gap:4px;font-size:14px}
.worn .row{display:grid;grid-template-columns:40px 1fr auto;gap:10px}
.worn .z{font-family:var(--f-mono);color:var(--accent);font-variant-numeric:tabular-nums}
.worn .k{color:var(--muted);font-size:12.5px}
.msg{font-size:13px;color:var(--warn);min-height:1.3em}
.canvas canvas{position:absolute;inset:0;width:100%;height:100%;display:block}
.slider{display:grid;gap:8px}
.slider input[type=range]{width:100%;height:28px;-webkit-appearance:none;appearance:none;background:transparent}
.slider input[type=range]::-webkit-slider-runnable-track{height:14px;border-radius:99px;background:linear-gradient(90deg,#f6ede4,#f3e7db,#f7ead0,#eadaba,#d7bd96,#a07e56,#825c43,#604134,#3a312a,#292420)}
.slider input[type=range]::-moz-range-track{height:14px;border-radius:99px;background:linear-gradient(90deg,#f6ede4,#f3e7db,#f7ead0,#eadaba,#d7bd96,#a07e56,#825c43,#604134,#3a312a,#292420)}
.slider input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:26px;height:26px;margin-top:-6px;border-radius:50%;background:var(--panel);border:3px solid var(--accent)}
.slider input[type=range]::-moz-range-thumb{width:20px;height:20px;border-radius:50%;background:var(--panel);border:3px solid var(--accent)}
.sw-row{display:flex;flex-wrap:wrap;gap:6px}
.sw2{width:28px;height:28px;border-radius:50%;border:2px solid var(--line);cursor:pointer;padding:0}
.sw2:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.toggles{display:flex;flex-wrap:wrap;gap:16px;font-size:14px}
.toggles label{display:flex;gap:6px;align-items:center;cursor:pointer}
.anim{display:flex;gap:14px;align-items:center;font-size:14px}
.anim label{display:flex;gap:6px;align-items:center;cursor:pointer}
.btn{font:inherit;font-size:15px;font-weight:700;padding:8px 22px;border-radius:99px;border:none;background:var(--accent);color:var(--bg);cursor:pointer}
.btn:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.perf{font-family:var(--f-mono);font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums}
.how{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;font-size:13.5px;display:grid;gap:6px}
.how ol{margin:0;padding-left:20px;display:grid;gap:4px}
@media (max-width:760px){.app{grid-template-columns:1fr}.stage2{position:static;max-width:420px;width:100%;justify-self:center}}
</style>"""
MANJSON = json.dumps(man, ensure_ascii=False)
body = f"""<title>素模换装方案</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@600;700&family=Noto+Sans+SC:wght@400;500;700&family=JetBrains+Mono:wght@400;600&display=swap">
{style}
{app_css}

<div class="wrap">
  <header>
    <div class="eyebrow">C 端换装 · 真实图片原型</div>
    <h1>素模换装：用 AI 真实图片叠图换装</h1>
    <p class="lede">换装台用的是 gpt-image-2 生成、再由流程自动抠出来的真实图层：1 个素模、20 件衣服。肤色用“做法 2”实现：衣服和皮肤先合成一张颜色图，同时合成一张皮肤蒙版，再由 WebGL shader 实时改色，拖动滑杆就能连续调肤色。</p>
  </header>

  <section id="try">
    <div class="sec-head">
      <div class="eyebrow">换装台</div>
      <h2>拖动肤色，点衣服，点“挥手”</h2>
      <p>同一类只能穿一件；连衣裙、连体裤、泳衣算“全身”，换上时自动取下上衣和下装。外套可以叠穿在上衣外面。再点一次已选中的衣服可以脱下。</p>
    </div>
    <div class="app">
      <div class="stage2">
        <div class="canvas" id="canvas" role="img" aria-label="换装预览"><canvas id="gl" width="1024" height="1536"></canvas><span class="busy" id="busy" hidden>加载中…</span></div>
        <div class="anim"><button class="btn" id="wave">挥手</button><label><input type="checkbox" id="loop"> 循环播放</label></div>
        <p class="perf" id="perf"></p>
        <p class="stage-note" id="poseNote"></p>
        <p class="stage-note">已知问题：叠穿敞开的外套时，外套边缘可能残留少量灰色（见下方测试报告）。</p>
      </div>
      <div class="picker" id="picker"></div>
    </div>
  </section>

  <section id="spec">
    <div class="sec-head">
      <div class="eyebrow">素材规格</div>
      <h2>衣服图片的格式和尺寸</h2>
      <p>所有衣服图层必须和素模在同一个坐标系里，这是能直接叠放的前提。</p>
    </div>
    <div class="cols">
      <div class="card">
        <h3>ChatGPT 能直接出透明 PNG 吗？</h3>
        <p><b>不能直接用。</b>实测 gpt-image-2 不支持透明背景，接口返回“Transparent background is not supported for this model”。旧的 gpt-image-1 支持透明背景，但单独生成的一件衣服，姿态、大小、位置都和素模对不上。</p>
        <p>所以流程是：先在素模身上“穿上”衣服生成整张图，再由流程自动抠出衣服，生成带透明通道的图片。下面换装台里的 80 张衣服图层都是这样得到的。</p>
      </div>
      <div class="card">
        <h3>尺寸规则</h3>
        <ul>
          <li><b>统一画布</b>：所有图层和素模同一画布。本次测试是 1024 × 1536；正式版建议 2048 × 3072，再按手机屏幕导出 @2x、@3x 两档</li>
          <li><b>只存有内容的部分</b>：每件衣服裁到不透明区域的外框，同时记录它在画布上的位置（x, y, 宽, 高）。比如短靴只有 305 × 177，约 7.6 KB</li>
          <li><b>格式</b>：WebP（带透明通道），体积约为 PNG 的 1/5 到 1/10；不支持 WebP 的环境退回 PNG</li>
          <li><b>本次总量</b>：20 件 × 4 种肤色 + 4 张素模底图，共 105 张图，2.9 MB</li>
        </ul>
      </div>
      <div class="card">
        <h3>每件衣服的说明文件</h3>
        <p>客户端读这份说明，就知道每张图放哪、叠第几层：</p>
<pre class="code"><code>{ex}</code></pre>
      </div>
      <div class="card">
        <h3>肤色怎么处理</h3>
        <p>换装台用的就是这个做法：每件衣服只存一张图层 + 一张“皮肤通道”（灰度表示哪里是皮肤），素模另有一张皮肤蒙版。换衣服时把颜色图和皮肤蒙版各合成一次；拖动肤色时只改 shader 的一个参数，不需要重新合成。素材量是每种肤色各存一套的四分之一，而且支持任意肤色。</p>
      </div>
    </div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>类目</th><th>层级</th><th>占用部位</th><th>换上时自动取下</th></tr></thead>
      <tbody>
        <tr><td>外套</td><td class="z">50</td><td>上身外层</td><td>无，可以叠穿在上衣外面</td></tr>
        <tr><td>上衣</td><td class="z">40</td><td>上身</td><td>全身类</td></tr>
        <tr><td>下装</td><td class="z">30</td><td>下身</td><td>全身类</td></tr>
        <tr><td>全身（连衣裙、连体裤、泳衣）</td><td class="z">30</td><td>上身 + 下身</td><td>上衣、下装</td></tr>
        <tr><td>鞋</td><td class="z">20</td><td>脚</td><td>只替换鞋；排在裤子下面，裤脚盖住鞋口</td></tr>
        <tr><td>素模底图</td><td class="z">0</td><td>—</td><td>永远在最底层</td></tr>
      </tbody>
    </table></div>
  </section>

  {r2}

  {r1}

  <p class="foot">图片均由 AI 生成，人物不是真实存在的人。</p>
</div>

<script>
(function(){{
  const MAN = {MANJSON};
  const [CW, CH] = MAN.canvas;
  const MONK = ['#f6ede4','#f3e7db','#f7ead0','#eadaba','#d7bd96','#a07e56','#825c43','#604134','#3a312a','#292420'];
  const GROUPS = [['top','上衣','上身'],['outer','外套','上身外层，可叠穿'],['bottom','下装','下身'],['full','全身','连衣裙、连体裤、泳衣'],['shoes','鞋','']];
  const DEFAULT = {{tone: 600, recolor: true, showMask: false, top:'tee', outer:null, bottom:'jeans', full:null, shoes:'sneakers'}};
  let state = Object.assign({{}}, DEFAULT), msg = '';
  try {{ const s = JSON.parse(localStorage.getItem('dressup-m2')||'null'); if (s) Object.assign(state, s); }} catch(e) {{}}
  for (const [cat] of GROUPS) if (state[cat] && !MAN.items[state[cat]]) state[cat] = null;

  // ---------- colour helpers (same formulas as the shader) ----------
  const hex = h => [1,3,5].map(i => parseInt(h.slice(i,i+2),16));
  function toneRGB(v){{ const t = v/100, i = Math.min(8, Math.floor(t)), f = t - i, a = hex(MONK[i]), b = hex(MONK[i+1]); return a.map((x,k) => Math.round(x + (b[k]-x)*f)); }}
  function rgb2lab([r,g,b]){{
    const lin = c => (c/=255) > .04045 ? Math.pow((c+.055)/1.055, 2.4) : c/12.92;
    const R = lin(r), G = lin(g), B = lin(b);
    const x = (.4124564*R + .3575761*G + .1804375*B)/.95047, y = .2126729*R + .7151522*G + .0721750*B, z = (.0193339*R + .1191920*G + .9503041*B)/1.08883;
    const f = t => t > .008856 ? Math.cbrt(t) : 7.787*t + 16/116;
    return [116*f(y)-16, 500*(f(x)-f(y)), 200*(f(y)-f(z))];
  }}

  // ---------- WebGL ----------
  const glc = document.getElementById('gl'), gl = glc.getContext('webgl', {{alpha:false, preserveDrawingBuffer:true}});
  const perf = document.getElementById('perf'), busy = document.getElementById('busy');
  if (!gl) {{ perf.textContent = '这个浏览器不支持 WebGL，无法演示实时改色。'; return; }}
  // one program, three passes: background plate, body (arm cut out), arm mesh deformed by a 2-bone rig.
  // Every pass samples the SAME composite colour + skin mask, so clothes and skin can never separate.
  const VS = `attribute vec2 aPos, aUV; varying vec2 v; uniform vec2 uSize;
    void main(){{ v = aUV; gl_Position = vec4(aPos.x/uSize.x*2.-1., 1.-aPos.y/uSize.y*2., 0., 1.); }}`;
  const FS = `precision highp float;
    varying vec2 v; uniform sampler2D uC, uM, uO, uA, uP; uniform vec3 uT, uMu; uniform float uOn, uShow, uMode, uFade; uniform vec2 uPx;
    vec3 toLin(vec3 c){{ return mix(c/12.92, pow((c+.055)/1.055, vec3(2.4)), step(.04045, c)); }}
    vec3 toSRGB(vec3 c){{ return mix(c*12.92, 1.055*pow(max(c,0.), vec3(1./2.4))-.055, step(.0031308, c)); }}
    const mat3 M  = mat3(.4124564,.2126729,.0193339, .3575761,.7151522,.1191920, .1804375,.0721750,.9503041);
    const mat3 Mi = mat3(3.2404542,-.9692660,.0556434, -1.5371385,1.8760108,-.2040259, -.4985314,.0415560,1.0572252);
    const vec3 WP = vec3(.95047, 1., 1.08883);
    vec3 f(vec3 t){{ return mix(7.787*t + 16./116., pow(max(t,0.), vec3(1./3.)), step(.008856, t)); }}
    vec3 finv(vec3 F){{ vec3 F3 = F*F*F; return mix((F - 16./116.)/7.787, F3, step(.008856, F3)); }}
    vec3 rgb2lab(vec3 c){{ vec3 F = f(M*toLin(c)/WP); return vec3(116.*F.y-16., 500.*(F.x-F.y), 200.*(F.y-F.z)); }}
    vec3 lab2rgb(vec3 L){{ float fy = (L.x+16.)/116.; vec3 xyz = finv(vec3(fy+L.y/500., fy, fy-L.z/200.))*WP; return toSRGB(clamp(Mi*xyz, 0., 1.)); }}
    void main(){{
      if (uMode < .5) {{ gl_FragColor = vec4(texture2D(uP, v).rgb, 1.); return; }}
      vec3 c = texture2D(uC, v).rgb; float m = texture2D(uM, v).r;
      vec3 lab = rgb2lab(c); float r = uT.x/uMu.x;
      float kp = clamp(.3+.7*r, .4, 1.), kn = clamp(.5+.5*r, .6, 1.), d = lab.x - uMu.x;
      vec3 o = vec3(uT.x + (d > 0. ? kp*d : kn*d), uT.y + .6*(lab.y-uMu.y), uT.z + .6*(lab.z-uMu.z));
      vec3 col = mix(c, lab2rgb(o), m*uOn);
      col = mix(col, vec3(.93,.16,.36), .6*m*uShow);
      float side = texture2D(uA, v).r, occ = texture2D(uO, v).r;
      // body pass removes the arm generously (soft edges included) so no ghost outline stays behind;
      // the plate underneath is plain background. The moving arm keeps its own soft edge for anti-aliasing.
      float occD = occ;                                   // occupancy dilated ~6 px: the mask is a little tighter than the real edge
      for (int k = 0; k < 8; k++) {{ float a = float(k)*.785398; vec2 o = vec2(cos(a), sin(a))*uPx;
        occD = max(occD, max(texture2D(uO, v + 3.*o).r, texture2D(uO, v + 6.*o).r)); }}
      float cut = side * smoothstep(.02, .3, occD);
      gl_FragColor = vec4(col, (uMode < 1.5 ? 1. - cut : side * occ) * uFade);
    }}`;
  function sh(type, src){{ const o = gl.createShader(type); gl.shaderSource(o, src); gl.compileShader(o); if (!gl.getShaderParameter(o, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(o)); return o; }}
  const prog = gl.createProgram(); gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(prog); gl.useProgram(prog);
  const U = n => gl.getUniformLocation(prog, n), aPos = gl.getAttribLocation(prog, 'aPos'), aUV = gl.getAttribLocation(prog, 'aUV');
  gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  gl.uniform2f(U('uSize'), CW, CH); gl.uniform2f(U('uPx'), 1/CW, 1/CH);
  function tex(unit){{ const t = gl.createTexture(); gl.activeTexture(gl.TEXTURE0+unit); gl.bindTexture(gl.TEXTURE_2D, t);
    for (const [k,v] of [[gl.TEXTURE_MIN_FILTER, gl.LINEAR],[gl.TEXTURE_MAG_FILTER, gl.LINEAR],[gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE],[gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, v);
    return t; }}
  const texP = tex(4);
  ['uC','uM','uO','uA','uP'].forEach((n,i) => gl.uniform1i(U(n), i)); gl.uniform3fv(U('uMu'), MAN.skin.mu_lab);
  const upload = (t, unit, src) => {{ gl.activeTexture(gl.TEXTURE0+unit); gl.bindTexture(gl.TEXTURE_2D, t); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, src); }};

  // full-canvas quad
  const quad = new Float32Array([0,0, 0,0,  CW,0, 1,0,  0,CH, 0,1,  CW,CH, 1,1]);
  const quadBuf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, quadBuf); gl.bufferData(gl.ARRAY_BUFFER, quad, gl.STATIC_DRAW);
  const ss = (e0, e1, x) => {{ const t = Math.min(1, Math.max(0, (x-e0)/(e1-e0))); return t*t*(3-2*t); }};
  function segDist(p, a, b){{ const ab = [b[0]-a[0], b[1]-a[1]], t = Math.max(0, Math.min(1, ((p[0]-a[0])*ab[0] + (p[1]-a[1])*ab[1])/(ab[0]*ab[0]+ab[1]*ab[1]))); return Math.hypot(p[0]-a[0]-t*ab[0], p[1]-a[1]-t*ab[1]); }}
  function rot(p, c, a){{ const s = Math.sin(a), k = Math.cos(a), x = p[0]-c[0], y = p[1]-c[1]; return [c[0] + x*k - y*s, c[1] + x*s + y*k]; }}
  const ang = (a, b) => Math.atan2(b[1]-a[1], b[0]-a[0]);
  const wrap = x => Math.atan2(Math.sin(x), Math.cos(x));

  // a "scene" = one pose: its composite textures + an arm mesh with bone weights
  function makeScene(rig, blendShoulder){{
    const J0 = rig.shoulder, J1 = rig.elbow, TIPX = [rig.tip[0] + (rig.tip[0]-rig.wrist[0])*.4, rig.tip[1] + (rig.tip[1]-rig.wrist[1])*.4];
    const d1 = [J1[0]-J0[0], J1[1]-J0[1]], L1 = Math.hypot(...d1); d1[0] /= L1; d1[1] /= L1;
    const [bx, by, bw, bh] = rig.box, NX = 28, NY = 52, verts = [], wts = [], idx = [];
    for (let j = 0; j <= NY; j++) for (let i = 0; i <= NX; i++) {{
      const p = [bx + bw*i/NX, by + bh*j/NY], along = (p[0]-J0[0])*d1[0] + (p[1]-J0[1])*d1[1];
      const wf = ss(-22, 22, segDist(p, J0, J1) - segDist(p, J1, TIPX));      // forearm share: closer to forearm than upper arm
      verts.push(...p); wts.push(blendShoulder ? ss(-45, 25, along) : 1, wf);
    }}
    for (let j = 0; j < NY; j++) for (let i = 0; i < NX; i++) {{ const q = j*(NX+1)+i; idx.push(q, q+1, q+NX+1, q+1, q+NX+2, q+NX+1); }}
    const sc = {{ J0, J1, verts, wts, n: idx.length, data: new Float32Array(verts.length*2), vbuf: gl.createBuffer(), ibuf: gl.createBuffer(),
                 tex: [tex(0), tex(1), tex(2), tex(3)], ready: false }};
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, sc.ibuf); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(idx), gl.STATIC_DRAW);
    return sc;
  }}
  function buildMesh(sc, au, af){{
    const {{J0, J1, verts, wts, data}} = sc;
    for (let n = 0; n < verts.length/2; n++) {{
      const p = [verts[2*n], verts[2*n+1]], wa = wts[2*n], wf = wts[2*n+1];
      const up = rot(p, J0, au), fo = rot(rot(p, J1, af), J0, au);
      const q = [up[0] + (fo[0]-up[0])*wf, up[1] + (fo[1]-up[1])*wf];
      data[4*n] = p[0] + (q[0]-p[0])*wa; data[4*n+1] = p[1] + (q[1]-p[1])*wa; data[4*n+2] = p[0]/CW; data[4*n+3] = p[1]/CH;
    }}
    gl.bindBuffer(gl.ARRAY_BUFFER, sc.vbuf); gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW);
  }}
  function bindAttrs(buf){{ gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.enableVertexAttribArray(aPos); gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 16, 0); gl.enableVertexAttribArray(aUV); gl.vertexAttribPointer(aUV, 2, gl.FLOAT, false, 16, 8); }}
  const R = MAN.rig, RB = MAN.raise;
  const SA = makeScene(R, true), SB = makeScene(RB, false);
  // mesh angles that bring the standing arm close to the real waving pose
  const AU = wrap(ang(RB.shoulder, RB.elbow) - ang(R.shoulder, R.elbow));
  const AF = wrap(ang(RB.elbow, RB.wrist) - (ang(R.elbow, R.wrist) + AU));

  // ---------- image cache + compositing (runs only when the outfit changes) ----------
  const cache = {{}};
  const load = src => cache[src] || (cache[src] = new Promise((ok, no) => {{ const im = new Image(); im.onload = () => ok(im); im.onerror = no; im.src = src; }}));
  const mk = () => {{ const c = document.createElement('canvas'); c.width = CW; c.height = CH; return c; }};
  const cc = mk(), mc = mk(), oc = mk(), tmp = mk(); const cx = cc.getContext('2d'), mx = mc.getContext('2d'), ox = oc.getContext('2d'), tx = tmp.getContext('2d');
  let composeMs = 0, seq = 0, ready = false, hasB = false;
  const plateReady = load(R.plate).then(img => upload(texP, 4, img));
  async function composeScene(sc, base, skin, person, region, layers){{
    const imgs = await Promise.all([load(base), load(skin), load(person), load(region), ...layers.flatMap(l => [load(l.file), load(l.mask)])]);
    return () => {{
      const [bI, sI, pI, rI] = imgs;
      cx.clearRect(0,0,CW,CH); cx.drawImage(bI, 0, 0, CW, CH);
      mx.fillStyle = '#000'; mx.fillRect(0,0,CW,CH); mx.drawImage(sI, 0, 0, CW, CH);
      ox.fillStyle = '#000'; ox.fillRect(0,0,CW,CH); ox.drawImage(pI, 0, 0, CW, CH);
      layers.forEach((l, i) => {{
        const [x,y,w,h] = l.box, ci = imgs[4+2*i], mi = imgs[5+2*i];
        cx.drawImage(ci, x, y, w, h); mx.drawImage(mi, x, y, w, h);
        tx.globalCompositeOperation = 'copy'; tx.drawImage(mi, x, y, w, h);
        tx.globalCompositeOperation = 'source-in'; tx.fillStyle = '#fff'; tx.fillRect(0,0,CW,CH);
        ox.drawImage(tmp, 0, 0); tx.clearRect(0,0,CW,CH);
      }});
      upload(sc.tex[0], 0, cc); upload(sc.tex[1], 1, mc); upload(sc.tex[2], 2, oc); upload(sc.tex[3], 3, rI); sc.ready = true;
    }};
  }}
  async function compose(){{
    const my = ++seq; busy.hidden = false;
    const worn = GROUPS.map(([c]) => state[c]).filter(Boolean).map(k => MAN.items[k]).sort((a,b) => a.z - b.z);
    const layA = worn.map(it => ({{file: it.files.orig, mask: it.mask, box: it.box}}));
    // waving pose exists when every upper-body item has a real waving image; trousers and shoes are reused as-is
    hasB = worn.every(it => it.raise || it.cat === 'bottom' || it.cat === 'shoes');
    const layB = hasB ? worn.map(it => it.raise ? {{file: it.raise.file, mask: it.raise.mask, box: it.raise.box}} : {{file: it.files.orig, mask: it.mask, box: it.box}}) : [];
    const doA = await composeScene(SA, MAN.tones.orig, MAN.skin.mask, R.person, R.arm, layA);
    const doB = hasB ? await composeScene(SB, RB.base, RB.skin, RB.person, RB.arm, layB) : null;
    await plateReady;
    if (my !== seq) return;
    const t0 = performance.now(); doA(); if (doB) doB(); composeMs = performance.now() - t0;
    busy.hidden = true; ready = true;
    document.getElementById('poseNote').textContent = hasB ? '这套搭配有真实的挥手姿势图：抬手后会切换到真实图片。' : '这套搭配里有衣服还没有挥手姿势图，只用网格变形（刚性跟随）。目前有挥手图的：白T恤、黄色碎花裙、黑色皮夹克、驼色风衣、米白麻花毛衣。';
    draw();
  }}
  // ---------- per frame ----------
  let drawMs = 0, frame = {{a: [0,0], b: 0, fade: 0}};
  function drawScene(sc, au, af, fade){{
    sc.tex.forEach((t, i) => {{ gl.activeTexture(gl.TEXTURE0+i); gl.bindTexture(gl.TEXTURE_2D, t); }});
    gl.uniform1f(U('uFade'), fade);
    bindAttrs(quadBuf); gl.uniform1f(U('uMode'), 1); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    buildMesh(sc, au, af); bindAttrs(sc.vbuf); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, sc.ibuf);
    gl.uniform1f(U('uMode'), 2); gl.drawElements(gl.TRIANGLES, sc.n, gl.UNSIGNED_SHORT, 0);
  }}
  function draw(){{
    if (!ready) return;
    const t0 = performance.now();
    gl.viewport(0, 0, glc.width, glc.height);
    gl.uniform3fv(U('uT'), rgb2lab(toneRGB(state.tone)));
    gl.uniform1f(U('uOn'), state.recolor ? 1 : 0); gl.uniform1f(U('uShow'), state.showMask ? 1 : 0);
    gl.activeTexture(gl.TEXTURE4); gl.bindTexture(gl.TEXTURE_2D, texP);
    bindAttrs(quadBuf); gl.uniform1f(U('uFade'), 1); gl.uniform1f(U('uMode'), 0); gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    if (frame.fade < 1) drawScene(SA, frame.a[0], frame.a[1], 1);
    if (frame.fade > 0 && SB.ready && hasB) drawScene(SB, 0, frame.b, frame.fade);
    drawMs = performance.now() - t0;
    perf.textContent = `换衣服时合成：${{composeMs.toFixed(1)}} ms　|　每帧重绘：${{drawMs.toFixed(1)}} ms`;
  }}
  // ---------- wave timeline ----------
  const DEG = Math.PI/180, SWING = 16*DEG;
  const ease = t => t < .5 ? 2*t*t : 1 - Math.pow(-2*t + 2, 2)/2;
  const RIGID = [92*DEG, 52*DEG];                         // fallback pose when there is no real waving image
  function frameAt(t){{
    const tgt = hasB ? [AU, AF] : RIGID, swing = Math.sin((t-.75)/2.15*3*2*Math.PI)*SWING;
    if (t < .75) {{ const e = ease(Math.min(1, t/.7)); return {{a: [tgt[0]*e, tgt[1]*e], b: 0, fade: hasB ? ease(Math.max(0, (t-.5)/.25)) : 0}}; }}
    if (t < 2.9) return hasB ? {{a: tgt, b: swing, fade: 1}} : {{a: [tgt[0], tgt[1] + swing], b: 0, fade: 0}};
    if (t < 3.6) {{ const e = 1 - ease((t-2.9)/.7); return {{a: [tgt[0]*e, tgt[1]*e], b: 0, fade: hasB ? 1 - ease(Math.min(1, (t-2.9)/.25)) : 0}}; }}
    return {{a: [0,0], b: 0, fade: 0}};
  }}
  let animStart = null;
  function tick(now){{
    if (animStart === null) return;
    const t = (now - animStart)/1000; frame = frameAt(t); draw();
    if (t < 3.6) requestAnimationFrame(tick);
    else if (document.getElementById('loop').checked) {{ animStart = now + 500; requestAnimationFrame(tick); }}
    else {{ animStart = null; frame = frameAt(99); draw(); }}
  }}
  document.getElementById('wave').addEventListener('click', () => {{ const go = animStart === null; animStart = performance.now(); if (go) requestAnimationFrame(tick); }});
  window.__setT = t => {{ frame = frameAt(t); draw(); }};   // used by automated screenshots

  function equip(cat, key){{
    msg = '';
    if (state[cat] === key) {{ state[cat] = null; return; }}
    state[cat] = key; const off = [];
    if (key && cat === 'full') for (const c of ['top','bottom']) if (state[c]) {{ off.push(MAN.items[state[c]].name); state[c] = null; }}
    if (key && (cat === 'top' || cat === 'bottom') && state.full) {{ off.push(MAN.items[state.full].name); state.full = null; }}
    if (off.length) msg = '换上' + MAN.items[key].name + '，已自动取下：' + off.join('、') + '。';
  }}
  function sync(){{
    document.querySelectorAll('[data-k]').forEach(b => b.setAttribute('aria-pressed', String(state[b.dataset.cat] === (b.dataset.k || null))));
    document.getElementById('toneVal').textContent = 'Monk ' + (state.tone/100 + 1).toFixed(1) + ' · rgb(' + toneRGB(state.tone).join(', ') + ')';
    document.getElementById('tone').value = state.tone;
    document.getElementById('recolor').checked = state.recolor; document.getElementById('showMask').checked = state.showMask;
    const worn = GROUPS.map(([c]) => state[c]).filter(Boolean).map(k => MAN.items[k]).sort((a,b) => b.z - a.z);
    document.getElementById('wornList').innerHTML = worn.map(it => `<div class="row"><span class="z">${{it.z}}</span><span>${{it.name}}</span><span class="k">${{GROUPS.find(g=>g[0]===it.cat)[1]}}</span></div>`).join('') +
      `<div class="row"><span class="z">0</span><span>素模</span><span class="k">底图</span></div>`;
    document.getElementById('msg').textContent = msg;
    try {{ localStorage.setItem('dressup-m2', JSON.stringify(state)); }} catch(e) {{}}
  }}

  let html = `<div class="grp"><div class="grp-head"><b>肤色</b><span id="toneVal"></span></div>
    <div class="slider"><input type="range" id="tone" min="0" max="900" step="1" aria-label="肤色"></div>
    <div class="sw-row">` + MONK.map((c,i) => `<button class="sw2" data-sw="${{i*100}}" style="background:${{c}}" aria-label="Monk ${{i+1}}"></button>`).join('') + `</div>
    <div class="toggles"><label><input type="checkbox" id="recolor"> 开启改色</label><label><input type="checkbox" id="showMask"> 显示皮肤蒙版</label></div></div>`;
  for (const [cat, label, hint] of GROUPS){{
    const keys = Object.keys(MAN.items).filter(k => MAN.items[k].cat === cat);
    html += `<div class="grp"><div class="grp-head"><b>${{label}}</b><span>${{hint}}</span></div><div class="items">` +
      `<button class="item none" data-cat="${{cat}}" data-k="">不穿</button>` +
      keys.map(k => `<button class="item" data-cat="${{cat}}" data-k="${{k}}"><img src="${{MAN.items[k].thumb}}" alt="" loading="lazy">${{MAN.items[k].name}}</button>`).join('') + `</div></div>`;
  }}
  html += `<p class="msg" id="msg" aria-live="polite"></p>
    <div class="how"><b>做法 2 是怎么工作的</b><ol>
      <li>换衣服时：把素模和衣服叠成一张<b>颜色图</b>，同时把素模的皮肤蒙版和每件衣服的皮肤通道叠成一张<b>皮肤蒙版</b>（被衣服盖住的皮肤自动去掉）</li>
      <li>两张图作为贴图交给 GPU</li>
      <li>拖动肤色时：只改 shader 的目标肤色参数，蒙版里是皮肤的像素实时改色，其他像素不动</li>
      <li>做动画时：颜色图、皮肤蒙版、占位蒙版用同一套骨骼网格变形，衣袖和手臂一起动，换肤色照样实时生效</li></ol></div>
    <div class="worn"><b>当前图层（从上到下）</b><div id="wornList"></div></div>`;
  const picker = document.getElementById('picker'); picker.innerHTML = html;
  picker.addEventListener('click', e => {{
    const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.sw !== undefined) {{ state.tone = +b.dataset.sw; sync(); draw(); return; }}
    if (b.dataset.cat) {{ equip(b.dataset.cat, b.dataset.k || null); sync(); compose(); }}
  }});
  document.getElementById('tone').addEventListener('input', e => {{ state.tone = +e.target.value; sync(); draw(); }});
  document.getElementById('recolor').addEventListener('change', e => {{ state.recolor = e.target.checked; sync(); draw(); }});
  document.getElementById('showMask').addEventListener('change', e => {{ state.showMask = e.target.checked; sync(); draw(); }});
  sync(); compose().catch(err => {{ perf.textContent = '图片加载失败：' + err; }});
}})();
</script>
"""
body = body.replace('{MANJSON}', json.dumps(man, ensure_ascii=False))
open('dressup/index.html', 'w', encoding='utf-8').write(body)
print('written', len(body))
