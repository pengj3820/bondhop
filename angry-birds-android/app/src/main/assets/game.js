// Angry Birds — a slingshot physics game on planck.js (Box2D).
// Port of the Unity version in ../../../../../angry-birds: same levels, tuning and rules.
'use strict';

const pl = planck;
const V = (x, y) => pl.Vec2(x, y);

// ---- constants ------------------------------------------------------------

const VIEW_LEFT = -11.5, VIEW_RIGHT = 13.5, GROUND_SHOWN = 1.4;
const SLING = { x: -8, y: 0 };
const REST = { x: -8, y: 2.35 };
const BACK_TIP = { x: -8.31, y: 2.42 }, FRONT_TIP = { x: -7.69, y: 2.42 };
const MAX_DRAG = 1.6, MAX_SPEED = 15, BIRD_R = 0.32;
const GRAVITY = -9.81;
const LEVEL_COUNT = 5;
const STEP = 1 / 60;

const MAT = {
  wood:  { fill: '#d18f47', edge: '#8c5421', density: 0.7, health: 7,  score: 500, debris: '#bf8040' },
  glass: { fill: 'rgba(173,224,255,0.75)', edge: 'rgba(217,247,255,0.95)', density: 0.8, health: 2.5, score: 300, debris: '#bfebff' },
  stone: { fill: '#8c8f99', edge: '#5c5e69', density: 2.4, health: 22, score: 800, debris: '#80808c' },
};

// ---- canvas & camera --------------------------------------------------------

const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
let W = 0, H = 0, dpr = 1, camX = 0, camY = 0, ppu = 1, uiScale = 1;

function resize() {
  dpr = window.devicePixelRatio || 1;
  W = window.innerWidth; H = window.innerHeight;
  canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
  const halfW = (VIEW_RIGHT - VIEW_LEFT) / 2;
  const size = Math.max(halfW / (W / Math.max(H, 1)), 5.5);
  camX = (VIEW_LEFT + VIEW_RIGHT) / 2;
  camY = size - GROUND_SHOWN;
  ppu = H / (2 * size);
  uiScale = H / 720;
}
window.addEventListener('resize', resize);
resize();

const sx = x => W / 2 + (x - camX) * ppu;
const sy = y => H / 2 - (y - camY) * ppu;
const toWorld = (px, py) => ({ x: camX + (px - W / 2) / ppu, y: camY - (py - H / 2) / ppu });

// ---- storage ----------------------------------------------------------------

function load(key, def) { try { const v = localStorage.getItem(key); return v == null ? def : v; } catch (e) { return def; } }
function save(key, v) { try { localStorage.setItem(key, String(v)); } catch (e) { /* storage unavailable */ } }

// ---- sound ------------------------------------------------------------------

