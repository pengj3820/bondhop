# 渲染《飞机为什么能飞上天？》：每个场景用 cairo 逐帧画动画，配上 tts.py 生成的旁白和字幕。
# 用法：python3 tts.py && python3 render.py   → 输出 build/how-planes-fly.mp4
import json, math, os, subprocess, sys
from multiprocessing import Pool

import cairo
import numpy as np

from script import SCENES

W, H, FPS = 1280, 720, 25
PAD0, GAP, PAD1 = 0.6, 0.4, 1.0
FONT = "WenQuanYi Zen Hei"
BUILD = "build"

# 配色
INK = (0.13, 0.15, 0.25)
WHITE = (1, 1, 1)
SKY_TOP, SKY_BOT = (0.45, 0.75, 0.97), (0.86, 0.95, 1.0)
GREEN, RED, ORANGE, PURPLE = (0.18, 0.72, 0.35), (0.90, 0.25, 0.25), (0.98, 0.58, 0.10), (0.55, 0.35, 0.85)
BLUE, DBLUE, GRAY = (0.15, 0.50, 0.95), (0.10, 0.30, 0.65), (0.62, 0.65, 0.72)
YELLOW = (1.0, 0.82, 0.15)


# ---------------------------------------------------------------- 基础工具
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def lerp(a, b, u):
    return a + (b - a) * u


class Scene:
    def __init__(self, key, title, lines, durs):
        self.key, self.title, self.lines, self.durs = key, title, lines, durs
        self.starts, self.ends = [], []
        t = PAD0
        for d in durs:
            self.starts.append(t)
            self.ends.append(t + d)
            t += d + GAP
        self.dur = self.ends[-1] + PAD1
        self.nframes = int(round(self.dur * FPS))

    def k(self, t):
        """当前（最近开始的）句子序号"""
        i = 0
        for j, s in enumerate(self.starts):
            if t >= s - 0.15:
                i = j
        return i

    def since(self, i, t):
        return t - self.starts[i]

    def on(self, i, t, d=0.6):
        """第 i 句开始后的渐入进度 0..1"""
        return ease((t - self.starts[i] + 0.15) / d)


def font(c, size, bold=True):
    c.select_font_face(FONT, cairo.FONT_SLANT_NORMAL,
                       cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    c.set_font_size(size)


def text_w(c, s, size, bold=True):
    font(c, size, bold)
    return c.text_extents(s).x_advance


def text(c, s, x, y, size, rgb=INK, align="c", alpha=1.0, stroke=None, bold=True):
    """y 为文字竖直中心"""
    if alpha <= 0:
        return
    font(c, size, bold)
    w = c.text_extents(s).x_advance
    x0 = x - w / 2 if align == "c" else (x if align == "l" else x - w)
    y0 = y + size * 0.36
    if stroke:
        c.move_to(x0, y0)
        c.text_path(s)
        c.set_source_rgba(*stroke, alpha)
        c.set_line_width(size * 0.18)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.stroke()
    c.move_to(x0, y0)
    c.set_source_rgba(*rgb, alpha)
    c.show_text(s)


def rrect(c, x, y, w, h, r):
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    c.close_path()


def label(c, s, x, y, size=26, fg=WHITE, bg=INK, alpha=1.0, pad=12):
    """圆角底色标签，(x, y) 为中心"""
    if alpha <= 0:
        return
    w = text_w(c, s, size) + pad * 2
    h = size + pad * 1.3
    rrect(c, x - w / 2, y - h / 2, w, h, h / 2.2)
    c.set_source_rgba(*bg, alpha * 0.92)
    c.fill()
    text(c, s, x, y, size, fg, alpha=alpha)


def fill_stroke(c, rgb, alpha=1.0, outline=INK, lw=3):
    c.set_source_rgba(*rgb, alpha)
    if outline:
        c.fill_preserve()
        c.set_source_rgba(*outline, alpha)
        c.set_line_width(lw)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.stroke()
    else:
        c.fill()


def arrow(c, x1, y1, x2, y2, rgb, w=14, head=30, alpha=1.0, outline=INK):
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    if L < 2 or alpha <= 0:
        return
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    head = min(head, L * 0.6)
    bx, by = x2 - ux * head, y2 - uy * head
    hw = w / 2
    pts = [(x1 + nx * hw, y1 + ny * hw), (bx + nx * hw, by + ny * hw), (bx + nx * hw * 2.4, by + ny * hw * 2.4),
           (x2, y2), (bx - nx * hw * 2.4, by - ny * hw * 2.4), (bx - nx * hw, by - ny * hw),
           (x1 - nx * hw, y1 - ny * hw)]
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()
    fill_stroke(c, rgb, alpha, outline, 2.5)


def sky(c, top=SKY_TOP, bot=SKY_BOT):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *top)
    g.add_color_stop_rgb(1, *bot)
    c.set_source(g)
    c.paint()


def cloud(c, x, y, s=1.0, alpha=0.9):
    c.set_source_rgba(1, 1, 1, alpha)
    for dx, dy, r in [(-50, 8, 30), (-15, -12, 40), (30, -5, 34), (60, 10, 24), (5, 14, 30)]:
        c.arc(x + dx * s, y + dy * s, r * s, 0, 2 * math.pi)
        c.fill()


def clouds(c, t, speed=30, alpha=0.85):
    for i, (x, y, s) in enumerate([(200, 120, 1.0), (700, 80, 0.8), (1100, 160, 1.2), (450, 230, 0.6), (950, 300, 0.7)]):
        xx = (x - t * speed * (0.6 + 0.2 * i)) % (W + 300) - 150
        cloud(c, xx, y, s, alpha)


def ground(c, y, rgb=(0.55, 0.80, 0.40)):
    c.rectangle(0, y, W, H - y)
    c.set_source_rgb(*rgb)
    c.fill()


# ---------------------------------------------------------------- 飞机
def plane_side(c, x, y, s=1.0, ang=0.0, elev=0.0, flame=0.0, hl=None, t=0.0, gear=False):
    """侧视图，机头朝右。ang：抬头角（度）；elev：升降舵后缘上翘角（度）；hl：高亮部件"""
    hl = hl or {}
    c.save()
    c.translate(x, y)
    c.rotate(-math.radians(ang))
    c.scale(s, s)
    # 远侧机翼
    c.move_to(48, 6); c.line_to(2, 6); c.line_to(-62, 42); c.line_to(-36, 42); c.close_path()
    fill_stroke(c, (0.70, 0.73, 0.80), 1, INK, 2.5)
    # 垂直尾翼与方向舵
    c.move_to(-100, -18); c.line_to(-140, -92); c.line_to(-160, -92); c.line_to(-152, -18); c.close_path()
    fill_stroke(c, (0.20, 0.45, 0.85), 1, INK, 2.5)
    c.move_to(-152, -18); c.line_to(-160, -92); c.line_to(-174, -92); c.line_to(-170, -14); c.close_path()
    fill_stroke(c, hl.get("rudder", (0.20, 0.45, 0.85)), 1, INK, 2.5)
    # 机身
    c.move_to(-172, -16); c.line_to(110, -20)
    c.curve_to(140, -20, 168, -10, 168, 2)
    c.curve_to(168, 14, 145, 20, 110, 20)
    c.line_to(-80, 20)
    c.curve_to(-115, 20, -150, 6, -176, -8)
    c.close_path()
    path = c.copy_path()
    c.set_source_rgb(1, 1, 1)
    c.fill_preserve()
    c.save(); c.clip()
    c.rectangle(-200, 5, 400, 6); c.set_source_rgb(0.20, 0.45, 0.85); c.fill()
    c.restore()
    c.new_path(); c.append_path(path)
    c.set_source_rgb(*INK); c.set_line_width(3); c.stroke()
    # 窗户与驾驶舱
    c.set_source_rgb(0.25, 0.45, 0.70)
    for wx in range(-100, 100, 15):
        c.arc(wx, -6, 3.5, 0, 2 * math.pi); c.fill()
    c.move_to(138, -13); c.line_to(156, -9); c.line_to(161, -2); c.line_to(138, -3); c.close_path()
    fill_stroke(c, (0.25, 0.45, 0.70), 1, INK, 2)
    # 水平尾翼 + 升降舵
    c.move_to(-118, -8); c.line_to(-150, -14); c.line_to(-160, -10); c.line_to(-150, -4); c.close_path()
    fill_stroke(c, (0.80, 0.82, 0.88), 1, INK, 2.5)
    a = math.radians(elev)
    c.save(); c.translate(-158, -10); c.rotate(a)
    c.move_to(0, -3); c.line_to(-30, -1.5); c.line_to(-30, 1.5); c.line_to(0, 3); c.close_path()
    fill_stroke(c, hl.get("elevator", (0.80, 0.82, 0.88)), 1, INK, 2.5)
    c.restore()
    # 近侧机翼（从机身下方伸出）
    c.move_to(60, 10); c.line_to(10, 10); c.line_to(-40, 34); c.line_to(-14, 36); c.close_path()
    fill_stroke(c, hl.get("wing", (0.82, 0.84, 0.90)), 1, INK, 2.5)
    # 发动机
    if flame > 0:
        for i in range(6):
            ph = (t * 6 + i / 6) % 1
            c.set_source_rgba(1, 0.7 - 0.4 * ph, 0.2, (1 - ph) * 0.6 * flame)
            c.arc(-14 - ph * 90 * flame, 36 + math.sin(i * 2.1) * 3, 6 + ph * 12, 0, 2 * math.pi)
            c.fill()
    c.move_to(8, 18); c.line_to(22, 26); c.line_to(30, 26); c.line_to(20, 18); c.close_path()
    fill_stroke(c, (0.75, 0.77, 0.83), 1, INK, 2)
    rrect(c, -12, 26, 54, 20, 9)
    fill_stroke(c, hl.get("engine", (0.85, 0.87, 0.92)), 1, INK, 2.5)
    c.save(); c.translate(42, 36); c.scale(5, 10); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore()
    fill_stroke(c, (0.30, 0.32, 0.40), 1, INK, 2)
    if gear:
        c.set_source_rgb(*INK); c.set_line_width(4)
        for gx in (-30, 120):
            c.move_to(gx, 18); c.line_to(gx, 40); c.stroke()
            c.arc(gx, 44, 7, 0, 2 * math.pi); c.fill()
    c.restore()


