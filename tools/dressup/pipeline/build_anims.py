"""Add animations to the generated rig. Spine rotation: degrees, counter-clockwise positive (y up).
Image-left arm/leg = '_A' (raising it outward = negative), image-right = '_B' (outward = positive)."""
import json, math
R = json.load(open('../spine/rig_base.json')); skel = R['skel']
ease = lambda t: t*t*(3-2*t)
def tri(t, T):                       # 0 -> 1 -> 0 over period T, smooth
    return ease(1 - abs((t % T)/T*2 - 1))
def osc(t, T): return math.sin(t/T*2*math.pi)
def hold(t, a, b, c, d):            # 0 before a, ramp to 1 by b, hold, ramp back to 0 from c to d
    if t <= a or t >= d: return 0.
    if t < b: return ease((t-a)/(b-a))
    if t <= c: return 1.
    return ease(1 - (t-c)/(d-c))
A = {}   # name -> (duration, fn(t) -> {bone: {'r':deg,'x':,'y':,'sx':,'sy':}})
A['idle']        = (3.0, lambda t: {'spine': {'sy': 1 + .012*tri(t,3)}, 'head': {'r': 2*osc(t,3)}, 'upperarm_A': {'r': -2*osc(t,3)}, 'upperarm_B': {'r': 2*osc(t,3)}})
A['head_tilt']   = (2.4, lambda t: {'head': {'r': 12*osc(t,2.4)}, 'neck': {'r': 3*osc(t,2.4)}})
A['lean']        = (3.0, lambda t: {'spine': {'r': 12*osc(t,3)}, 'head': {'r': -5*osc(t,3)}, 'upperarm_A': {'r': -6*osc(t,3)}, 'upperarm_B': {'r': -6*osc(t,3)}})
def wave(a_up, a_fore, swing):
    return lambda t: {'upperarm_A': {'r': a_up*hold(t,0,.6,3.0,3.6)}, 'forearm_A': {'r': a_fore*hold(t,0,.6,3.0,3.6) + swing*osc(t-.6,.7)*hold(t,.6,.8,2.8,3.0)}}
A['wave_small']  = (3.8, wave(-12, -75, 15))
A['wave_hi']     = (3.8, wave(-30, -150, 14))
A['arms_45']     = (3.0, lambda t: {'upperarm_A': {'r': -45*hold(t,0,.8,2.2,3.0)}, 'upperarm_B': {'r': 45*hold(t,0,.8,2.2,3.0)}})
A['arms_90']     = (3.0, lambda t: {'upperarm_A': {'r': -88*hold(t,0,.8,2.2,3.0)}, 'upperarm_B': {'r': 88*hold(t,0,.8,2.2,3.0)}})
A['arms_up']     = (3.0, lambda t: {'upperarm_A': {'r': -160*hold(t,0,.9,2.1,3.0)}, 'upperarm_B': {'r': 160*hold(t,0,.9,2.1,3.0)}})
A['hands_hips']  = (3.0, lambda t: {'upperarm_A': {'r': -38*hold(t,0,.7,2.3,3.0)}, 'forearm_A': {'r': 72*hold(t,0,.7,2.3,3.0)},
                                    'upperarm_B': {'r': 38*hold(t,0,.7,2.3,3.0)}, 'forearm_B': {'r': -72*hold(t,0,.7,2.3,3.0)}})
A['arms_front']  = (3.0, lambda t: {'upperarm_A': {'r': 12*hold(t,0,.7,2.3,3.0)}, 'forearm_A': {'r': 118*hold(t,0,.7,2.3,3.0)}})
A['leg_side']    = (3.0, lambda t: {'thigh_A': {'r': -28*hold(t,0,.7,2.3,3.0)}, 'hip': {'r': 3*hold(t,0,.7,2.3,3.0)}})
A['kick']        = (3.0, lambda t: {'thigh_A': {'r': -70*hold(t,0,.6,2.4,3.0)}, 'shin_A': {'r': 35*hold(t,0,.6,2.4,3.0)}, 'hip': {'r': 6*hold(t,0,.6,2.4,3.0)}})
def march(t):
    l, r = max(0, math.sin(t/1.2*2*math.pi)), max(0, -math.sin(t/1.2*2*math.pi))
    return {'thigh_A': {'sy': 1 - .22*l}, 'shin_A': {'r': -6*l}, 'thigh_B': {'sy': 1 - .22*r}, 'shin_B': {'r': 6*r},
            'root': {'y': 8*abs(math.sin(t/1.2*2*math.pi))}, 'upperarm_A': {'r': 12*math.sin(t/1.2*2*math.pi)}, 'upperarm_B': {'r': 12*math.sin(t/1.2*2*math.pi)}}
A['march']       = (2.4, march)
def jump(t):
    c = hold(t,0,.35,.45,.6); air = hold(t,.5,.8,.85,1.15); land = hold(t,1.1,1.25,1.3,1.6)
    return {'root': {'y': 140*air, 'sy': 1 - .06*c - .05*land + .03*air}, 'thigh_A': {'r': 10*c}, 'thigh_B': {'r': -10*c},
            'upperarm_A': {'r': -60*air}, 'upperarm_B': {'r': 60*air}}
A['jump']        = (2.0, jump)
A['bow']         = (3.0, lambda t: {'spine': {'sy': 1 - .18*hold(t,0,.8,2.2,3.0)}, 'head': {'y': -20*hold(t,0,.8,2.2,3.0), 'r': 0}})
A['turn']        = (4.0, lambda t: {'root': {'sx': math.cos(min(1, t/3.0)*math.pi)}})
anims = {}
for name, (dur, fn) in A.items():
    steps = int(dur/0.05); bones = {}
    for s in range(steps + 1):
        t = s*0.05; pose = fn(t)
        for b, v in pose.items():
            tl = bones.setdefault(b, {})
            if 'r' in v: tl.setdefault('rotate', []).append({'time': round(t,3), 'value': round(v['r'],3)})
            if 'x' in v or 'y' in v: tl.setdefault('translate', []).append({'time': round(t,3), 'x': round(v.get('x',0),2), 'y': round(v.get('y',0),2)})
            if 'sx' in v or 'sy' in v: tl.setdefault('scale', []).append({'time': round(t,3), 'x': round(v.get('sx',1),4), 'y': round(v.get('sy',1),4)})
    anims[name] = {'bones': bones}
skel['animations'] = anims
json.dump(skel, open('../spine/skeleton.json', 'w'), separators=(',', ':'))
print('animations', list(anims))