let audio = null;
const buffers = {};
function initAudio() {
  if (audio) { if (audio.state === 'suspended') audio.resume(); return; }
  try { audio = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { audio = null; }
}
function makeSound(name) {
  const rate = 22050;
  let len, wave;
  const rnd = () => Math.random() * 2 - 1;
  switch (name) {
    case 'launch': len = 0.35; wave = t => rnd() * (1 - t / len) * 0.5 * Math.sin(t * 30); break;
    case 'stretch': len = 0.15; wave = t => Math.sin(2 * Math.PI * (300 + 600 * t) * t) * (1 - t / len) * 0.3; break;
    case 'pig': len = 0.3; wave = t => Math.sin(2 * Math.PI * (520 - 900 * t) * t) * (1 - t / len) * 0.5; break;
    case 'win': len = 0.9; wave = t => Math.sin(2 * Math.PI * (t < 0.3 ? 523 : t < 0.6 ? 659 : 784) * t) * 0.35 * (1 - t / len); break;
    case 'lose': len = 0.9; wave = t => Math.sin(2 * Math.PI * (330 - 150 * t) * t) * 0.35 * (1 - t / len); break;
    default: len = 0.12; wave = t => rnd() * Math.exp(-t * 35) * 0.6; break;
  }
  const n = Math.floor(rate * len);
  const buf = audio.createBuffer(1, n, rate);
  const data = buf.getChannelData(0);
  for (let i = 0; i < n; i++) data[i] = wave(i / rate);
  return buf;
}
function playSound(name, volume = 1) {
  if (!audio || audio.state !== 'running') return;
  const buf = buffers[name] || (buffers[name] = makeSound(name));
  const src = audio.createBufferSource();
  const gain = audio.createGain();
  gain.gain.value = volume;
  src.buffer = buf;
  src.connect(gain).connect(audio.destination);
  src.start();
}

// ---- game state -------------------------------------------------------------

let world = null;
let objects = [];          // blocks and pigs
let pigs = [];
let queue = [];            // birds waiting on the ground
let current = null;        // bird on the sling or in flight
let state = 'menu';        // menu | aiming | flying | won | lost
let level = 0, score = 0, levelStartScore = 0;
let best = +load('best', 0) || 0;
let time = 0, levelStartTime = 0, stateTime = 0, settleTime = 0;
let popups = [], debris = [];
let dragging = false, lastStretchSound = -1;
let hits = [];
const fresh = new Map();   // contact -> relative speed at first touch

const damageEnabled = () => state !== 'menu' && time - levelStartTime > 1.0;

function newWorld() {
  world = new pl.World({ gravity: V(0, GRAVITY) });
  world.on('begin-contact', c => {
    const a = c.getFixtureA().getBody(), b = c.getFixtureB().getBody();
    const rel = pl.Vec2.sub(a.getLinearVelocity(), b.getLinearVelocity()).length();
    fresh.set(c, rel);
  });
  world.on('end-contact', c => fresh.delete(c));
  world.on('post-solve', (c, imp) => {
    if (!fresh.has(c)) return;
    const rel = fresh.get(c);
    fresh.delete(c);
    let sum = 0;
    const n = c.getManifold().pointCount;
    for (let i = 0; i < n; i++) sum += imp.normalImpulses[i];
    hits.push([c.getFixtureA().getBody().getUserData(), c.getFixtureB().getBody().getUserData(), sum, rel]);
  });
  const ground = world.createBody({ type: 'static', position: V(5, -5) });
  ground.createFixture(pl.Box(45, 5), { friction: 0.8, restitution: 0.05 });
  ground.setUserData({ kind: 'ground' });
}

// ---- level construction -----------------------------------------------------

function block(m, x, y, w, h, angle = 0) {
  const mat = MAT[m];
  const body = world.createBody({ type: 'dynamic', position: V(x, y), angle: angle * Math.PI / 180 });
  const mass = Math.max(0.15, w * h * mat.density);
  body.createFixture(pl.Box(w / 2, h / 2), { density: mass / (w * h), friction: 0.7, restitution: 0.02 });
  const o = {
    kind: 'block', m, body, w, h,
    maxHealth: mat.health * Math.min(2, Math.max(0.6, w * h * 2)),
    score: mat.score, debris: mat.debris, seed: Math.random() * 1000,
  };
  o.health = o.maxHealth;
  body.setUserData(o);
  objects.push(o);
  return o;
}

function pig(x, y, r = 0.38, helmet = false) {
  const body = world.createBody({ type: 'dynamic', position: V(x, y + r), angularDamping: 2 });
  const mass = 0.6 + r;
  body.createFixture(pl.Circle(r), { density: mass / (Math.PI * r * r), friction: 0.7, restitution: 0.02 });
  const o = {
    kind: 'pig', body, r, helmet, isPig: true,
    maxHealth: (helmet ? 7 : 3) * (r / 0.38), score: 5000, debris: '#73cc40',
  };
  o.health = o.maxHealth;
  body.setUserData(o);
  objects.push(o);
  pigs.push(o);
}

/** Two posts and a roof plank. Returns the height of the roof top. */
function frame(m, cx, baseY, width, height, roof) {
  const t = 0.3;
  block(m, cx - width / 2 + t / 2, baseY + height / 2, t, height);
  block(m, cx + width / 2 - t / 2, baseY + height / 2, t, height);
  block(roof || m, cx, baseY + height + t / 2, width + 0.1, t);
  return baseY + height + t;
}

function buildLevel(i) {
  const Wd = 'wood', G = 'glass', S = 'stone';
  switch (i) {
    case 0: { // A simple hut.
      const top = frame(Wd, 6, 0, 2.4, 2);
      pig(6, 0); pig(6, top);
      setBirds('red', 'red', 'red');
      break;
    }
    case 1: { // Two-storey tower with glass.
      const y1 = frame(Wd, 7, 0, 2.6, 1.8);
      const y2 = frame(G, 7, y1, 2.0, 1.5, Wd);
      pig(7, 0); pig(7, y1); pig(7, y2, 0.32);
      block(G, 4.5, 0.6, 0.6, 1.2);
      setBirds('red', 'yellow', 'red');
      break;
    }
    case 2: { // Twin towers joined by a bridge.
      let a = frame(S, 4.5, 0, 1.8, 1.6), b = frame(S, 9.5, 0, 1.8, 1.6);
      a = frame(Wd, 4.5, a, 1.6, 1.4); b = frame(Wd, 9.5, b, 1.6, 1.4);
      block(Wd, 7, a + 0.15, 5.4, 0.3);
      pig(4.5, 0); pig(9.5, 0, 0.38, true); pig(7, 0, 0.5); pig(7, a + 0.3, 0.32);
      setBirds('red', 'yellow', 'red', 'yellow');
      break;
    }
    case 3: { // Pyramid of frames.
      frame(Wd, 4.6, 0, 1.8, 1.4); frame(G, 6.6, 0, 1.8, 1.4); frame(Wd, 8.6, 0, 1.8, 1.4);
      const top1 = 1.7;
      frame(Wd, 5.6, top1, 1.8, 1.3, S); frame(Wd, 7.6, top1, 1.8, 1.3, S);
      const top2 = top1 + 1.6;
      frame(G, 6.6, top2, 1.8, 1.2, Wd);
      pig(4.6, 0, 0.32); pig(6.6, 0, 0.32); pig(8.6, 0, 0.32);
      pig(6.6, top2, 0.36, true); pig(6.6, top2 + 1.5, 0.4);
      setBirds('yellow', 'red', 'yellow', 'red');
      break;
    }
    default: { // Fortress on a stone hill.
      block(S, 8, 0.5, 6, 1);
      const y = 1;
      frame(Wd, 6, y, 1.6, 1.6, S); frame(Wd, 10, y, 1.6, 1.6, S);
      const mid = frame(Wd, 8, y, 1.8, 2.2, S);
      frame(G, 8, mid, 1.4, 1.2, Wd);
      block(G, 4.2, 0.9, 0.5, 1.8); block(Wd, 12.2, 1.1, 0.4, 2.2);
      pig(6, y, 0.34); pig(10, y, 0.34, true); pig(8, y, 0.42, true); pig(8, mid, 0.3); pig(8, mid + 1.5, 0.5);
      setBirds('red', 'yellow', 'red', 'yellow', 'red');
      break;
    }
  }
}

function setBirds(...kinds) {
  queue = kinds.map(k => ({ kind: k, x: 0, y: BIRD_R, angle: 0, body: null, launched: false }));
  layoutQueue();
}

function layoutQueue() {
  queue.forEach((b, i) => { b.x = SLING.x - 0.9 - i * 0.65; b.y = BIRD_R; });
}

function loadLevel(i) {
  newWorld();
  fresh.clear();
  objects = []; pigs = []; popups = []; hits = [];
  current = null; dragging = false;
  level = i;
  if (i === 0) score = 0;
  levelStartScore = score;
  buildLevel(i);
  levelStartTime = time;
  nextBird();
}

function nextBird() {
  if (current) {
    burst(birdPos(current), '#ffffff', 6, 0.2);
    if (current.body) world.destroyBody(current.body);
  }
  current = null;
  if (!queue.length) return;
  current = queue.shift();
  current.x = REST.x; current.y = REST.y; current.angle = 0;
  layoutQueue();
  setState('aiming');
}

function setState(s) {
  state = s;
  stateTime = time;
  settleTime = 0;
  if (s === 'won') playSound('win');
  if (s === 'lost') playSound('lose');
}

// ---- birds ------------------------------------------------------------------

function birdPos(b) { if (b.body) { const p = b.body.getPosition(); return { x: p.x, y: p.y }; } return { x: b.x, y: b.y }; }

function launch(b, vx, vy) {
  const body = world.createBody({ type: 'dynamic', position: V(b.x, b.y), bullet: true, angularDamping: 1.5 });
  const mass = b.kind === 'yellow' ? 1.2 : 1.6;
  body.createFixture(pl.Circle(BIRD_R), { density: mass / (Math.PI * BIRD_R * BIRD_R), friction: 0.4, restitution: 0.1 });
  body.setLinearVelocity(V(vx, vy));
  body.setAngularVelocity(-vx * 40 * Math.PI / 180);
  b.body = body; b.launched = true; b.launchTime = time; b.slowTime = 0; b.hit = false; b.abilityUsed = false;
  body.setUserData(b);
}

function tryAbility(b) {
  if (!b || !b.launched || b.abilityUsed || b.hit || b.kind !== 'yellow') return false;
  b.abilityUsed = true;
  const v = b.body.getLinearVelocity();
  const len = v.length();
  const d = len > 0.1 ? { x: v.x / len, y: v.y / len } : { x: 1, y: 0 };
  b.body.setLinearVelocity(V(d.x * 24, d.y * 24));
  burst(birdPos(b), '#ffe666', 6, 0.15);
  return true;
}

function birdDone(b) {
  if (!b) return true;
  if (!b.launched) return false;
  const since = time - b.launchTime;
  if (since > 9) return true;
  const p = birdPos(b);
  if (p.y < -5 || p.x > 16 || p.x < -20) return true; // off-screen
  return since > 0.5 && b.slowTime > 1.2;
}

// ---- damage -----------------------------------------------------------------

function applyHit(o, other, impulse, rel) {
  if (!o || o.dead || (o.kind !== 'block' && o.kind !== 'pig')) return;
  impulse = Math.max(impulse, rel * 0.25);
  if (other && other.kind && (other.kind === 'red' || other.kind === 'yellow')) impulse *= 1.5;
  if (impulse < 0.8) return;
  damage(o, impulse);
  if (impulse > 2) playSound('hit', Math.min(1, impulse / 10));
}

function damage(o, amount) {
  if (o.dead) return;
  o.health -= amount;
  if (o.health <= 0) breakObj(o);
}

function breakObj(o) {
  if (o.dead) return;
  o.dead = true;
  const p = o.body.getPosition();
  addScore(o.score, p.x, p.y, o.isPig ? '#4de633' : '#ffffff');
  if (o.isPig) { pigs.splice(pigs.indexOf(o), 1); playSound('pig'); }
  else playSound('hit', 0.6);
  const size = o.isPig ? o.r * 2 * 1.414 : Math.hypot(o.w, o.h);
  burst(p, o.debris, o.isPig ? 14 : 8, size * 0.12);
  world.destroyBody(o.body);
  objects.splice(objects.indexOf(o), 1);
}

function addScore(amount, x, y, color) {
  score += amount;
  popups.push({ x, y, text: String(amount), t: time, color });
}

function burst(p, color, count, size) {
  size = Math.min(0.3, Math.max(0.08, size));
  for (let i = 0; i < count; i++) {
    const a = Math.random() * Math.PI * 2, r = Math.random() * 0.3, s = Math.random() * 4;
    debris.push({
      x: p.x + Math.cos(a) * r, y: p.y + Math.sin(a) * r,
      vx: Math.cos(a) * s, vy: Math.sin(a) * s + 2,
      rot: Math.random() * 6.28, spin: (Math.random() * 2 - 1) * 9.4,
      size: size * (0.6 + Math.random() * 0.8), life: 0.6 + Math.random() * 0.5, age: 0,
      color, round: Math.random() < 0.5,
    });
  }
}

// ---- input ------------------------------------------------------------------

const input = { down: false, held: false, up: false, x: 0, y: 0 };
let buttons = [];          // [{x,y,w,h,action}] in CSS pixels, from the last draw

function pointerPos(e) { return { x: e.clientX, y: e.clientY }; }

canvas.addEventListener('pointerdown', e => {
  initAudio();
  const p = pointerPos(e);
  for (const b of buttons) {
    if (p.x >= b.x && p.x <= b.x + b.w && p.y >= b.y && p.y <= b.y + b.h) { b.action(); e.preventDefault(); return; }
  }
  canvas.setPointerCapture && canvas.setPointerCapture(e.pointerId);
  input.down = true; input.held = true; input.x = p.x; input.y = p.y;
  e.preventDefault();
});
canvas.addEventListener('pointermove', e => { const p = pointerPos(e); input.x = p.x; input.y = p.y; });
const release = e => { if (!input.held) return; const p = pointerPos(e); input.x = p.x; input.y = p.y; input.held = false; input.up = true; };
canvas.addEventListener('pointerup', release);
canvas.addEventListener('pointercancel', release);

// Android back button (called from the Java shell).
window.handleBack = function () {
  if (state === 'menu') { if (window.Android) window.Android.quit(); }
  else setState('menu');
};
window.addEventListener('keydown', e => { if (e.key === 'Escape') window.handleBack(); });

function launchVelocity(off) { return { x: -off.x / MAX_DRAG * MAX_SPEED, y: -off.y / MAX_DRAG * MAX_SPEED }; }

/** Returns the clamped drag offset from the rest point for a world-space pointer. */
function dragOffset(wp) {
  let ox = wp.x - REST.x, oy = wp.y - REST.y;
  const len = Math.hypot(ox, oy);
  if (len > MAX_DRAG) { ox *= MAX_DRAG / len; oy *= MAX_DRAG / len; }
  const y = Math.max(REST.y + oy, BIRD_R + 0.05);
  return { x: ox, y: y - REST.y };
}

function handleSling() {
  if (!current || current.launched) return false;
  const wp = toWorld(input.x, input.y);
  if (input.down && Math.hypot(wp.x - current.x, wp.y - current.y) < 1.3) dragging = true;
  if (!dragging) return false;
  const off = dragOffset(wp);
  const mag = Math.hypot(off.x, off.y);
  if (input.held || input.down) {
    current.x = REST.x + off.x; current.y = REST.y + off.y;
    if (mag > 0.6 && time - lastStretchSound > 0.6) { lastStretchSound = time; playSound('stretch', 0.5); }
  }
  if (input.up) {
    dragging = false;
    if (mag < 0.3) { current.x = REST.x; current.y = REST.y; return false; }
    const v = launchVelocity(off);
    launch(current, v.x, v.y);
    return true;
  }
  return false;
}

// ---- simulation -------------------------------------------------------------

let accumulator = 0;

function physicsStep() {
  hits = [];
  world.step(STEP, 12, 6);
  for (const [a, b, imp, rel] of hits) {
    if (!damageEnabled()) break;
    applyHit(a, b, imp, rel);
    applyHit(b, a, imp, rel);
    if (a && a.launched) a.hit = true;
    if (b && b.launched) b.hit = true;
  }
  if (current && current.launched) {
    if (current.body.getLinearVelocity().length() < 0.25) current.slowTime += STEP;
    else current.slowTime = 0;
  }
  for (const o of objects.slice()) {
    const p = o.body.getPosition();
    if (p.y < -6 || Math.abs(p.x) > 40) breakObj(o);
  }
}

function worldAtRest() {
  for (let b = world.getBodyList(); b; b = b.getNext()) {
    // The spent bird may still be rolling far away; it's already judged by birdDone().
    if (current && b === current.body) continue;
    if (b.isDynamic() && b.getLinearVelocity().lengthSquared() > 0.04) return false;
  }
  return true;
}

function updateFlying(dt) {
  const done = birdDone(current);
  const allSlow = done && worldAtRest();
  if (pigs.length === 0 || allSlow) settleTime += dt; else settleTime = 0;
  const timeout = done && time - stateTime > 14;
  if (settleTime < 1.0 && !timeout) return;

  if (pigs.length === 0) {
    const bonus = queue.length * 10000;
    if (bonus > 0) addScore(bonus, REST.x, REST.y + 1, '#ffd933');
    if (level === LEVEL_COUNT - 1 && score > best) { best = score; save('best', best); }
    setState('won');
  } else if (queue.length > 0) {
    nextBird();
  } else {
    setState('lost');
  }
}

function update(dt) {
  time += dt;
  accumulator = Math.min(accumulator + dt, 0.25);
  while (accumulator >= STEP) { physicsStep(); accumulator -= STEP; }

  if (state === 'aiming') {
    if (handleSling()) { playSound('launch'); setState('flying'); }
  } else if (state === 'flying') {
    if (input.down && tryAbility(current)) playSound('launch', 0.7);
    updateFlying(dt);
  }

  for (let i = debris.length - 1; i >= 0; i--) {
    const d = debris[i];
    d.age += dt; d.vy += GRAVITY * dt; d.x += d.vx * dt; d.y += d.vy * dt; d.rot += d.spin * dt;
    if (d.age >= d.life) debris.splice(i, 1);
  }
  input.down = false; input.up = false;
}

// ---- drawing: world ---------------------------------------------------------

/** Run fn in a local frame: origin (x,y), rotation, `scale` world units per local unit, y up. */
function local(x, y, angle, scale, fn) {
  ctx.save();
  ctx.translate(sx(x), sy(y));
  ctx.rotate(-angle);
  ctx.scale(ppu * scale, -ppu * scale);
  fn();
  ctx.restore();
}

function circle(x, y, r, color) { ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill(); }

function drawBackground() {
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, '#5fb6ee'); g.addColorStop(1, '#c4e8fb');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  for (let i = 0; i < 5; i++) {
    const x = -10 + i * 6 + (i % 2) * 2, y = 7.5 + (i % 3) * 1.2;
    local(x, y, 0, 1, () => {
      ctx.globalAlpha = 0.9;
      circle(-0.8, -0.1, 0.9, '#fff'); circle(0.2, 0.0, 1.1, '#fff'); circle(1.1, -0.2, 0.8, '#fff');
    });
  }
  for (let i = 0; i < 6; i++) {
    local(-14 + i * 6.5, -2.5, 0, 1, () => { ctx.beginPath(); ctx.ellipse(0, 0, 4.5, 3.5, 0, 0, Math.PI * 2); ctx.fillStyle = '#78bf66'; ctx.fill(); });
  }
  ctx.fillStyle = '#6b4a29'; ctx.fillRect(0, sy(0), W, H - sy(0));
  ctx.fillStyle = '#59b333'; ctx.fillRect(0, sy(0), W, 0.3 * ppu);
}