def plane_top(c, x, y, s=1.0, yaw=0.0, rudder=0.0, ail=0.0, elev=0.0, hl=None):
    """俯视图，机头朝上。yaw：向右转为正（度）；rudder：方向舵后缘偏向右为正"""
    hl = hl or {}
    c.save(); c.translate(x, y); c.rotate(math.radians(yaw)); c.scale(s, s)
    for sx in (-1, 1):
        # 主翼
        c.move_to(sx * 14, -30); c.line_to(sx * 170, 40); c.line_to(sx * 170, 58); c.line_to(sx * 14, 30); c.close_path()
        fill_stroke(c, (0.82, 0.84, 0.90), 1, INK, 2.5)
        # 副翼
        c.move_to(sx * 115, 33 + 0); c.line_to(sx * 165, 55); c.line_to(sx * 165, 66); c.line_to(sx * 115, 44); c.close_path()
        fill_stroke(c, hl.get("aileron", (0.82, 0.84, 0.90)), 1, INK, 2)
        # 发动机
        rrect(c, sx * 70 - 9, -2, 18, 40, 7)
        fill_stroke(c, (0.85, 0.87, 0.92), 1, INK, 2)
        # 水平尾翼 + 升降舵
        c.move_to(sx * 10, 120); c.line_to(sx * 64, 150); c.line_to(sx * 64, 158); c.line_to(sx * 10, 148); c.close_path()
        fill_stroke(c, (0.82, 0.84, 0.90), 1, INK, 2)
        c.move_to(sx * 10, 148); c.line_to(sx * 64, 158); c.line_to(sx * 64, 168); c.line_to(sx * 10, 160); c.close_path()
        fill_stroke(c, hl.get("elevator", (0.82, 0.84, 0.90)), 1, INK, 2)
    # 机身
    c.save(); c.translate(0, 20); c.scale(18, 160); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore()
    fill_stroke(c, WHITE, 1, INK, 3)
    c.move_to(-9, -122); c.curve_to(-6, -132, 6, -132, 9, -122); c.close_path()
    fill_stroke(c, (0.25, 0.45, 0.70), 1, INK, 2)
    # 垂直尾翼（俯视为一条线）+ 方向舵
    c.move_to(-3, 110); c.line_to(3, 110); c.line_to(3, 160); c.line_to(-3, 160); c.close_path()
    fill_stroke(c, (0.20, 0.45, 0.85), 1, INK, 2)
    c.save(); c.translate(0, 160); c.rotate(-math.radians(rudder))
    c.move_to(-3, 0); c.line_to(3, 0); c.line_to(1.5, 30); c.line_to(-1.5, 30); c.close_path()
    fill_stroke(c, hl.get("rudder", (0.20, 0.45, 0.85)), 1, INK, 2)
    c.restore()
    c.restore()


def plane_front(c, x, y, s=1.0, roll=0.0, ail=0.0, hl=None):
    """正视图（飞机迎面飞来）。roll>0：画面左侧机翼抬起。ail>0：画面左侧副翼下偏、右侧上偏"""
    hl = hl or {}
    c.save(); c.translate(x, y); c.rotate(math.radians(roll)); c.scale(s, s)
    # 垂直尾翼
    c.move_to(-5, -20); c.line_to(-4, -110); c.line_to(4, -110); c.line_to(5, -20); c.close_path()
    fill_stroke(c, (0.20, 0.45, 0.85), 1, INK, 2.5)
    # 水平尾翼
    c.move_to(-70, -6); c.line_to(70, -6); c.line_to(70, 0); c.line_to(-70, 0); c.close_path()
    fill_stroke(c, (0.75, 0.77, 0.83), 1, INK, 2)
    # 主翼（略上反）
    for sx in (-1, 1):
        c.move_to(sx * 20, 10); c.line_to(sx * 240, -8); c.line_to(sx * 240, 0); c.line_to(sx * 20, 22); c.close_path()
        fill_stroke(c, (0.82, 0.84, 0.90), 1, INK, 2.5)
        d = ail * (-1 if sx < 0 else 1)  # 左下偏为正 → 用 y 偏移示意
        c.move_to(sx * 170, -2 - d * 0); c.line_to(sx * 232, -7); c.line_to(sx * 232, -7 - d * 18); c.line_to(sx * 170, -2 - d * 14); c.close_path()
        fill_stroke(c, hl.get("aileron", (0.95, 0.75, 0.20)), 1, INK, 2)
        c.save(); c.translate(sx * 85, 32); c.arc(0, 0, 17, 0, 2 * math.pi); c.restore()
        fill_stroke(c, (0.85, 0.87, 0.92), 1, INK, 2.5)
        c.arc(sx * 85, 32, 9, 0, 2 * math.pi); fill_stroke(c, (0.3, 0.32, 0.4), 1, None)
    # 机身
    c.arc(0, 0, 32, 0, 2 * math.pi)
    fill_stroke(c, WHITE, 1, INK, 3)
    c.move_to(-16, -10); c.line_to(16, -10); c.line_to(12, -2); c.line_to(-12, -2); c.close_path()
    fill_stroke(c, (0.25, 0.45, 0.70), 1, INK, 2)
    c.restore()


# ---------------------------------------------------------------- 儒可夫斯基翼型 + 势流（真实的绕翼气流）
MU = complex(-0.10, 0.10)
R = abs(1 - MU)
ALPHA = math.radians(8)
U = 1.0
# 库塔条件：后缘 ζ=1 处速度为零，求环量
_dW = lambda zeta, G: U * (np.exp(-1j * ALPHA) - R ** 2 * np.exp(1j * ALPHA) / (zeta - MU) ** 2) + 1j * G / (2 * np.pi * (zeta - MU))
GAMMA = (-(U * (np.exp(-1j * ALPHA) - R ** 2 * np.exp(1j * ALPHA) / (1 - MU) ** 2)) * 2 * np.pi * (1 - MU) / 1j).real


def airfoil_pts(n=200):
    th = np.linspace(0, 2 * np.pi, n)
    zeta = MU + R * np.exp(1j * th)
    return zeta + 1 / zeta  # 后缘约在 x=+2，前缘约在 x=-2


def zeta_of(z):
    s = np.sqrt(z * z - 4 + 0j)
    z1, z2 = (z + s) / 2, (z - s) / 2
    return np.where(np.abs(z1 - MU) >= np.abs(z2 - MU), z1, z2)


def vel(zeta):
    """z 平面中的速度 u+iv"""
    dz = 1 - 1 / zeta ** 2
    return np.conj(_dW(zeta, GAMMA) / dz)