function drawRect(x, y, angle, w, h, color) {
  local(x, y, angle, 1, () => { ctx.fillStyle = color; ctx.fillRect(-w / 2, -h / 2, w, h); });
}

function drawSlingBack() {
  drawRect(-8.2, 2.05, 18 * Math.PI / 180, 0.2, 0.8, '#3b210d');
  drawRect(-8, 0.85, 0, 0.28, 1.7, '#73421a');
}
function drawSlingFront() { drawRect(-7.8, 2.05, -18 * Math.PI / 180, 0.2, 0.8, '#73421a'); }

function drawBand(tip, to) {
  ctx.beginPath(); ctx.moveTo(sx(tip.x), sy(tip.y)); ctx.lineTo(sx(to.x), sy(to.y));
  ctx.strokeStyle = '#4d260d'; ctx.lineWidth = 0.11 * ppu; ctx.lineCap = 'round'; ctx.stroke();
}

function pouchPos() { return current && !current.launched ? { x: current.x, y: current.y } : REST; }

function drawBlock(o) {
  const p = o.body.getPosition(), mat = MAT[o.m];
  const dmg = 1 - Math.max(0, o.health) / o.maxHealth;
  local(p.x, p.y, o.body.getAngle(), 1, () => {
    const w = o.w, h = o.h, e = 0.06;
    ctx.fillStyle = mat.edge; ctx.fillRect(-w / 2, -h / 2, w, h);
    ctx.fillStyle = mat.fill; ctx.fillRect(-w / 2 + e, -h / 2 + e, w - 2 * e, h - 2 * e);
    ctx.lineWidth = 0.025;
    if (o.m === 'wood') {
      ctx.strokeStyle = 'rgba(110,60,20,0.45)';
      const long = w > h;
      for (let i = 1; i < 3; i++) {
        ctx.beginPath();
        if (long) { const yy = -h / 2 + (h * i) / 3; ctx.moveTo(-w / 2 + e, yy); ctx.lineTo(w / 2 - e, yy); }
        else { const xx = -w / 2 + (w * i) / 3; ctx.moveTo(xx, -h / 2 + e); ctx.lineTo(xx, h / 2 - e); }
        ctx.stroke();
      }
    } else if (o.m === 'glass') {
      ctx.strokeStyle = 'rgba(255,255,255,0.8)';
      ctx.beginPath(); ctx.moveTo(-w / 2 + e * 2, -h / 2 + e * 2); ctx.lineTo(Math.min(w, h) * 0.4 - w / 2, Math.min(w, h) * 0.4 - h / 2); ctx.stroke();
    } else {
      ctx.fillStyle = 'rgba(60,60,70,0.35)';
      for (let i = 0; i < 4; i++) {
        const fx = ((o.seed * (i + 1) * 7.13) % 1) - 0.5, fy = ((o.seed * (i + 1) * 3.71) % 1) - 0.5;
        ctx.beginPath(); ctx.arc(fx * (w - 0.2), fy * (h - 0.2), 0.05, 0, 6.29); ctx.fill();
      }
    }
    if (dmg > 0.05) {
      ctx.strokeStyle = 'rgba(30,20,10,' + (0.3 + dmg * 0.5) + ')'; ctx.lineWidth = 0.03;
      ctx.beginPath(); ctx.moveTo(-w * 0.3, h * 0.35); ctx.lineTo(0, 0); ctx.lineTo(w * 0.2, -h * 0.3);
      if (dmg > 0.5) { ctx.moveTo(0, 0); ctx.lineTo(w * 0.35, h * 0.1); }
      ctx.stroke();
      ctx.fillStyle = 'rgba(0,0,0,' + dmg * 0.3 + ')'; ctx.fillRect(-w / 2, -h / 2, w, h);
    }
  });
}

function drawPig(o) {
  const p = o.body.getPosition();
  const dmg = 1 - Math.max(0, o.health) / o.maxHealth;
  local(p.x, p.y, o.body.getAngle(), o.r * 2, () => {
    circle(0, 0, 0.5, '#2e6e17');
    circle(0, 0, 0.47, '#73cc40');
    if (o.helmet) {
      ctx.save(); ctx.beginPath(); ctx.arc(0, 0, 0.5, 0, Math.PI * 2); ctx.clip();
      ctx.fillStyle = '#9a9aa6'; ctx.fillRect(-0.5, 0.2, 1, 0.4);
      ctx.fillStyle = '#7d7d88'; ctx.fillRect(-0.5, 0.2, 1, 0.05);
      ctx.restore();
    }
    ctx.beginPath(); ctx.ellipse(0, -0.08, 0.17, 0.13, 0, 0, 6.29); ctx.fillStyle = '#3f8c1f'; ctx.fill();
    ctx.beginPath(); ctx.ellipse(0, -0.08, 0.15, 0.11, 0, 0, 6.29); ctx.fillStyle = '#9be66b'; ctx.fill();
    circle(-0.05, -0.08, 0.035, '#2e6e17'); circle(0.05, -0.08, 0.035, '#2e6e17');
    circle(-0.2, 0.12, 0.09, '#fff'); circle(0.2, 0.12, 0.09, '#fff');
    if (dmg > 0.4) {
      ctx.strokeStyle = '#000'; ctx.lineWidth = 0.035;
      for (const ex of [-0.2, 0.2]) { ctx.beginPath(); ctx.moveTo(ex - 0.05, 0.07); ctx.lineTo(ex + 0.05, 0.17); ctx.moveTo(ex + 0.05, 0.07); ctx.lineTo(ex - 0.05, 0.17); ctx.stroke(); }
    } else {
      circle(-0.18, 0.11, 0.04, '#000'); circle(0.18, 0.11, 0.04, '#000');
    }
    if (dmg > 0.05) { ctx.globalAlpha = dmg * 0.3; circle(0, 0, 0.5, '#000'); }
  });
}