class Flow:
    """把数学坐标映射到屏幕：来流水平、从右往左吹（飞机向右飞），翼型抬头 ALPHA"""

    def __init__(self, cx=640, cy=330, sc=100):
        self.cx, self.cy, self.sc = cx, cy, sc
        self.rot = np.exp(-1j * ALPHA)

    def scr(self, z):  # 数学 z → 屏幕
        d = z * self.rot
        return self.cx - self.sc * d.real, self.cy - self.sc * d.imag

    def inv(self, X, Y):  # 屏幕 → 数学 z
        d = (-(X - self.cx) + 1j * -(Y - self.cy)) / self.sc
        return d / self.rot

    def trajectories(self, heights, x0=-7.0, x1=7.0, dt=0.01):
        out = []
        for h in heights:
            zeta = zeta_of(np.array([complex(x0, h) / self.rot]))[0]
            pts = []
            for _ in range(6000):
                z = zeta + 1 / zeta
                d = z * self.rot
                pts.append(z)
                if d.real > x1:
                    break
                f = lambda zt: vel(zt) / (1 - 1 / zt ** 2)
                k1 = f(zeta); k2 = f(zeta + dt / 2 * k1); k3 = f(zeta + dt / 2 * k2); k4 = f(zeta + dt * k3)
                zeta = zeta + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
            out.append((h, np.array(pts), dt))
        return out

    def heatmap(self):
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        X, Y = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
        z = self.inv(X, Y)
        zeta = zeta_of(z)
        inside = np.abs(zeta - MU) < R * 1.002
        sp = np.abs(vel(np.where(inside, 3 + 0j, zeta)))
        cp = np.clip(1 - sp ** 2, -1.6, 1.0)
        a = np.where(cp < 0, np.clip(-cp / 1.3, 0, 1), np.clip(cp / 0.7, 0, 1)) * 0.62
        r = np.where(cp < 0, 0.20, 0.95); g = np.where(cp < 0, 0.45, 0.30); b = np.where(cp < 0, 0.98, 0.25)
        a[inside] = 0
        buf = np.zeros((H, W, 4), np.uint8)  # 预乘 alpha 的 BGRA
        buf[..., 0] = (b * a * 255).astype(np.uint8)
        buf[..., 1] = (g * a * 255).astype(np.uint8)
        buf[..., 2] = (r * a * 255).astype(np.uint8)
        buf[..., 3] = (a * 255).astype(np.uint8)
        stride = surf.get_stride()
        data = surf.get_data()
        arr = np.ndarray((H, stride // 4, 4), np.uint8, data)
        arr[:, :W] = buf
        surf.mark_dirty()
        return surf


def draw_airfoil(c, pts_xy, rgb=(0.85, 0.87, 0.93)):
    c.move_to(*pts_xy[0])
    for p in pts_xy[1:]:
        c.line_to(*p)
    c.close_path()
    fill_stroke(c, rgb, 1, INK, 3)


def airfoil_screen(cx, cy, sc, aoa_deg, mirror=True):
    """翼型屏幕坐标：前缘朝右（mirror），抬头 aoa_deg"""
    z = airfoil_pts() * np.exp(-1j * math.radians(aoa_deg))
    sx = -1 if mirror else 1
    return [(cx + sx * sc * p.real, cy - sc * p.imag) for p in z]


# ---------------------------------------------------------------- 小道具
def elephant(c, x, y, s=1.0):
    c.save(); c.translate(x, y); c.scale(s, s)
    col = (0.60, 0.62, 0.70)
    c.set_source_rgb(*col)
    for lx in (-26, -10, 12, 26):
        c.rectangle(lx - 6, 10, 12, 28); fill_stroke(c, col, 1, INK, 2)
    c.save(); c.scale(42, 28); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore(); fill_stroke(c, col, 1, INK, 2.5)
    c.move_to(52, -2); c.curve_to(64, 6, 62, 22, 66, 34); c.set_line_width(9); c.set_source_rgb(*INK); c.stroke()
    c.move_to(52, -2); c.curve_to(64, 6, 62, 22, 66, 34); c.set_line_width(5); c.set_source_rgb(*col); c.stroke()
    c.arc(42, -12, 20, 0, 2 * math.pi); fill_stroke(c, col, 1, INK, 2.5)
    c.save(); c.translate(32, -10); c.scale(11, 16); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore()
    fill_stroke(c, (0.68, 0.55, 0.62), 1, INK, 2)
    c.arc(50, -18, 2.5, 0, 2 * math.pi); c.set_source_rgb(*INK); c.fill()
    c.restore()


def kid(c, x, y, s=1.0, run=0.0, arm=None, shirt=(0.95, 0.35, 0.35)):
    """简笔小朋友，(x,y) 为脚底，run 为跑步相位"""
    c.save(); c.translate(x, y); c.scale(s, s)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    sw = math.sin(run) * 0.7
    c.set_source_rgb(*INK); c.set_line_width(7)
    for a in (sw, -sw):
        c.move_to(0, -60); c.line_to(math.sin(a) * 34, -60 + math.cos(a) * 30); c.line_to(math.sin(a) * 34 - 6, 0 if a < 0 else -6); c.stroke()
    c.move_to(-14, -110); c.line_to(14, -110); c.line_to(16, -58); c.line_to(-16, -58); c.close_path()
    fill_stroke(c, shirt, 1, INK, 3)
    if arm:
        c.move_to(0, -100); c.line_to(*arm); c.set_line_width(7); c.set_source_rgb(*INK); c.stroke()
    else:
        for a in (-sw, sw):
            c.move_to(0, -100); c.line_to(math.sin(a) * 28, -72); c.set_line_width(7); c.set_source_rgb(*INK); c.stroke()
    c.arc(0, -134, 24, 0, 2 * math.pi); fill_stroke(c, (1.0, 0.85, 0.70), 1, INK, 3)
    c.arc(9, -138, 3, 0, 2 * math.pi); c.set_source_rgb(*INK); c.fill()
    c.arc(4, -126, 7, 0.2, math.pi - 0.2); c.set_line_width(2.5); c.stroke()
    c.restore()


def kite(c, x, y, s=1.0, rot=0.0):
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(s, s)
    c.move_to(0, -50); c.line_to(32, 0); c.line_to(0, 60); c.line_to(-32, 0); c.close_path()
    fill_stroke(c, (0.98, 0.40, 0.45), 1, INK, 3)
    c.move_to(0, -50); c.line_to(0, 60); c.move_to(-32, 0); c.line_to(32, 0)
    c.set_source_rgb(*INK); c.set_line_width(2); c.stroke()
    c.move_to(0, 60)
    for i in range(1, 5):
        c.line_to(math.sin(i * 1.3) * 12, 60 + i * 22)
    c.stroke()
    for i in range(1, 5):
        c.arc(math.sin(i * 1.3) * 12, 60 + i * 22, 5, 0, 2 * math.pi); c.set_source_rgb(*YELLOW); c.fill()
    c.restore()


def wind_lines(c, t, x0, x1, ys, speed=400, rgb=WHITE, alpha=0.8, seg=60, direction=-1):
    """横向风线；direction=-1 表示从右往左吹"""
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_width(4)
    span = x1 - x0
    for i, y in enumerate(ys):
        for j in range(2):
            p = ((t * speed + i * 137 + j * span / 2) % span)
            xx = x1 - p if direction < 0 else x0 + p
            c.set_source_rgba(*rgb, alpha)
            c.move_to(xx, y); c.line_to(xx - direction * seg, y); c.stroke()


def scene_tag(c, s, alpha=1.0):
    if not s:
        return
    w = text_w(c, s, 26) + 34
    rrect(c, 20, 18, w, 46, 23)
    c.set_source_rgba(1, 1, 1, 0.85 * alpha); c.fill()
    text(c, s, 20 + w / 2, 41, 26, DBLUE, alpha=alpha)


# ---------------------------------------------------------------- 字幕
def sub_pages(line, maxc=24):
    """把句子按标点切成不超过 maxc 字的行，再两行一页"""
    parts, cur = [], ""
    for ch in line:
        cur += ch
        if ch in "，。！？：；、":
            parts.append(cur); cur = ""
    if cur:
        parts.append(cur)
    rows, row = [], ""
    for p in parts:
        while len(p) > maxc:
            if row:
                rows.append(row); row = ""
            rows.append(p[:maxc]); p = p[maxc:]
        if len(row) + len(p) > maxc:
            rows.append(row); row = p
        else:
            row += p
    if row:
        rows.append(row)
    pages = [rows[i:i + 2] for i in range(0, len(rows), 2)]
    return [[r.rstrip("，。；、：") if r[-1] in "，。；、：" else r for r in pg] for pg in pages]


def subtitles(c, S, t):
    i = None
    for j in range(len(S.lines)):
        if S.starts[j] - 0.1 <= t <= S.ends[j] + GAP * 0.9:
            i = j
    if i is None:
        return
    pages = sub_pages(S.lines[i])
    counts = [sum(len(r) for r in pg) for pg in pages]
    tot = sum(counts)
    u = (t - S.starts[i]) / S.durs[i] * tot
    acc, pg = 0, pages[-1]
    for p, n in zip(pages, counts):
        acc += n
        if u < acc:
            pg = p
            break
    h = 44 * len(pg) + 20
    y0 = H - 18 - h
    wmax = max(text_w(c, r, 32) for r in pg) + 50
    rrect(c, W / 2 - wmax / 2, y0, wmax, h, 16)
    c.set_source_rgba(0.05, 0.07, 0.15, 0.68); c.fill()
    for k, r in enumerate(pg):
        text(c, r, W / 2, y0 + 32 + k * 44, 32, (1, 1, 1))


# ================================================================= 各场景
def sc_intro(c, S, t):
    sky(c); clouds(c, t)
    # 飞机横穿天空
    px = lerp(-200, W + 200, (t % 9) / 9) if t < 9 else lerp(-200, 640, ease((t - 9) / 3))
    py = 230 + math.sin(t * 1.5) * 10
    if S.k(t) >= 2:
        px, py = lerp(px, 640, S.on(2, t, 1.2)), lerp(py, 330, S.on(2, t, 1.2))
    plane_side(c, px, py, 1.25, 3 + math.sin(t) * 2, flame=1, t=t)
    a1 = S.on(1, t) * (1 - S.on(2, t))
    if a1 > 0:
        for i in range(8):
            ap = ease((t - S.starts[1] - i * 0.25) / 0.4) * (1 - S.on(2, t))
            if ap > 0:
                c.push_group(); elephant(c, 120 + i * 140, 520, 0.9); c.pop_group_to_source(); c.paint_with_alpha(ap)
        label(c, "大客机 ≈ 几十头大象那么重！", 640, 410, 34, WHITE, RED, a1)
    a0 = 1 - S.on(1, t)
    text(c, "飞机为什么能飞上天？", 640, 520, 70, WHITE, alpha=a0, stroke=DBLUE)
    a2 = S.on(2, t)
    text(c, "飞机为什么能飞上天？", 640, 130, 70, WHITE, alpha=a2, stroke=DBLUE)
    label(c, "一起揭开飞行的秘密", 640, 500, 32, INK, YELLOW, a2)


def sc_forces(c, S, t):
    sky(c); clouds(c, t, 60)
    cx, cy = 640, 320
    plane_side(c, cx, cy + math.sin(t * 1.3) * 6, 1.4, 2, flame=1, t=t)
    k = S.k(t)
    big = lambda i: 1 + 0.25 * math.sin(clamp(S.since(i, t) / 0.8) * math.pi) if k == i else 1
    tug = 0.5 + 0.5 * math.sin(t * 3)
    rope = 6 * math.sin(t * 4)
    if S.on(0, t) > 0 and k == 0:
        # 拔河：两个小人
        for sx, col in ((-1, RED), (1, BLUE)):
            kid(c, cx + sx * (380 + rope * sx), 560, 0.9, run=t * 6, arm=(sx * -40, -95), shirt=col)
        c.move_to(cx - 340, 470); c.line_to(cx + 340, 470); c.set_line_width(6); c.set_source_rgb(0.6, 0.4, 0.2); c.stroke()
        c.arc(cx + rope, 470, 12, 0, 2 * math.pi); c.set_source_rgb(*RED); c.fill()
    if S.on(1, t) > 0:
        L = 160 * S.on(1, t) * big(1)
        arrow(c, cx, cy + 50, cx, cy + 50 + L, RED, 20, 40)
        label(c, "重力", cx + 70, cy + 50 + L * 0.7, 30, WHITE, RED, S.on(1, t))
    if S.on(2, t) > 0:
        L = 170 * S.on(2, t) * big(2) * (1 + 0.05 * tug * (k >= 5))
        arrow(c, cx - 10, cy - 30, cx - 10, cy - 30 - L, GREEN, 20, 40)
        label(c, "升力", cx + 60, cy - 30 - L * 0.7, 30, WHITE, GREEN, S.on(2, t))
    if S.on(3, t) > 0:
        L = 200 * S.on(3, t) * big(3)
        arrow(c, cx + 240, cy + 10, cx + 240 + L, cy + 10, ORANGE, 20, 40)
        label(c, "推力", cx + 240 + L * 0.5, cy - 40, 30, WHITE, ORANGE, S.on(3, t))
    if S.on(4, t) > 0:
        L = 160 * S.on(4, t) * big(4)
        arrow(c, cx - 260, cy, cx - 260 - L, cy, PURPLE, 20, 40)
        label(c, "阻力", cx - 260 - L * 0.5, cy - 50, 30, WHITE, PURPLE, S.on(4, t))
        wind_lines(c, t, 0, W, [150, 420, 470], 500, WHITE, 0.6)
    a5 = S.on(5, t)
    if a5 > 0:
        label(c, "升力 > 重力   ⇒  往上升", 340, 610 - 50, 30, WHITE, GREEN, a5)
        label(c, "推力 > 阻力   ⇒  往前冲", 940, 610 - 50, 30, WHITE, ORANGE, a5)


def balloon(c, x, y, s, t, puff):
    c.save(); c.translate(x, y); c.scale(s, s)
    for i in range(7):
        ph = (t * 3 + i / 7) % 1
        c.set_source_rgba(0.85, 0.92, 1.0, (1 - ph) * puff)
        c.arc(-70 - ph * 160, math.sin(i * 1.7 + t * 9) * (10 + ph * 20), 8 + ph * 18, 0, 2 * math.pi); c.fill()
    c.save(); c.scale(70, 55); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore()
    fill_stroke(c, (0.98, 0.35, 0.50), 1, INK, 3)
    c.move_to(-66, -8); c.line_to(-82, -12); c.line_to(-82, 12); c.line_to(-66, 8); c.close_path()
    fill_stroke(c, (0.90, 0.25, 0.40), 1, INK, 2.5)
    c.save(); c.translate(25, -22); c.rotate(-0.5); c.scale(16, 8); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore()
    c.set_source_rgba(1, 1, 1, 0.6); c.fill()
    c.restore()


def engine_cut(c, cx, cy, t, a):
    """喷气发动机剖面：右边进气，左边喷气"""
    if a <= 0:
        return
    c.push_group()
    # 外壳
    for sy in (-1, 1):
        c.move_to(cx + 260, cy + sy * 110); c.curve_to(cx + 120, cy + sy * 128, cx - 120, cy + sy * 110, cx - 260, cy + sy * 70)
        c.line_to(cx - 260, cy + sy * 92); c.curve_to(cx - 120, cy + sy * 135, cx + 120, cy + sy * 150, cx + 270, cy + sy * 128)
        c.close_path()
        fill_stroke(c, (0.75, 0.78, 0.85), 1, INK, 3)
    # 核心机
    c.move_to(cx + 160, cy - 40); c.line_to(cx - 180, cy - 30); c.line_to(cx - 230, cy); c.line_to(cx - 180, cy + 30); c.line_to(cx + 160, cy + 40); c.close_path()
    fill_stroke(c, (0.55, 0.58, 0.66), 1, INK, 2.5)
    # 区域：压气机 / 燃烧室 / 涡轮
    for i in range(7):
        xx = cx + 140 - i * 22
        c.move_to(xx, cy - 38 + i * 1.5); c.line_to(xx, cy - 60 - i * 2 + 30); c.move_to(xx, cy + 38 - i * 1.5); c.line_to(xx, cy + 30 + i * 2 - 0)
    c.set_source_rgb(*INK); c.set_line_width(2); c.stroke()
    fl = 0.6 + 0.4 * math.sin(t * 20)
    for sy in (-1, 1):
        c.save(); c.translate(cx - 50, cy + sy * 70); c.scale(45, 16); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore()
        c.set_source_rgba(1, 0.45 + 0.2 * fl, 0.1, 0.9); c.fill()
    # 风扇（旋转的叶片）
    for i in range(8):
        ph = t * 12 + i * math.pi / 4
        yy = math.sin(ph) * 108
        wdt = abs(math.cos(ph)) * 10 + 2
        c.rectangle(cx + 195 - wdt / 2, cy + yy - 6, wdt, 12)
        c.set_source_rgba(*DBLUE, 0.5 + 0.5 * math.cos(ph) ** 2); c.fill()
    c.rectangle(cx + 192, cy - 112, 6, 224); c.set_source_rgb(*INK); c.fill()
    c.arc(cx + 210, cy, 22, -math.pi / 2, math.pi / 2); fill_stroke(c, (0.3, 0.32, 0.4), 1, INK, 2)
    # 气流粒子：慢慢进来 → 挤紧 → 变热 → 飞快喷出
    rng = np.random.default_rng(3)
    for i in range(70):
        y0 = rng.uniform(-95, 95)
        ph = (t * 0.45 + i / 70) % 1
        # 位置：x 从右到左；速度后段变快
        u = ph ** 1.8
        xx = cx + 420 - u * 860
        squeeze = 1 - 0.55 * ease((cx + 160 - xx) / 200) if xx < cx + 160 else 1
        yy = cy + y0 * squeeze
        hot = ease((cx - 20 - xx) / 80)
        col = (lerp(0.55, 1.0, hot), lerp(0.80, 0.45, hot), lerp(1.0, 0.15, hot))
        c.set_source_rgba(*col, 0.95)
        c.arc(xx, yy, 5, 0, 2 * math.pi); c.fill()
    text(c, "吸进空气", cx + 330, cy - 160, 26, DBLUE, stroke=WHITE)
    text(c, "压紧", cx + 90, cy - 175, 26, INK, stroke=WHITE)
    text(c, "加热", cx - 50, cy - 175, 26, RED, stroke=WHITE)
    text(c, "往后猛喷！", cx - 390, cy - 140, 26, ORANGE, stroke=WHITE)
    c.pop_group_to_source(); c.paint_with_alpha(a)


def sc_thrust(c, S, t):
    sky(c); clouds(c, t, 20)
    k = S.k(t)
    if k <= 1:
        a = 1 - S.on(2, t)
        tt = max(0, S.since(0, t) - 2.5)
        bx = 300 + 600 * (1 - math.exp(-tt * 0.25)) if tt > 0 else 300
        c.push_group()
        balloon(c, bx, 330 + math.sin(t * 7) * 6 * (tt > 0), 1.4, t, 1.0 if tt > 0 else 0)
        if S.on(1, t) > 0:
            arrow(c, bx - 140, 480, bx - 320, 480, BLUE, 16, 34, S.on(1, t))
            text(c, "气球把空气往后喷", bx - 230, 530, 26, DBLUE, alpha=S.on(1, t), stroke=WHITE)
            arrow(c, bx + 40, 480, bx + 220, 480, ORANGE, 16, 34, S.on(1, t))
            text(c, "空气把气球往前推", bx + 130, 530, 26, ORANGE, alpha=S.on(1, t), stroke=WHITE)
        c.pop_group_to_source(); c.paint_with_alpha(a)
    if S.on(2, t) > 0:
        engine_cut(c, 620, 330, t, S.on(2, t))
    if S.on(3, t) > 0:
        a = S.on(3, t)
        arrow(c, 860, 520, 860 + 220 * a, 520, ORANGE, 22, 44)
        label(c, "推力：把飞机往前推", 1000, 575, 28, WHITE, ORANGE, a)
        arrow(c, 380, 520, 380 - 200 * a, 520, BLUE, 16, 36)
        label(c, "空气往后跑", 280, 575, 26, WHITE, BLUE, a)


FLOW = None
FLOW_TRAJ = None
FLOW_HEAT = None


def flow_setup():
    global FLOW, FLOW_TRAJ, FLOW_HEAT
    if FLOW is not None:
        return
    FLOW = Flow(640, 320, 100)
    # 找到“分流线”（正好撞到前缘的那条），再在它上下均匀布线
    foil = airfoil_pts() * FLOW.rot
    mid_y = foil[np.abs(foil.real) < 0.15].imag.mean()  # 翼弦中点附近的翼型高度

    def above(pts):
        d = pts * FLOW.rot
        return d[np.argmin(np.abs(d.real))].imag > mid_y

    lo, hi = -1.5, 1.5
    for _ in range(25):
        mid = (lo + hi) / 2
        if above(FLOW.trajectories([mid], x1=0.5)[0][1]):
            hi = mid
        else:
            lo = mid
    h0 = (lo + hi) / 2
    hs = [h0 + 0.10 + 0.34 * i for i in range(9)] + [h0 - 0.10 - 0.34 * i for i in range(9)]
    FLOW_TRAJ = [(above(p), p, dt) for h, p, dt in FLOW.trajectories(hs)]
    FLOW_HEAT = FLOW.heatmap()


def draw_flow(c, t, dots=1.0, lines=1.0, color=True, speed=1.6):
    for above, pts, dt in FLOW_TRAJ:
        xy = [FLOW.scr(z) for z in pts[::4]]
        if lines > 0:
            c.move_to(*xy[0])
            for p in xy[1:]:
                c.line_to(*p)
            c.set_source_rgba(0.35, 0.45, 0.60, 0.35 * lines); c.set_line_width(2); c.stroke()
        if dots > 0:
            n = len(pts)
            period = 0.40 / dt  # 每 0.3 时间单位放一个点 → 点越稀说明跑得越快
            col = (0.10, 0.30, 0.85) if (above and color) else ((0.90, 0.42, 0.02) if color else (0.35, 0.40, 0.55))
            off = (t * speed / dt) % period
            j = off
            while j < n:
                z = pts[int(j)]
                X, Y = FLOW.scr(z)
                c.new_sub_path()
                c.arc(X, Y, 6, 0, 2 * math.pi)
                j += period
            c.set_source_rgba(*col, dots); c.fill()


def sc_wingshape(c, S, t):
    sky(c); clouds(c, t, 20, 0.6)
    a0 = 1 - S.on(1, t)
    if a0 > 0:
        c.push_group()
        plane_top(c, 640, 350, 1.5, 0)
        cut = S.since(0, t)
        # 红色虚线：沿翼弦方向“切开”机翼
        p = ease((cut - 1.0) / 1.0)
        c.set_dash([14, 10]); c.set_line_width(5); c.set_source_rgb(*RED)
        c.move_to(790, 330)
        c.line_to(790, 330 + 120 * p); c.stroke(); c.set_dash([])
        if p > 0.5:
            label(c, "切开看看！", 900, 200, 30, WHITE, RED, ease((cut - 1.6) / 0.5))
        c.pop_group_to_source(); c.paint_with_alpha(a0)
    a1 = S.on(1, t, 1.0)
    if a1 > 0:
        aoa = 8 * S.on(2, t, 1.5)
        pts = airfoil_screen(640, 330, 115, aoa)
        c.push_group()
        draw_airfoil(c, pts)
        le = max(pts, key=lambda p: p[0]); te = min(pts, key=lambda p: p[0])
        top = min(pts, key=lambda p: p[1])
        k1 = S.since(1, t)
        if k1 > 1.5:
            arrow(c, le[0] + 120, le[1] - 90, le[0] + 18, le[1] - 10, INK, 6, 18, ease((k1 - 1.5) / 0.5))
            label(c, "前面：圆圆胖胖", le[0] + 120, le[1] - 120, 26, WHITE, BLUE, ease((k1 - 1.5) / 0.5))
        if k1 > 3.3:
            arrow(c, te[0] - 60, te[1] + 100, te[0] - 6, te[1] + 10, INK, 6, 18, ease((k1 - 3.3) / 0.5))
            label(c, "后面：又尖又薄", te[0] - 40, te[1] + 130, 26, WHITE, PURPLE, ease((k1 - 3.3) / 0.5))
        if k1 > 5.3:
            arrow(c, top[0], top[1] - 90, top[0], top[1] - 12, INK, 6, 18, ease((k1 - 5.3) / 0.5))
            label(c, "上面：微微鼓起", top[0], top[1] - 115, 26, WHITE, GREEN, ease((k1 - 5.3) / 0.5))
        a2 = S.on(2, t)
        if a2 > 0:
            # 翼弦线和水平线，夹角就是迎角
            c.set_dash([8, 6]); c.set_line_width(3); c.set_source_rgba(*RED, a2)
            c.move_to(te[0] - 30, te[1] + 30 * math.tan(math.radians(aoa)) * 0); c.move_to(*te); c.line_to(le[0] + 80 * math.cos(math.radians(aoa)), le[1] - 80 * math.sin(math.radians(aoa))); c.stroke()
            c.set_source_rgba(*INK, a2); c.move_to(*te); c.line_to(le[0] + 100, te[1]); c.stroke(); c.set_dash([])
            c.arc_negative(te[0], te[1], le[0] + 70 - te[0], 0, -math.radians(aoa)); c.set_line_width(4); c.set_source_rgba(*RED, a2); c.stroke()
            label(c, "迎角", le[0] + 130, te[1] - 30, 30, WHITE, RED, a2)
            wind_lines(c, t, 0, W, [140, 190, 470, 520], 450, BLUE, 0.7 * a2)
            label(c, "← 风迎面吹来", 1050, 590, 26, WHITE, BLUE, a2)
        c.pop_group_to_source(); c.paint_with_alpha(a1)


def sc_airflow(c, S, t):
    flow_setup()
    sky(c, (0.86, 0.93, 0.99), (0.95, 0.97, 1.0))
    k = S.k(t)
    heat = S.on(1, t, 1.2) * (1 - 0.5 * S.on(4, t))
    if heat > 0:
        c.set_source_surface(FLOW_HEAT, 0, 0); c.paint_with_alpha(heat)
    draw_flow(c, t, dots=S.on(0, t), lines=S.on(0, t), color=S.on(1, t) > 0.01)
    draw_airfoil(c, airfoil_screen(640, 320, 100, 8))
    if k >= 1:
        a = S.on(1, t)
        label(c, "上面：跑得快，气压小", 640, 70, 30, WHITE, BLUE, a)
    if k >= 2:
        a = S.on(2, t)
        label(c, "下面：跑得慢，气压大", 640, 560, 30, WHITE, RED, a)
        for i, x in enumerate((520, 640, 760)):
            bob = math.sin(t * 5 + i) * 6
            arrow(c, x, 470 + bob, x, 400 + bob, RED, 12, 26, a)
    if k >= 3:
        a = S.on(3, t)
        L = 180 * a * (1 + 0.06 * math.sin(t * 4))
        arrow(c, 655, 300, 655, 300 - L, GREEN, 26, 50)
        label(c, "升力！", 760, 300 - L * 0.8, 36, WHITE, GREEN, a)
    if k >= 4:
        a = S.on(4, t)
        for i, (x, y) in enumerate(((330, 360), (260, 420), (390, 440))):
            p = (t * 0.8 + i * 0.33) % 1
            arrow(c, x + 40 - p * 30, y - 40 + p * 30, x - 40 - p * 30, y + 40 + p * 30, (0.35, 0.85, 1.0), 12, 26, a * (1 - p * 0.5))
        label(c, "空气被往下推", 300, 520, 28, WHITE, DBLUE, a)
        # 小插图：游泳划水
        sw = 1 - S.on(4, t, 0.6) * 0 if True else 0
        if S.since(4, t) > 6:
            b = ease((S.since(4, t) - 6) / 0.6)
            c.push_group()
            rrect(c, 900, 380, 330, 200, 20); c.set_source_rgba(0.85, 0.95, 1.0, 0.95); c.fill()
            c.rectangle(900, 450, 330, 130); c.set_source_rgba(0.30, 0.65, 0.95, 0.6); c.fill()
            ph = t * 3
            hx = 1060 + math.cos(ph) * 50; hy = 470 + abs(math.sin(ph)) * 50
            c.save(); c.translate(1020, 450); c.scale(60, 16); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore(); fill_stroke(c, (0.95, 0.35, 0.35), 1, INK, 2.5)
            c.arc(1095, 440, 18, 0, 2 * math.pi); fill_stroke(c, (1, 0.85, 0.7), 1, INK, 2.5)
            c.move_to(1050, 450); c.line_to(hx, hy); c.set_source_rgb(*INK); c.set_line_width(6); c.stroke()
            arrow(c, 990, 500, 990, 560, (0.1, 0.3, 0.8), 10, 22)
            arrow(c, 1150, 470, 1150, 410, GREEN, 10, 22)
            text(c, "手往下划水", 990, 400, 22, DBLUE)
            text(c, "身体往上浮", 1150, 395, 22, GREEN)
            c.pop_group_to_source(); c.paint_with_alpha(b)


def sc_experiment(c, S, t):
    sky(c, (0.98, 0.93, 0.80), (0.99, 0.97, 0.90))
    a01 = 1 - S.on(2, t)
    if a01 > 0:
        c.push_group()
        hx, hy = 330, 300
        # 头（侧脸，朝右）
        c.arc(hx, hy, 120, 0, 2 * math.pi); fill_stroke(c, (1.0, 0.85, 0.70), 1, INK, 4)
        c.move_to(hx - 120, hy - 20); c.curve_to(hx - 130, hy - 170, hx + 90, hy - 190, hx + 110, hy - 60)
        c.curve_to(hx + 40, hy - 110, hx - 60, hy - 100, hx - 120, hy - 20); fill_stroke(c, (0.25, 0.18, 0.12), 1, INK, 3)
        c.arc(hx + 60, hy - 25, 9, 0, 2 * math.pi); c.set_source_rgb(*INK); c.fill()
        c.move_to(hx + 118, hy - 10); c.line_to(hx + 140, hy + 20); c.line_to(hx + 116, hy + 25); fill_stroke(c, (1.0, 0.85, 0.70), 1, INK, 3)
        blowing = S.since(1, t) > 0.3
        mx, my = hx + 112, hy + 60
        if blowing:
            c.arc(mx + 4, my, 9, 0, 2 * math.pi); fill_stroke(c, (0.85, 0.3, 0.3), 1, INK, 3)
        else:
            c.move_to(mx - 14, my); c.line_to(mx + 6, my); c.set_line_width(4); c.set_source_rgb(*INK); c.stroke()
        # 纸条：不吹时下垂，吹气时飘起来
        lift = ease((S.since(1, t) - 0.6) / 1.2) if blowing else 0
        flap = math.sin(t * 18) * 0.06 * lift
        droop = lerp(1.25, 0.12, lift) + flap
        L = 300
        x0, y0 = mx + 4, my + 14
        c.move_to(x0, y0)
        pts = []
        for i in range(1, 21):
            s_ = i / 20
            ang = droop * s_ ** 1.2
            pts.append((ang, s_))
        x, y = x0, y0
        poly = [(x, y)]
        for ang, s_ in pts:
            x += math.cos(ang) * L / 20; y += math.sin(ang) * L / 20
            poly.append((x, y))
        c.move_to(*poly[0])
        for p in poly[1:]:
            c.line_to(*p)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.set_source_rgb(*INK); c.set_line_width(14); c.stroke_preserve()
        c.set_source_rgb(1, 1, 1); c.set_line_width(9); c.stroke()
        text(c, "纸条", poly[-1][0] + 40, poly[-1][1] + 10, 26, INK)
        if blowing:
            for i in range(4):
                ph = (t * 1.5 + i / 4) % 1
                xx = x0 + 10 + ph * 330
                c.set_source_rgba(*BLUE, 1 - ph)
                c.move_to(xx, y0 - 22 - i % 2 * 12); c.line_to(xx + 50, y0 - 22 - i % 2 * 12 + 2); c.set_line_width(5); c.stroke()
            a = ease((S.since(1, t) - 2) / 0.6)
            label(c, "上面：空气跑得快，气压小", 900, 160, 28, WHITE, BLUE, a)
            arrow(c, 700, 500, 700, 420, GREEN, 18, 36, a)
            label(c, "下面的空气把纸条托起来", 900, 540, 28, WHITE, GREEN, a)
        else:
            label(c, "对着纸条上面吹气", 900, 160, 28, WHITE, INK, S.on(0, t))
            text(c, "?", 870, 400, 120, ORANGE, alpha=S.on(0, t) * (0.6 + 0.4 * math.sin(t * 4)))
        c.pop_group_to_source(); c.paint_with_alpha(a01)
    a2 = S.on(2, t)
    if a2 > 0:
        c.push_group()
        sky(c)
        ground(c, 520)
        for i in range(8):
            gx = (i * 200 - t * 220) % (W + 200) - 100
            c.move_to(gx, 520); c.line_to(gx + 10, 500); c.line_to(gx + 20, 520); c.set_source_rgb(0.3, 0.6, 0.3); c.fill()
        kx = 560
        kid(c, kx, 540, 1.3, run=t * 9, arm=(40, -80))
        # 纸板（前边抬高）
        c.save(); c.translate(kx + 75, 410 + math.sin(t * 9) * 3); c.rotate(-0.25)
        c.rectangle(-70, -6, 140, 12); fill_stroke(c, (0.80, 0.60, 0.35), 1, INK, 3)
        c.restore()
        wind_lines(c, t, 0, W, [300, 360, 450, 160], 600, WHITE, 0.9)
        arrow(c, kx + 75, 390, kx + 75, 250 + math.sin(t * 6) * 8, GREEN, 18, 36)
        label(c, "纸板被往上托！", kx + 75, 220, 30, WHITE, GREEN, ease((S.since(2, t) - 4) / 0.5))
        label(c, "前边稍微抬高", kx + 300, 400, 26, WHITE, INK, ease((S.since(2, t) - 1.5) / 0.5))
        c.pop_group_to_source(); c.paint_with_alpha(a2)


def sc_takeoff(c, S, t):
    k = S.k(t)
    s0, s2 = S.starts[0], S.starts[2]
    # 速度：从 0 加速到 280 公里/小时
    v = 280 * ease((t - s0) / (s2 + 3 - s0)) ** 0.8
    lift_off = s2 + 3.0
    alt = max(0.0, t - lift_off)
    pitch = 9 * ease((t - (lift_off - 1.2)) / 1.0)
    climb = 1 - math.exp(-alt * 0.6)
    a3 = S.on(3, t)
    if a3 < 1:
        c.push_group()
        sky(c); clouds(c, t, 10 + v * 0.3)
        gy = 440 + climb * 300
        ground(c, gy, (0.50, 0.75, 0.38))
        c.rectangle(0, gy + 10, W, 60); c.set_source_rgb(0.32, 0.33, 0.36); c.fill()
        dist = 0.0
        # 近似积分：位移
        n = 40
        for i in range(n):
            tt = s0 + (t - s0) * (i + 0.5) / n
            dist += 280 * ease((tt - s0) / (s2 + 3 - s0)) ** 0.8 * (t - s0) / n
        for i in range(12):
            mx = (i * 150 - dist * 3.0) % (W + 150) - 75
            c.rectangle(mx, gy + 36, 70, 8); c.set_source_rgb(1, 1, 1); c.fill()
        px, py = 520, 400 - climb * 120
        plane_side(c, px, py, 1.3, pitch, flame=0.3 + v / 280, t=t, gear=True)
        wind_lines(c, t, 0, W, [200, 260, 330], 100 + v * 4, WHITE, clamp(v / 100) * 0.7)
        L = min(180, 170 * (v / 250) ** 2)
        Wt = 150
        arrow(c, px, py - 10, px, py - 10 - L, GREEN, 20, 40)
        arrow(c, px + 30, py + 20, px + 30, py + 20 + Wt * 0.75, RED, 20, 40)
        label(c, "升力", px - 70, py - 10 - L * 0.6, 26, WHITE, GREEN, clamp(L / 40))
        label(c, "重力", px + 100, py + 20 + Wt * 0.6, 26, WHITE, RED)
        # 速度表
        rrect(c, 930, 90, 320, 110, 20); c.set_source_rgba(1, 1, 1, 0.9); c.fill()
        text(c, "速度", 1000, 145, 30, INK)
        text(c, f"{int(v)}", 1120, 140, 54, ORANGE)
        text(c, "公里/小时", 1120, 182, 20, INK)
        c.rectangle(950, 210, 280, 14); c.set_source_rgb(0.85, 0.85, 0.9); c.fill()
        c.rectangle(950, 210, 280 * v / 280, 14); c.set_source_rgb(*ORANGE); c.fill()
        if k == 1 and S.since(1, t) > 4:
            label(c, "汽车：120 公里/小时", 1090, 260, 22, WHITE, INK, ease((S.since(1, t) - 4) / 0.5))
        if t > lift_off - 1.6:
            label(c, "升力 > 重力，起飞！", 960, 440, 36, WHITE, GREEN, ease((t - lift_off + 1.6) / 0.5))
        c.pop_group_to_source(); c.paint_with_alpha(1 - a3)
    if a3 > 0:
        c.push_group()
        sky(c); clouds(c, t, 40)
        ground(c, 560)
        kx = 980 + math.sin(t * 2) * 10
        kid(c, kx, 590, 1.1, run=t * 9, arm=(-40, -110))
        u = ease(S.since(3, t) / 5)
        kxx, kyy = 330 - u * 60, 420 - u * 250
        c.move_to(kx - 44, 590 - 121); c.curve_to(kx - 200, 400, kxx + 80, kyy + 160, kxx, kyy + 20)
        c.set_source_rgb(*INK); c.set_line_width(2); c.stroke()
        kite(c, kxx, kyy, 1.2, -0.4 + math.sin(t * 3) * 0.08)
        wind_lines(c, t, 0, W, [140, 220, 300, 380], 500, WHITE, 0.8)
        arrow(c, kxx + 70, kyy, kxx + 70, kyy - 110, GREEN, 14, 30, ease(S.since(3, t) / 1.5))
        label(c, "风越大 → 升力越大", 640, 120, 30, WHITE, GREEN, ease((S.since(3, t) - 2) / 0.5))
        c.pop_group_to_source(); c.paint_with_alpha(a3)


def blink(t, base, hi):
    u = 0.5 + 0.5 * math.sin(t * 6)
    return tuple(lerp(b, h, u) for b, h in zip(base, hi))


def sc_control(c, S, t):
    sky(c); clouds(c, t, 30)
    k = S.k(t)
    fade = lambda i: S.on(i, t) * (1 - S.on(i + 1, t) if i + 1 < len(S.lines) else 1)
    a = fade(0)
    if a > 0:
        c.push_group()
        hl = {"aileron": blink(t, (0.95, 0.75, 0.2), (1, 0.4, 0.1)), "elevator": blink(t, (0.3, 0.8, 0.4), (0.1, 0.6, 0.2)),
              "rudder": blink(t, (0.9, 0.3, 0.6), (0.7, 0.1, 0.4))}
        plane_top(c, 640, 300, 1.3, 0, hl=hl)
        label(c, "副翼", 360, 400, 28, WHITE, ORANGE); label(c, "副翼", 920, 400, 28, WHITE, ORANGE)
        label(c, "升降舵", 470, 560, 28, WHITE, GREEN); label(c, "方向舵", 800, 560, 28, WHITE, (0.8, 0.2, 0.5))
        c.pop_group_to_source(); c.paint_with_alpha(a)
    a = fade(1)
    if a > 0:
        c.push_group()
        u = S.since(1, t)
        e = 18 * math.sin(clamp((u - 0.5) / 7.5) * 2 * math.pi)  # 先上翘再下压
        ang = 0
        # 机头角度跟着升降舵慢慢变
        ang = 12 * math.sin(clamp((u - 0.9) / 7.5) * 2 * math.pi)
        plane_side(c, 640, 330, 1.7, ang, elev=e, hl={"elevator": (0.3, 0.8, 0.4)}, flame=1, t=t)
        up = e > 2
        dn = e < -2
        if up:
            label(c, "升降舵往上翘 → 机头抬起来", 640, 120, 32, WHITE, GREEN)
        elif dn:
            label(c, "升降舵往下压 → 机头低下去", 640, 120, 32, WHITE, ORANGE)
        c.pop_group_to_source(); c.paint_with_alpha(a)
    a = fade(2)
    if a > 0:
        c.push_group()
        u = S.since(2, t)
        r = 22 * math.sin(clamp((u - 0.5) / 6) * 2 * math.pi)
        yaw = 20 * math.sin(clamp((u - 1.0) / 6) * 2 * math.pi)  # 机头稍晚一点跟着方向舵转
        plane_top(c, 640, 330, 1.2, yaw, rudder=r, hl={"rudder": (0.9, 0.3, 0.6)})
        if r > 3:
            label(c, "方向舵偏右 → 机头往右转", 640, 70, 30, WHITE, (0.8, 0.2, 0.5))
        elif r < -3:
            label(c, "方向舵偏左 → 机头往左转", 640, 70, 30, WHITE, (0.8, 0.2, 0.5))
        # 小船舵插图
        c.save(); c.translate(1110, 470)
        c.move_to(-40, -60); c.curve_to(-50, 20, -20, 60, 0, 60); c.curve_to(20, 60, 50, 20, 40, -60); c.close_path()
        fill_stroke(c, (0.75, 0.50, 0.30), 1, INK, 3)
        c.translate(0, 60); c.rotate(-math.radians(r))
        c.rectangle(-4, 0, 8, 34); fill_stroke(c, (0.9, 0.3, 0.6), 1, INK, 2)
        c.restore()
        text(c, "船舵", 1110, 380, 24, INK, stroke=WHITE)
        c.pop_group_to_source(); c.paint_with_alpha(a)
    a = fade(3)
    if a > 0:
        c.push_group()
        u = S.since(3, t)
        ail = math.sin(clamp((u - 0.8) / 8) * 2 * math.pi)
        roll = 25 * math.sin(clamp((u - 1.3) / 8) * 2 * math.pi)
        plane_front(c, 640, 320, 1.6, roll, ail)
        if abs(ail) > 0.15:
            label(c, "一边翘起，一边压下 → 飞机侧身转弯", 640, 80, 30, WHITE, ORANGE)
            side = 1 if ail > 0 else -1  # 副翼下偏的一侧升力变大，抬起来
            arrow(c, 640 - side * 330, 400, 640 - side * 330, 300, GREEN, 14, 30)
            arrow(c, 640 + side * 330, 260, 640 + side * 330, 360, RED, 14, 30)
        # 自行车拐弯小插图
        if u > 6:
            b = ease((u - 6) / 0.6)
            c.save(); c.translate(1120, 540); c.rotate(-0.35 * math.sin(t * 1.5))
            c.push_group()
            c.set_source_rgb(*INK); c.set_line_width(5)
            for wx in (-40, 40):
                c.arc(wx, 0, 26, 0, 2 * math.pi); c.stroke()
            c.move_to(-40, 0); c.line_to(0, -40); c.line_to(40, 0); c.move_to(0, -40); c.line_to(-10, -70); c.stroke()
            c.arc(-10, -95, 16, 0, 2 * math.pi); fill_stroke(c, (1, 0.85, 0.7), 1, INK, 2.5)
            c.pop_group_to_source(); c.paint_with_alpha(b)
            c.restore()
        c.pop_group_to_source(); c.paint_with_alpha(a)


def bird(c, x, y, s, t):
    c.save(); c.translate(x, y); c.scale(s, s)
    f = math.sin(t * 6)
    col = (0.35, 0.60, 0.95)
    # 远侧翅膀
    c.move_to(-10, -5); c.curve_to(-30, -60 * f - 20, -80, -90 * f - 10, -120, -110 * f); c.curve_to(-60, -40 * f, -30, 0, 10, 0); c.close_path()
    fill_stroke(c, (0.25, 0.45, 0.80), 1, INK, 2.5)
    c.save(); c.scale(70, 30); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore(); fill_stroke(c, col, 1, INK, 3)
    c.move_to(-60, -5); c.line_to(-110, -25); c.line_to(-105, 15); c.close_path(); fill_stroke(c, col, 1, INK, 2.5)
    c.arc(70, -20, 24, 0, 2 * math.pi); fill_stroke(c, col, 1, INK, 3)
    c.move_to(90, -25); c.line_to(120, -15); c.line_to(90, -8); c.close_path(); fill_stroke(c, YELLOW, 1, INK, 2.5)
    c.arc(76, -26, 4, 0, 2 * math.pi); c.set_source_rgb(*INK); c.fill()
    c.move_to(10, -5); c.curve_to(0, -60 * f - 30, -40, -100 * f - 20, -70, -120 * f - 10); c.curve_to(-30, -40 * f, -20, 0, 30, 5); c.close_path()
    fill_stroke(c, (0.55, 0.75, 1.0), 1, INK, 2.5)
    c.restore()


def helicopter(c, x, y, s, t):
    c.save(); c.translate(x, y); c.scale(s, s)
    c.move_to(-60, -10); c.line_to(-200, -20); c.line_to(-200, 0); c.line_to(-60, 15); c.close_path()
    fill_stroke(c, (0.95, 0.75, 0.20), 1, INK, 3)
    for i in range(2):
        ph = t * 25 + i * math.pi / 2
        c.save(); c.translate(-200, -10); c.rotate(ph); c.rectangle(-30, -3, 60, 6); c.restore(); fill_stroke(c, GRAY, 1, INK, 1.5)
    c.save(); c.scale(95, 55); c.arc(0, 0, 1, 0, 2 * math.pi); c.restore(); fill_stroke(c, (0.95, 0.75, 0.20), 1, INK, 3)
    c.move_to(20, -45); c.curve_to(70, -45, 95, -10, 92, 10); c.line_to(20, 10); c.close_path(); fill_stroke(c, (0.6, 0.85, 1.0), 1, INK, 2.5)
    c.set_source_rgb(*INK); c.set_line_width(5)
    c.move_to(-60, 55); c.line_to(-60, 75); c.move_to(50, 50); c.line_to(50, 75); c.move_to(-100, 75); c.line_to(90, 75); c.stroke()
    c.rectangle(-6, -80, 12, 30); fill_stroke(c, GRAY, 1, INK, 2)
    for i in range(2):
        L = 260 * math.cos(t * 14 + i * math.pi / 2)
        c.move_to(0, -82); c.line_to(L, -82 - 4 * math.sin(t * 14 + i)); c.set_line_width(10); c.set_source_rgb(*INK); c.stroke()
        c.move_to(0, -82); c.line_to(L, -82 - 4 * math.sin(t * 14 + i)); c.set_line_width(6); c.set_source_rgb(0.4, 0.42, 0.5); c.stroke()
    c.restore()


def bamboo(c, x, y, s, t):
    c.save(); c.translate(x, y); c.scale(s, s)
    c.rectangle(-4, 0, 8, 110); fill_stroke(c, (0.75, 0.60, 0.35), 1, INK, 2)
    L = 80 * math.cos(t * 16)
    c.move_to(-L, 4); c.line_to(L, -4); c.set_line_width(14); c.set_source_rgb(*INK); c.stroke()
    c.move_to(-L, 4); c.line_to(L, -4); c.set_line_width(9); c.set_source_rgb(0.4, 0.8, 0.45); c.stroke()
    c.restore()


def racecar(c, x, y, s, t):
    c.save(); c.translate(x, y); c.scale(s, s)
    # 尾翼（倒装的机翼）
    c.set_source_rgb(*INK); c.set_line_width(6)
    c.move_to(-175, -30); c.line_to(-175, -100); c.move_to(-125, -30); c.line_to(-135, -100); c.stroke()
    z = airfoil_pts()
    pts = [(-150 - 30 * p.real, -108 + 30 * p.imag) for p in z]  # 前缘朝前，上下翻转 → 拱面朝下
    draw_airfoil(c, pts, (0.95, 0.30, 0.30))
    c.move_to(-200, 0); c.line_to(-190, -40); c.line_to(-60, -45); c.line_to(0, -80); c.line_to(80, -80); c.line_to(130, -40)
    c.line_to(220, -25); c.line_to(230, 0); c.close_path(); fill_stroke(c, (0.90, 0.20, 0.20), 1, INK, 3)
    c.move_to(10, -75); c.line_to(70, -75); c.line_to(105, -45); c.line_to(10, -45); c.close_path(); fill_stroke(c, (0.6, 0.85, 1.0), 1, INK, 2.5)
    for wx in (-130, 150):
        c.arc(wx, 0, 36, 0, 2 * math.pi); fill_stroke(c, (0.15, 0.15, 0.18), 1, INK, 3)
        c.arc(wx, 0, 16, 0, 2 * math.pi); fill_stroke(c, GRAY, 1, None)
        for i in range(3):
            a = -t * 20 + i * 2.09
            c.move_to(wx, 0); c.line_to(wx + 16 * math.cos(a), 16 * math.sin(a))
        c.set_source_rgb(*INK); c.set_line_width(3); c.stroke()
    c.restore()


def sailboat(c, x, y, s, t):
    c.save(); c.translate(x, y + math.sin(t * 2) * 5); c.scale(s, s)
    c.move_to(-150, 0); c.line_to(150, 0); c.line_to(110, 50); c.line_to(-120, 50); c.close_path(); fill_stroke(c, (0.75, 0.45, 0.25), 1, INK, 3)
    c.rectangle(-4, -260, 8, 260); fill_stroke(c, (0.5, 0.35, 0.2), 1, INK, 2)
    c.move_to(0, -250); c.curve_to(120, -180, 140, -60, 0, -15); c.close_path(); fill_stroke(c, WHITE, 1, INK, 3)
    c.move_to(-10, -230); c.curve_to(-60, -150, -90, -50, -110, -15); c.line_to(-10, -15); c.close_path(); fill_stroke(c, (0.95, 0.95, 0.85), 1, INK, 3)
    c.restore()


def sc_analogies(c, S, t):
    sky(c); clouds(c, t, 25)
    fade = lambda i: S.on(i, t) * (1 - S.on(i + 1, t) if i + 1 < len(S.lines) else 1)
    a = fade(0)
    if a > 0:
        c.push_group()
        text(c, "举一反三", 640, 140, 72, WHITE, stroke=DBLUE)
        items = [("小鸟", lambda: bird(c, 250, 380, 0.7, t)), ("直升机", lambda: helicopter(c, 520, 400, 0.5, t)),
                 ("赛车", lambda: racecar(c, 800, 410, 0.45, t)), ("帆船", lambda: sailboat(c, 1060, 450, 0.55, t))]
        for i, (name, fn) in enumerate(items):
            b = ease((S.since(0, t) - 0.4 - i * 0.5) / 0.5)
            c.push_group(); fn(); c.pop_group_to_source(); c.paint_with_alpha(b)
            label(c, name, 250 + i * 270, 540, 28, WHITE, DBLUE, b)
        c.pop_group_to_source(); c.paint_with_alpha(a)
    a = fade(1)
    if a > 0:
        c.push_group()
        bird(c, 480, 360 + math.sin(t * 6) * 10, 1.6, t)
        rrect(c, 840, 180, 380, 240, 20); c.set_source_rgba(1, 1, 1, 0.85); c.fill()
        draw_airfoil(c, airfoil_screen(1030, 300, 70, 6))
        text(c, "翅膀切面也像机翼", 1030, 220, 26, INK)
        text(c, "上面鼓  下面凹", 1030, 385, 24, DBLUE)
        label(c, "翅膀 = 天生的机翼", 640, 90, 34, WHITE, BLUE)
        c.pop_group_to_source(); c.paint_with_alpha(a)
    a = fade(2)
    if a > 0:
        c.push_group()
        helicopter(c, 520, 330, 1.2, t)
        for i in range(5):
            p = (t * 1.2 + i * 0.2) % 1
            arrow(c, 250 + i * 135, 300 + p * 120, 250 + i * 135, 360 + p * 120, (0.35, 0.80, 1.0), 10, 22, 1 - p)
        arrow(c, 520, 180, 520, 70, GREEN, 18, 36)
        label(c, "转圈的机翼把空气往下推", 520, 610 - 40, 28, WHITE, DBLUE)
        rrect(c, 960, 160, 270, 380, 20); c.set_source_rgba(1, 1, 1, 0.85); c.fill()
        bamboo(c, 1095, 330 - 60 * ease(((t - S.starts[2]) % 4) / 2) + 60 * ease(((t - S.starts[2]) % 4 - 2) / 2), 1.0, t)
        text(c, "竹蜻蜓", 1095, 510, 28, INK)
        c.pop_group_to_source(); c.paint_with_alpha(a)
    a = fade(3)
    if a > 0:
        c.push_group()
        ground(c, 470, (0.4, 0.42, 0.46))
        for i in range(6):
            mx = (i * 260 - t * 900) % (W + 260) - 130
            c.rectangle(mx, 520, 130, 10); c.set_source_rgb(1, 1, 1); c.fill()
        racecar(c, 640, 434, 1.6, t)
        wind_lines(c, t, 0, W, [170, 210, 300], 900, WHITE, 0.8)
        arrow(c, 400, 150, 400, 240, RED, 18, 36)
        label(c, "倒过来的机翼：往下压", 640, 100, 32, WHITE, RED)
        label(c, "贴紧地面，拐弯不打滑", 900, 220, 28, WHITE, INK)
        c.pop_group_to_source(); c.paint_with_alpha(a)
    a = fade(4)
    if a > 0:
        c.push_group()
        c.rectangle(0, 470, W, 250); c.set_source_rgb(0.25, 0.55, 0.85); c.fill()
        for i in range(10):
            wx = (i * 160 - t * 40) % (W + 160) - 80
            c.arc(wx, 480, 30, math.pi, 2 * math.pi); c.set_source_rgba(1, 1, 1, 0.5); c.set_line_width(4); c.stroke()
        sailboat(c, 640, 460, 1.2, t)
        wind_lines(c, t, 0, 600, [200, 260, 330, 400], 400, WHITE, 0.9, direction=1)
        label(c, "风 →", 140, 150, 28, WHITE, DBLUE)
        arrow(c, 830, 380, 1030, 380, ORANGE, 20, 40)
        label(c, "竖着的机翼：把船往前拉", 960, 300, 28, WHITE, ORANGE)
        c.pop_group_to_source(); c.paint_with_alpha(a)


def card(c, x, y, w, h, title, body, col, a, icon=None):
    if a <= 0:
        return
    c.push_group()
    rrect(c, x, y, w, h, 24); c.set_source_rgba(1, 1, 1, 0.92); c.fill_preserve()
    c.set_source_rgb(*col); c.set_line_width(5); c.stroke()
    text(c, title, x + w / 2, y + 45, 34, col)
    for i, b in enumerate(body):
        text(c, b, x + w / 2, y + 100 + i * 40, 26, INK)
    c.pop_group_to_source(); c.paint_with_alpha(a)


def sc_summary(c, S, t):
    sky(c); clouds(c, t, 25)
    fade = lambda i: S.on(i, t) * (1 - S.on(i + 1, t) if i + 1 < len(S.lines) else 1)
    a = S.on(0, t) * (1 - S.on(2, t))
    if a > 0:
        c.push_group()
        text(c, "飞行的秘密", 640, 100, 56, WHITE, stroke=DBLUE)
        card(c, 90, 170, 340, 260, "推力", ["发动机", "把空气往后推"], ORANGE, ease(S.since(0, t) / 0.6))
        card(c, 470, 170, 340, 260, "升力", ["机翼让上面空气跑得快", "还把空气往下推"], GREEN, ease((S.since(0, t) - 4) / 0.6))
        card(c, 850, 170, 340, 260, "四个力", ["升力托住重力", "推力赢过阻力"], BLUE, S.on(1, t))
        c.pop_group_to_source(); c.paint_with_alpha(a)
    a = S.on(2, t)
    if a > 0:
        c.push_group()
        rrect(c, 140, 120, 1000, 380, 30); c.set_source_rgba(1, 1, 1, 0.94); c.fill()
        c.arc(260, 300, 70, 0, 2 * math.pi); c.set_source_rgb(*ORANGE); c.fill()
        text(c, "?", 260, 300, 100, WHITE)
        text(c, "思考题", 700, 190, 40, ORANGE)
        text(c, "为什么飞机都喜欢", 700, 270, 44, INK)
        text(c, "迎着风起飞呢？", 700, 335, 44, INK)
        hint = S.on(3, t)
        if hint > 0:
            kite(c, 1040, 300 + math.sin(t * 3) * 8, 0.8, -0.3)
            text(c, "提示：想想风筝！", 700, 430, 32, GREEN, alpha=hint)
        c.pop_group_to_source(); c.paint_with_alpha(a)
        if S.since(3, t) > 3:
            u = ease((S.since(3, t) - 3) / 3)
            plane_side(c, lerp(-150, 1450, u), 600 - u * 120, 0.8, 8, flame=1, t=t)


DRAW = {"intro": sc_intro, "forces": sc_forces, "thrust": sc_thrust, "wingshape": sc_wingshape, "airflow": sc_airflow,
        "experiment": sc_experiment, "takeoff": sc_takeoff, "control": sc_control, "analogies": sc_analogies,
        "summary": sc_summary}


def load_scenes():
    timing = json.load(open(f"{BUILD}/timing.json"))
    return [Scene(k, title, lines, timing[k]) for k, title, lines in SCENES]


def render_frame(S, t):
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    c = cairo.Context(surf)
    DRAW[S.key](c, S, t)
    if S.key != "intro":
        scene_tag(c, S.title)
    subtitles(c, S, t)
    # 场景首尾淡入淡出
    f = min(clamp(t / 0.35), clamp((S.dur - t) / 0.35))
    if f < 1:
        c.set_source_rgba(1, 1, 1, 1 - f); c.paint()
    surf.flush()
    return surf


def render_scene(idx):
    S = load_scenes()[idx]
    out = f"{BUILD}/scene_{idx:02d}.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                          "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for f in range(S.nframes):
        surf = render_frame(S, f / FPS)
        p.stdin.write(bytes(surf.get_data()))
    p.stdin.close(); p.wait()
    print("done", S.key, S.nframes, flush=True)
    return out


def build_audio(scenes):
    sr = 24000
    total = sum(S.nframes for S in scenes) / FPS
    track = np.zeros(int(total * sr) + sr, np.float32)
    off = 0.0
    for S in scenes:
        for i in range(len(S.lines)):
            raw = subprocess.check_output(["ffmpeg", "-loglevel", "error", "-i", f"{BUILD}/audio/{S.key}_{i}.mp3",
                                           "-f", "s16le", "-ac", "1", "-ar", str(sr), "-"])
            a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
            s0 = int((off + S.starts[i]) * sr)
            track[s0:s0 + len(a)] += a[:len(track) - s0]
        off += S.nframes / FPS
    pcm = (np.clip(track, -1, 1) * 32767).astype(np.int16).tobytes()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(sr), "-ac", "1", "-i", "-",
                    f"{BUILD}/narration.wav"], input=pcm, check=True)


def main():
    scenes = load_scenes()
    if len(sys.argv) > 2 and sys.argv[1] == "--still":
        # 预览：--still <场景key> <秒>
        S = next(s for s in scenes if s.key == sys.argv[2])
        render_frame(S, float(sys.argv[3])).write_to_png(sys.argv[4] if len(sys.argv) > 4 else f"{BUILD}/still.png")
        return
    only = [int(x) for x in sys.argv[1:]] or list(range(len(scenes)))
    with Pool(4) as pool:
        pool.map(render_scene, only)
    build_audio(scenes)
    with open(f"{BUILD}/list.txt", "w") as f:
        for i in range(len(scenes)):
            f.write(f"file 'scene_{i:02d}.mp4'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{BUILD}/list.txt",
                    "-i", f"{BUILD}/narration.wav", "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
                    "-shortest",
                    "-movflags", "+faststart", f"{BUILD}/how-planes-fly.mp4"], check=True)
    print("total", sum(S.nframes for S in scenes) / FPS, "s")


if __name__ == "__main__":
    main()