function drawBird(b) {
  const p = birdPos(b), angle = b.body ? b.body.getAngle() : 0;
  const body = b.kind === 'yellow' ? '#ffd926' : '#db1f1f';
  local(p.x, p.y, angle, BIRD_R * 2, () => {
    circle(0, 0, 0.5, b.kind === 'yellow' ? '#b38f00' : '#8a0f0f');
    circle(0, 0, 0.47, body);
    ctx.save(); ctx.beginPath(); ctx.arc(0, 0, 0.47, 0, 6.29); ctx.clip();
    circle(-0.05, -0.28, 0.26, '#f7e0bf');
    ctx.restore();
    if (b.kind === 'red') { // head feathers
      ctx.fillStyle = body;
      ctx.beginPath(); ctx.moveTo(-0.1, 0.42); ctx.lineTo(-0.2, 0.62); ctx.lineTo(0.02, 0.46); ctx.lineTo(0.0, 0.66); ctx.lineTo(0.1, 0.44); ctx.fill();
    } else {
      ctx.fillStyle = '#222';
      ctx.beginPath(); ctx.moveTo(-0.05, 0.45); ctx.lineTo(0.05, 0.62); ctx.lineTo(0.1, 0.44); ctx.fill();
    }
    circle(0.1, 0.08, 0.1, '#fff'); circle(0.3, 0.08, 0.1, '#fff');
    circle(0.13, 0.07, 0.045, '#000'); circle(0.33, 0.07, 0.045, '#000');
    ctx.strokeStyle = '#000'; ctx.lineWidth = 0.07; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(-0.01, 0.25); ctx.lineTo(0.42, 0.11); ctx.stroke();
    ctx.fillStyle = '#ffa61a';
    ctx.beginPath(); ctx.moveTo(0.17, 0.0); ctx.lineTo(0.17, -0.15); ctx.lineTo(0.5, -0.06); ctx.closePath(); ctx.fill();
  });
}

function drawDots() {
  if (!dragging || !current || current.launched) return;
  const off = { x: current.x - REST.x, y: current.y - REST.y };
  if (Math.hypot(off.x, off.y) <= 0.25) return;
  const v = launchVelocity(off);
  for (let i = 0; i < 18; i++) {
    const t = (i + 1) * 0.07;
    const x = current.x + v.x * t, y = current.y + v.y * t + 0.5 * GRAVITY * t * t;
    const s = 0.16 + (0.06 - 0.16) * (i / 18);
    ctx.globalAlpha = 0.8; circle(sx(x), sy(y), (s / 2) * ppu, '#fff'); ctx.globalAlpha = 1;
  }
}

function drawDebris() {
  for (const d of debris) {
    ctx.globalAlpha = Math.max(0, 1 - d.age / d.life);
    local(d.x, d.y, d.rot, d.size, () => {
      ctx.fillStyle = d.color;
      if (d.round) { ctx.beginPath(); ctx.arc(0, 0, 0.5, 0, 6.29); ctx.fill(); } else ctx.fillRect(-0.5, -0.5, 1, 1);
    });
  }
  ctx.globalAlpha = 1;
}

// ---- drawing: UI ------------------------------------------------------------

function text(str, x, y, size, color, align = 'left', baseline = 'top') {
  ctx.font = 'bold ' + Math.round(size * uiScale) + 'px sans-serif';
  ctx.textAlign = align; ctx.textBaseline = baseline;
  ctx.fillStyle = 'rgba(0,0,0,0.6)';
  ctx.fillText(str, x * uiScale + 3, y * uiScale + 3);
  ctx.fillStyle = color;
  ctx.fillText(str, x * uiScale, y * uiScale);
}

function button(x, y, w, h, label, size, action) {
  const s = uiScale;
  const r = 14 * s;
  ctx.beginPath();
  ctx.roundRect ? ctx.roundRect(x * s, y * s, w * s, h * s, r) : ctx.rect(x * s, y * s, w * s, h * s);
  const g = ctx.createLinearGradient(0, y * s, 0, (y + h) * s);
  g.addColorStop(0, '#ffb43c'); g.addColorStop(1, '#e0701a');
  ctx.fillStyle = g; ctx.fill();
  ctx.lineWidth = 3 * s; ctx.strokeStyle = '#7a3a0a'; ctx.stroke();
  text(label, x + w / 2, y + h / 2, size, '#fff', 'center', 'middle');
  buttons.push({ x: x * s, y: y * s, w: w * s, h: h * s, action });
}

function star(cx, cy, r, color) {
  ctx.beginPath();
  for (let i = 0; i < 10; i++) {
    const rr = i % 2 === 0 ? r : r * 0.42, a = -Math.PI / 2 + i * Math.PI / 5;
    ctx.lineTo(cx + rr * Math.cos(a), cy + rr * Math.sin(a));
  }
  ctx.closePath(); ctx.fillStyle = color; ctx.fill();
  ctx.lineWidth = 3 * uiScale; ctx.strokeStyle = 'rgba(0,0,0,0.35)'; ctx.stroke();
}

function dim(alpha) { ctx.fillStyle = 'rgba(0,0,0,' + alpha + ')'; ctx.fillRect(0, 0, W, H); }

function drawUI() {
  buttons = [];
  const w = W / uiScale;

  for (let i = popups.length - 1; i >= 0; i--) {
    const p = popups[i], age = time - p.t;
    if (age > 1.2) { popups.splice(i, 1); continue; }
    ctx.globalAlpha = 1 - age / 1.2;
    text(p.text, sx(p.x) / uiScale, sy(p.y + age) / uiScale, 30, p.color, 'center', 'middle');
    ctx.globalAlpha = 1;
  }

  if (state === 'menu') {
    dim(0.35);
    text('ANGRY BIRDS', w / 2, 190, 72, '#ff4d33', 'center', 'middle');
    text('Drag the bird back and release to fire.  Yellow birds: tap mid-air to boost!', w / 2, 255, 22, '#fff', 'center', 'middle');
    if (best > 0) text('Best total: ' + best, w / 2, 300, 28, '#ffeb3b', 'center', 'middle');
    button(w / 2 - 160, 360, 320, 90, 'PLAY', 36, () => loadLevel(0));
    if (level > 0) button(w / 2 - 160, 470, 320, 80, 'CONTINUE (Level ' + (level + 1) + ')', 24, () => loadLevel(level));
    return;
  }

  text('Level ' + (level + 1) + ' / ' + LEVEL_COUNT, 24, 16, 30, '#fff');
  text('Score ' + score, 24, 56, 30, '#fff');
  text('Pigs ' + pigs.length, 24, 96, 30, '#b3ff80');
  button(w - 160, 16, 140, 60, 'RETRY', 22, () => loadLevel(level));
  button(w - 290, 16, 120, 60, 'MENU', 22, () => setState('menu'));

  if (state === 'won' || state === 'lost') {
    dim(0.45);
    const won = state === 'won', last = level === LEVEL_COUNT - 1;
    text(won ? (last ? 'YOU BEAT THEM ALL!' : 'LEVEL CLEARED!') : 'LEVEL FAILED', w / 2, 200, 64, won ? '#ffd933' : '#ff6650', 'center', 'middle');
    if (won) {
      const stars = 1 + (queue.length >= 1 ? 1 : 0) + (queue.length >= 2 ? 1 : 0);
      for (let i = 0; i < 3; i++)
        star((w / 2 - 90 + i * 90) * uiScale, 285 * uiScale, 38 * uiScale, i < stars ? '#ffd926' : 'rgba(255,255,255,0.3)');
      text('Level score ' + (score - levelStartScore) + '     Total ' + score, w / 2, 350, 30, '#fff', 'center', 'middle');
    }
    if (time - stateTime < 0.6) return;
    button(w / 2 - 330, 420, 300, 90, 'RETRY', 32, () => loadLevel(level));
    if (won) button(w / 2 + 30, 420, 300, 90, last ? 'PLAY AGAIN' : 'NEXT', 32, () => loadLevel(last ? 0 : level + 1));
    else button(w / 2 + 30, 420, 300, 90, 'MENU', 32, () => setState('menu'));
  }
}

function draw() {
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  drawBackground();
  drawSlingBack();
  drawBand(BACK_TIP, pouchPos());
  for (const o of objects) if (o.kind === 'block') drawBlock(o);
  for (const o of objects) if (o.kind === 'pig') drawPig(o);
  for (const b of queue) drawBird(b);
  if (current) drawBird(current);
  drawBand(FRONT_TIP, pouchPos());
  drawSlingFront();
  drawDots();
  drawDebris();
  drawUI();
}

// ---- main loop --------------------------------------------------------------

let last = performance.now();
function tick(now) {
  const dt = Math.min(0.1, (now - last) / 1000);
  last = now;
  update(dt);
  draw();
  requestAnimationFrame(tick);
}

loadLevel(0);
setState('menu');
requestAnimationFrame(tick);

// Exposed for automated tests.
window.__game = {
  get state() { return state; }, get level() { return level; }, get pigs() { return pigs.length; },
  get birds() { return queue.length + (current && !current.launched ? 1 : 0); }, get score() { return score; },
  get pigPositions() { return pigs.map(o => { const q = o.body.getPosition(); return { x: q.x, y: q.y }; }); },
  loadLevel, setState, toScreen: (x, y) => ({ x: sx(x), y: sy(y) }), REST,
};
