"""Retro arcade cabinet (key 'arcade', 遊戲機.fbx) in a worn arcade corner at night: cosmic-pattern carpet,
painted block walls with pink / cyan neon, a second cabinet and a stool, posters; the CRT and marquee glow
and light the cabinet front.

  & $blender -b --factory-startup --python tools\\render\\scene_arcade.py -- --quality draft [--only hero,s1] [--turn] [--out DIR]
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402
import common as C  # noqa: E402
import modellib as ML  # noqa: E402

args = C.parse_args()
C.reset()

# ---------------------------------------------------------------- model
model = C.load("arcade", size=1.85)
# measured (model space): CRT picture area, marquee panel
SCR_X, SCR_Z0, SCR_Z1 = 0.22, 1.13, 1.46
MQ_X, MQ_Z0, MQ_Z1, MQ_Y = 0.27, 1.653, 1.813, -0.226


# ---------------------------------------------------------------- helpers for node maths
def _ops(nt):
    M = lambda op, a, b=None: C.mathn(nt, op, a, b)  # noqa: E731

    def rng(a, lo, hi):          # 1 if lo <= a < hi (integer pixel indices)
        return M("MULTIPLY", M("GREATER_THAN", a, lo - 0.5), M("LESS_THAN", a, hi - 0.5))

    def wn(a, b, c=0.0):
        w = C.N(nt, "TexWhiteNoise", noise_dimensions="3D")
        C._sock_set(w.inputs["Vector"], C.N(nt, "CombineXYZ", {"X": a, "Y": b, "Z": c}).outputs[0])
        return w.outputs["Value"]
    return M, rng, wn


def game_screen(name, colA="#ff3fd0", colB="#3ff0ff", colP="#5dff6a", seed=0.0, strength=3.2):
    """CRT showing a pixel shoot-'em-up (invader rows, shields, player ship, score line), with pixel dots,
    scanlines, vignette and a glossy curved-glass coat. Object coords of the cabinet (stays on the screen)."""
    m, nt, out = C.new_mat(name)
    M, rng, wn = _ops(nt)
    v = C.coords(nt)
    s = C.N(nt, "SeparateXYZ", {"Vector": v})
    u = C.maprange(nt, s.outputs[0], -SCR_X, SCR_X, 0.0, 1.0)
    w = C.maprange(nt, s.outputs[2], SCR_Z0, SCR_Z1, 0.0, 1.0)
    # rounded picture mask
    du = M("ABSOLUTE", M("SUBTRACT", u, 0.5)); dw = M("ABSOLUTE", M("SUBTRACT", w, 0.5))
    edge = M("MAXIMUM", M("POWER", M("MULTIPLY", du, 2.0), 6.0), M("POWER", M("MULTIPLY", dw, 2.0), 6.0))
    pic = C.maprange(nt, edge, 0.98, 0.7)
    px = M("FLOOR", M("MULTIPLY", u, 96.0)); py = M("FLOOR", M("MULTIPLY", w, 72.0))
    fu = M("FRACT", M("MULTIPLY", u, 96.0)); fv = M("FRACT", M("MULTIPLY", w, 72.0))
    dot = C.maprange(nt, M("MAXIMUM", M("ABSOLUTE", M("SUBTRACT", fu, 0.5)), M("ABSOLUTE", M("SUBTRACT", fv, 0.5))), 0.5, 0.32)
    # invaders: 8 x 4 grid of 7x5 mirrored sprites
    cx = M("SUBTRACT", px, 12.0); col = M("FLOOR", M("DIVIDE", cx, 9.0)); i = M("SUBTRACT", cx, M("MULTIPLY", col, 9.0))
    ry = M("SUBTRACT", py, 34.0); row = M("FLOOR", M("DIVIDE", ry, 7.0)); j = M("SUBTRACT", ry, M("MULTIPLY", row, 7.0))
    im = M("MINIMUM", i, M("SUBTRACT", 6.0, i))
    on = M("GREATER_THAN", wn(im, j, M("ADD", row, seed)), 0.4)
    inv = M("MULTIPLY", M("MULTIPLY", rng(col, 0, 8), M("LESS_THAN", i, 6.5)), M("MULTIPLY", rng(row, 0, 4), M("LESS_THAN", j, 4.5)))
    inv = M("MULTIPLY", inv, on)
    player = M("MAXIMUM", M("MULTIPLY", rng(py, 4, 7), rng(px, 44, 51)), M("MULTIPLY", rng(py, 7, 9), rng(px, 47, 48)))
    bunk = M("MULTIPLY", M("MULTIPLY", rng(py, 12, 17), rng(M("MODULO", px, 24.0), 7, 16)), M("GREATER_THAN", wn(px, py, 7.0 + seed), 0.22))
    bullets = M("MAXIMUM", M("MULTIPLY", rng(px, 30, 31), rng(py, 20, 23)), M("MULTIPLY", rng(px, 63, 64), rng(py, 27, 30)))
    bullets = M("MAXIMUM", bullets, M("MULTIPLY", rng(px, 47, 48), rng(py, 11, 15)))
    score = M("MULTIPLY", rng(py, 64, 68), M("MAXIMUM", rng(px, 6, 30), rng(px, 60, 90)))
    score = M("MULTIPLY", score, M("GREATER_THAN", wn(M("FLOOR", M("DIVIDE", px, 1.0)), py, 3.0 + seed), 0.38))
    ufo = M("MULTIPLY", M("MULTIPLY", rng(py, 57, 60), rng(px, 70, 79)), M("GREATER_THAN", wn(M("MINIMUM", M("SUBTRACT", px, 70.0), M("SUBTRACT", 78.0, px)), py, 9.0), 0.25))
    ground = M("MULTIPLY", rng(py, 2, 3), rng(px, 2, 94))
    c = C.col("#05071a")
    rowcol = C.mix(nt, M("LESS_THAN", row, 1.5), colB, colA)
    c = C.mix(nt, inv, c, rowcol)
    c = C.mix(nt, M("MAXIMUM", player, M("MAXIMUM", bunk, ground)), c, colP)
    c = C.mix(nt, M("MAXIMUM", bullets, score), c, "#f4f4ff")
    c = C.mix(nt, ufo, c, "#ff3b2b")
    lit = M("MAXIMUM", M("MAXIMUM", inv, M("MAXIMUM", player, bunk)), M("MAXIMUM", M("MAXIMUM", bullets, score), M("MAXIMUM", ufo, ground)))
    k = M("ADD", 0.12, M("MULTIPLY", lit, M("MULTIPLY", dot, 0.95)))
    vign = C.maprange(nt, M("ADD", M("MULTIPLY", du, du), M("MULTIPLY", dw, dw)), 0.05, 0.5, 1.0, 0.45)
    k = M("MULTIPLY", M("MULTIPLY", k, vign), pic)
    scan = C.maprange(nt, M("ABSOLUTE", M("SUBTRACT", fv, 0.5)), 0.2, 0.5, 1.0, 0.55)
    k = M("MULTIPLY", k, scan)
    n = C.noise(nt, v, 40.0, 3, 0.6)
    principled_ = C.principled(nt, out, color="#020203", rough=C.maprange(nt, n, 0.4, 0.75, 0.05, 0.22), coat=1.0,
                               coat_rough=0.02, emit=c, emit_strength=M("MULTIPLY", k, strength))
    m["recipe"] = "screen"
    return m


def marquee_mat(name, top="#1a0b5e", bottom="#ff2d7a", strength=2.6):
    """Back-lit marquee print: deep gradient with a star field and a low sun band."""
    m, nt, out = C.new_mat(name)
    M, rng, wn = _ops(nt)
    v = C.coords(nt)
    s = C.N(nt, "SeparateXYZ", {"Vector": v})
    u = C.maprange(nt, s.outputs[0], -MQ_X, MQ_X); w = C.maprange(nt, s.outputs[2], MQ_Z0, MQ_Z1)
    c = C.mix(nt, w, bottom, top)
    stars = M("GREATER_THAN", wn(M("FLOOR", M("MULTIPLY", u, 220.0)), M("FLOOR", M("MULTIPLY", w, 64.0)), 1.0), 0.985)
    c = C.mix(nt, stars, c, "#ffffff")
    band = M("MULTIPLY", C.maprange(nt, w, 0.0, 0.35, 1.0, 0.0), M("GREATER_THAN", M("FRACT", M("MULTIPLY", w, 22.0)), 0.45))
    c = C.mix(nt, M("MULTIPLY", band, 0.8), c, "#ffb02e")
    n = C.noise(nt, v, 30.0, 4, 0.6)
    C.principled(nt, out, color="#101010", rough=C.maprange(nt, n, 0.3, 0.7, 0.15, 0.35), coat=0.6, coat_rough=0.1,
                 emit=c, emit_strength=strength)
    m["recipe"] = "emissive"
    return m


def side_art(name, base="#1d3f86", stripes=("#ff7a1f", "#ff2d7a", "#ffd23a"), wear=0.55, tmold="#0c0c0e"):
    """Cabinet side panel: painted base with 80s diagonal speed stripes, scratches and kick scuffs,
    chipped edges showing raw particle board; faces not along X (the panel edges) get black T-molding."""
    m, nt, out = C.new_mat(name)
    M, rng, wn = _ops(nt)
    v = C.coords(nt)
    s = C.N(nt, "SeparateXYZ", {"Vector": v})
    y, z = s.outputs[1], s.outputs[2]
    on = C.N(nt, "SeparateXYZ", {"Vector": C.N(nt, "TexCoord").outputs["Normal"]}).outputs[0]
    is_side = C.maprange(nt, M("ABSOLUTE", on), 0.6, 0.85)
    diag = M("ADD", M("MULTIPLY", y, 0.9), z)            # diagonal coordinate
    c = C.col(base)
    c = C.mix(nt, 1.0, c, c)
    for k, sc in enumerate(stripes):
        lo = 0.75 + k * 0.11
        band = M("MULTIPLY", C.maprange(nt, diag, lo, lo + 0.012), C.maprange(nt, diag, lo + 0.07, lo + 0.058))
        c = C.mix(nt, band, c, sc)
    # a second, thinner stripe group lower down
    for k, sc in enumerate(stripes[:2]):
        lo = 0.2 + k * 0.06
        band = M("MULTIPLY", C.maprange(nt, diag, lo, lo + 0.008), C.maprange(nt, diag, lo + 0.03, lo + 0.022))
        c = C.mix(nt, band, c, sc)
    n_big = C.noise(nt, v, 3.0, 5, 0.6); n_fine = C.noise(nt, v, 30.0, 6, 0.65)
    # scratches: noise stretched along a random-ish direction
    scr = C.noise(nt, C.vmath(nt, "MULTIPLY", v, (1.0, 2.0, 60.0)), 3.0, 3, 0.5)
    scratch = M("MULTIPLY", C.maprange(nt, M("ABSOLUTE", M("SUBTRACT", scr, 0.5)), 0.016, 0.0), C.maprange(nt, n_big, 0.35, 0.55))
    # kick scuffs low on the panel
    kick = M("MULTIPLY", C.maprange(nt, z, 0.45, 0.05), C.maprange(nt, n_fine, 0.45, 0.6))
    grime = M("MAXIMUM", M("MULTIPLY", C.maprange(nt, n_big, 0.5, 0.8), 0.5), M("MULTIPLY", kick, 0.8))
    grime = M("MAXIMUM", grime, M("MULTIPLY", C.cavity_mask(nt, 0.1), 1.2))
    c = C.mix(nt, M("MULTIPLY", grime, 0.65), c, "#0d0b0a")
    c = C.mix(nt, M("MULTIPLY", scratch, 0.7), c, "#c9c4bb")
    e = C.edge_mask(nt, 0.006)
    chip = M("MULTIPLY", M("MULTIPLY", e, C.maprange(nt, n_fine, 0.4, 0.58)), wear * 2.2)
    chip = M("MINIMUM", chip, 1.0)
    c = C.mix(nt, chip, c, "#5b4a36")                    # particle board under the paint
    c = C.mix(nt, M("SUBTRACT", 1.0, is_side), c, tmold)
    r = C.maprange(nt, n_fine, 0.3, 0.7, 0.32, 0.5)
    r = C.mixf(nt, grime, r, 0.7)
    r = C.mixf(nt, chip, r, 0.85)
    r = C.mixf(nt, scratch, r, 0.6)
    r = C.mixf(nt, M("SUBTRACT", 1.0, is_side), r, 0.45)
    h = M("SUBTRACT", M("MULTIPLY", n_fine, 0.1), M("MULTIPLY", scratch, 0.3))
    C.principled(nt, out, color=c, rough=r, coat=M("MULTIPLY", is_side, 0.35), coat_rough=0.25,
                 normal=C.bump(nt, M("SUBTRACT", h, M("MULTIPLY", chip, 0.4)), 0.3, 0.002))
    return m


def carpet(name):
    """Arcade carpet (world space): dark navy with neon confetti shapes and squiggles, stains and a worn,
    flattened path in front of the cabinets."""
    m, nt, out = C.new_mat(name)
    M, rng, wn = _ops(nt)
    v = C.coords(nt, "world")
    s = C.N(nt, "SeparateXYZ", {"Vector": v})
    vor = C.N(nt, "TexVoronoi", {"Vector": v, "Scale": 5.0}, feature="F1")
    hue = vor.outputs["Color"]
    dots = C.maprange(nt, vor.outputs["Distance"], 0.13, 0.1)
    # keep only ~40 % of the dots and colour them from a small neon set
    pick = C.N(nt, "SeparateXYZ", {"Vector": hue})
    keep = M("GREATER_THAN", pick.outputs[0], 0.6)
    dc = C.mix(nt, M("GREATER_THAN", pick.outputs[1], 0.5), "#ff2d9a", "#2de0ff")
    dc = C.mix(nt, M("GREATER_THAN", pick.outputs[2], 0.75), dc, "#ffd23a")
    sq = C.noise(nt, v, 3.5, 2, 0.5, distortion=1.5)
    squig = C.maprange(nt, M("ABSOLUTE", M("SUBTRACT", sq, 0.5)), 0.012, 0.004)
    tri = C.N(nt, "TexVoronoi", {"Vector": v, "Scale": 9.0}, feature="F1").outputs["Distance"]
    rings = M("MULTIPLY", C.maprange(nt, M("ABSOLUTE", M("SUBTRACT", tri, 0.2)), 0.02, 0.008),
              M("GREATER_THAN", wn(M("FLOOR", M("MULTIPLY", s.outputs[0], 9.0)), M("FLOOR", M("MULTIPLY", s.outputs[1], 9.0)), 2.0), 0.85))
    c = C.col("#0b0b26")
    c = C.mix(nt, M("MULTIPLY", dots, keep), c, dc)
    c = C.mix(nt, squig, c, "#7a3dff")
    c = C.mix(nt, rings, c, "#2de0ff")
    n_big = C.noise(nt, v, 0.6, 5, 0.6); n_fine = C.noise(nt, v, 220.0, 3, 0.6)
    stain = M("MULTIPLY", C.maprange(nt, n_big, 0.55, 0.68), 0.75)
    c = C.mix(nt, stain, c, "#050404")
    # worn path in front of the cabinets (y in -1.3..-0.4): flattened, greyer, dirtier
    path = M("MULTIPLY", C.maprange(nt, s.outputs[1], -1.6, -1.0), C.maprange(nt, s.outputs[1], -0.45, -0.2))
    path = M("MULTIPLY", path, C.maprange(nt, M("ABSOLUTE", s.outputs[0]), 2.0, 1.0))
    c = C.mix(nt, M("MULTIPLY", path, 0.45), c, "#2b2a33")
    c = C.mix(nt, M("MULTIPLY", n_fine, 0.25), c, "#000000")
    C.principled(nt, out, color=c, rough=0.92, sheen=0.5, sheen_rough=0.5, spec=0.25,
                 normal=C.bump(nt, M("MULTIPLY", n_fine, M("SUBTRACT", 1.0, M("MULTIPLY", path, 0.6))), 0.35, 0.002))
    return m


def poster(name, top="#2a0b52", mid="#ff3d7f", bottom="#0b0420", sun="#ffb02e", age=0.5):
    """Synthwave-style poster print on a plane (Generated coords): gradient sky, striped sun, perspective grid,
    faded and grimy edges, slightly glossy paper."""
    m, nt, out = C.new_mat(name)
    M, rng, wn = _ops(nt)
    g = C.N(nt, "TexCoord").outputs["Generated"]
    s = C.N(nt, "SeparateXYZ", {"Vector": g})
    x, y = s.outputs[0], s.outputs[1]
    c = C.mix(nt, C.maprange(nt, y, 0.35, 1.0), mid, top)
    d = M("SQRT", M("ADD", M("MULTIPLY", M("SUBTRACT", x, 0.5), M("SUBTRACT", x, 0.5)), M("MULTIPLY", M("SUBTRACT", y, 0.45), M("SUBTRACT", y, 0.45))))
    sunm = M("MULTIPLY", C.maprange(nt, d, 0.23, 0.22), M("MAXIMUM", M("GREATER_THAN", y, 0.55),
                                                            M("GREATER_THAN", M("FRACT", M("MULTIPLY", y, 40.0)), 0.4)))
    sunm = M("MULTIPLY", sunm, M("GREATER_THAN", y, 0.37))
    c = C.mix(nt, sunm, c, sun)
    low = M("LESS_THAN", y, 0.37)
    gy = M("LESS_THAN", M("FRACT", M("DIVIDE", 1.0, M("ADD", M("SUBTRACT", 0.4, y), 0.03))), 0.12)
    gx = M("LESS_THAN", M("FRACT", M("MULTIPLY", M("DIVIDE", M("SUBTRACT", x, 0.5), M("ADD", M("SUBTRACT", 0.4, y), 0.03)), 0.6)), 0.06)
    c = C.mix(nt, low, c, bottom)
    c = C.mix(nt, M("MULTIPLY", low, M("MAXIMUM", gx, gy)), c, "#ff2d9a")
    n = C.noise(nt, g, 6.0, 5, 0.6)
    edge = M("MAXIMUM", M("ABSOLUTE", M("SUBTRACT", x, 0.5)), M("ABSOLUTE", M("SUBTRACT", y, 0.5)))
    fade = M("MULTIPLY", M("ADD", C.maprange(nt, edge, 0.38, 0.5), M("MULTIPLY", C.maprange(nt, n, 0.5, 0.75), 0.6)), age)
    c = C.mix(nt, M("MINIMUM", fade, 1.0), c, "#3a3226")
    C.principled(nt, out, color=c, rough=C.maprange(nt, n, 0.3, 0.7, 0.35, 0.6), spec=0.4)
    return m


def neon(name, color, strength=18.0):
    m = C.material("emissive", name, color=color, strength=strength, base=color)
    return m


# ---------------------------------------------------------------- model looks
M_BEZEL = C.material("plastic", "arc_bezel", color="#060607", rough=0.3, coat=0.4)
M_SCREEN = game_screen("arc_game")
M_MARQ = marquee_mat("arc_marq")
LOOKS = {
    "arc_trim": side_art("arc_sideart"),                    # the two big side panels (立方体.001)
    "arc_side": ("painted", dict(color="#121318", rough=0.5, grime=0.6, wear=0.6, panels=None, under="#5b4a36", scale=0.4)),
    "arc_front": ("painted", dict(color="#141519", rough=0.48, grime=0.65, wear=0.7, panels=None, under="#5b4a36",
                                  grime_color="#050403", scale=0.35, streaks=0.3)),
    "arc_screen": M_SCREEN,
    "arc_marquee": M_MARQ,
    "metal_mid": ("metal", dict(color="#9ea4ab", rough=0.32, brushed=0.7, grime=0.6, scale=0.3)),   # coin door
    "metal_dark": ("metal", dict(color="#c9cdd2", rough=0.16, grime=0.3, scale=0.3)),               # stick shafts, speaker rings
    "btn_red": ("plastic", dict(color="#d8262b", rough=0.22, coat=0.8)),
    "btn_yellow": ("plastic", dict(color="#f1c22d", rough=0.22, coat=0.8)),
    "btn_blue": ("plastic", dict(color="#2c7be0", rough=0.22, coat=0.8)),
    "btn_green": ("plastic", dict(color="#2fb86a", rough=0.22, coat=0.8)),
}
C.apply_looks(model.objs, LOOKS)


def split_bezel(objs, bezel, front):
    """The palette's 'screen' region also covers the bezel above the CRT and the recess walls; the 'marquee'
    region covers its frame. Re-slot those faces so only the CRT picture and the marquee panel glow."""
    for o in objs:
        if o.name != "立方体":
            continue
        me = o.data
        idx = {C.palette_of(m): i for i, m in enumerate(me.materials)}
        me.materials.append(bezel); bi = len(me.materials) - 1
        fi = idx["arc_front"]
        for p in me.polygons:
            pal = C.palette_of(me.materials[p.material_index])
            n, c = p.normal, p.center
            if pal == "arc_screen" and (n.z < -0.3 or c.z > 1.472 or abs(n.x) > 0.6):
                p.material_index = bi
            elif pal == "arc_marquee" and n.y > -0.95:
                p.material_index = fi


split_bezel(model.objs, M_BEZEL, None)

# marquee title + coin-door lamps, parented to the cabinet
M_TITLE = C.material("emissive", "arc_title", color="#ffd84a", strength=7.0, base="#ffd84a")
M_TITLE2 = C.material("emissive", "arc_title2", color="#3ff0ff", strength=5.0, base="#3ff0ff")
M_COIN = C.material("emissive", "arc_coinlamp", color="#ff2b1f", strength=6.0, base="#ff2b1f")
M_BLACK = C.material("flat", "arc_ink", color="#0a0610", rough=0.5)
ATTACH = []
t = C.text("mq_title", "COSMO RAID", 0.068, (0, MQ_Y - 0.004, 1.745), (90, 0, 0), M_TITLE, C.FONT_STENCIL, extrude=0.0015,
           spacing=1.05)
ATTACH.append(t)
ATTACH.append(C.text("mq_sub", "宇 宙 突 襲", 0.026, (0, MQ_Y - 0.004, 1.684), (90, 0, 0), M_TITLE2, C.FONT_TC, extrude=0.001))
for k, x in enumerate((-0.06, 0.06)):
    ATTACH.append(C.plane(f"coin_lamp_{k}", (0.03, 0.045), (x, -0.2925, 0.70), (90, 0, 0), M_COIN, role="keep"))
    ATTACH.append(C.text(f"coin_lbl_{k}", "25¢", 0.012, (x, -0.2935, 0.70), (90, 0, 0), M_BLACK, C.FONT_LATIN))
# screen and marquee light (parented: they spin with the cabinet on the turntable)
ATTACH.append(C.area("crt_light", (0, -0.2, 1.29), (0, -3.0, 0.9), 14, "#7fc8ff", 0.44, 0.32))
ATTACH.append(C.area("marq_light", (0, -0.3, 1.73), (0, -3.0, 1.2), 8, "#ff5a8a", 0.5, 0.15))
for o in ATTACH:
    o.parent = model.pivot

# ---------------------------------------------------------------- set: arcade corner
BACK, FRONT, XL, XR, H = 0.78, -4.6, -2.15, 3.2, 2.95

M_CARPET = carpet("arc_carpet")
M_BLOCK = C.material("painted", "arc_blockwall", color="#221a2c", rough=0.7, grime=0.75, wear=0.15, panels=(0.4, 0.4, 0.2),
                     seam_width=0.008, space="world", streaks=0.7, grime_color="#08060a", under="#4a4650")
M_CEIL = C.material("painted", "arc_ceiling", color="#141218", rough=0.8, grime=0.5, wear=0.0, panels=(0.6, 0.6, 1000),
                    seam_width=0.006, space="world")
M_BASEB = C.material("plastic", "arc_baseboard", color="#0b0b0d", rough=0.5)
M_CHROME = C.material("metal", "arc_chrome", color="#d4d8dc", rough=0.12, grime=0.25, space="world")
M_VINYL = C.material("leather", "arc_vinyl", color="#2a1630", rough=0.4, space="world")
M_TAPE = C.material("flat", "arc_paper", color="#e8e2cf", rough=0.8)
M_N_PINK = neon("arc_neon_pink", "#ff2d9a", 22.0)
M_N_CYAN = neon("arc_neon_cyan", "#2de6ff", 18.0)
M_N_PURP = neon("arc_neon_purple", "#8a3dff", 5.0)
M_TUBE_BACK = C.material("flat", "arc_neon_backing", color="#0a0a0c", rough=0.5)

C.plane("floor", (XR - XL, BACK - FRONT), ((XL + XR) / 2, (BACK + FRONT) / 2, 0), mat=M_CARPET)
C.box("wall_back", (XR - XL + 0.4, 0.2, H), ((XL + XR) / 2, BACK + 0.1, 0), mat=M_BLOCK, origin="bottom", bevel=0)
C.box("wall_left", (0.2, BACK - FRONT, H), (XL - 0.1, (BACK + FRONT) / 2, 0), mat=M_BLOCK, origin="bottom", bevel=0)
C.box("wall_right", (0.2, BACK - FRONT, H), (XR + 0.1, (BACK + FRONT) / 2, 0), mat=M_BLOCK, origin="bottom", bevel=0)
C.box("wall_front", (XR - XL + 0.4, 0.2, H), ((XL + XR) / 2, FRONT - 0.1, 0), mat=M_BLOCK, origin="bottom", bevel=0)
C.box("ceiling", (XR - XL + 0.4, BACK - FRONT + 0.4, 0.1), ((XL + XR) / 2, (BACK + FRONT) / 2, H), mat=M_CEIL,
      origin="bottom", bevel=0)
C.box("baseboard_b", (XR - XL, 0.03, 0.1), ((XL + XR) / 2, BACK - 0.015, 0), mat=M_BASEB, origin="bottom", bevel=0.005)
C.box("baseboard_l", (0.03, BACK - FRONT, 0.1), (XL + 0.015, (BACK + FRONT) / 2, 0), mat=M_BASEB, origin="bottom", bevel=0.005)

# neon on the back wall: tube zig-zag + sign, each tube on a dark backing rail
C.text("neon_sign", "GAME CENTER", 0.17, (1.25, BACK - 0.03, 2.4), (90, 0, 0), M_N_PINK, C.FONT_STENCIL, extrude=0.008,
       spacing=1.1, role="keep")
C.text("neon_sign_tc", "電子遊樂場", 0.15, (1.25, BACK - 0.03, 2.14), (90, 0, 0), M_N_CYAN, C.FONT_TC, extrude=0.008,
       role="keep")
zig = [(-1.95 + k * 0.32, BACK - 0.04, 2.72 + (0.07 if k % 2 else -0.07)) for k in range(13)]
C.cable("neon_zig", zig, 0.011, M_N_PURP, role="keep")
# cyan tube along the left wall, pink tube along the right wall
C.cable("neon_left", [(XL + 0.04, BACK - 0.2, 2.55), (XL + 0.04, -1.0, 2.55), (XL + 0.04, -2.2, 2.55), (XL + 0.04, -3.3, 2.4)],
        0.012, M_N_CYAN, role="keep")
C.cable("neon_right", [(XR - 0.04, -0.2, 2.5), (XR - 0.04, -1.6, 2.5), (XR - 0.04, -2.9, 2.5)], 0.012, M_N_PINK, role="keep")
for k, (x0, y0, x1, y1) in enumerate(((XL + 0.02, BACK - 0.2, XL + 0.02, -3.3), (XR - 0.02, -0.2, XR - 0.02, -2.9))):
    C.box(f"neon_rail_{k}", (0.02, abs(y1 - y0), 0.03), (x0, (y0 + y1) / 2, 2.52), mat=M_TUBE_BACK, bevel=0)

# second cabinet (duplicate of the model, different art/game), left of the hero
M_SIDE2 = side_art("arc_sideart_2", base="#7a1414", stripes=("#ffd23a", "#ffffff", "#ff7a1f"), wear=0.7)
M_SCREEN2 = game_screen("arc_game_2", colA="#ffd23a", colB="#5dff6a", colP="#ff3fd0", seed=5.0, strength=2.4)
M_MARQ2 = marquee_mat("arc_marq_2", top="#062a3a", bottom="#18d0ff", strength=1.8)
SWAP2 = {"arc_trim": M_SIDE2, "arc_screen": M_SCREEN2, "arc_marquee": M_MARQ2}


def dup_cabinet(name, loc, rotz, swap):
    piv = bpy.data.objects.new(name + "_pivot", None); C.link(piv)
    piv.location = loc; piv.rotation_euler.z = math.radians(rotz)
    for o in model.objs:
        c = o.copy(); C.link(c); c.parent = piv; c.matrix_parent_inverse = Matrix.Identity(4)
        c.matrix_basis = Matrix.Identity(4)
        # own mesh data: the clay/wire passes swap + restore materials per mesh, shared meshes would not restore
        c.data = o.data.copy()
        if any(C.palette_of(m) in swap for m in o.data.materials):
            for i, m in enumerate(c.data.materials):
                if C.palette_of(m) in swap:
                    nm = swap[C.palette_of(m)]; nm["palette"] = C.palette_of(m)
                    c.data.materials[i] = nm
        C.tag(c, "set")
    t2 = C.text(name + "_title", "NEON DRIFT", 0.062, (0, MQ_Y - 0.004, 1.735), (90, 0, 0),
                C.material("emissive", "arc_title_b", color="#ffffff", strength=5.0), C.FONT_STENCIL, extrude=0.0015)
    t2.parent = piv
    C.area(name + "_crt", (0, -0.2, 1.29), (0, -3.0, 0.9), 8, "#b8ff9a", 0.44, 0.32).parent = piv
    # handwritten "out of order" note taped to the screen
    note = C.plane(name + "_note", (0.16, 0.1), (0.08, -0.135, 1.22), (78, 0, 4), M_TAPE)
    note.parent = piv
    C.text(name + "_note_t", "故障", 0.035, (0.08, -0.14, 1.222), (78, 0, 4), M_BLACK, C.FONT_TC).parent = piv
    return piv


dup_cabinet("cab2", (-1.08, 0.04, 0), -7.0, SWAP2)

# stool (hidden on the turntable: it is close to the cabinet front)
STOOL = (-1.4, -1.05)
st = [C.cylinder("stool_base", 0.22, 0.03, (STOOL[0], STOOL[1], 0), mat=M_CHROME, segments=32, origin="bottom"),
      C.cylinder("stool_post", 0.03, 0.58, (STOOL[0], STOOL[1], 0.03), mat=M_CHROME, segments=16, origin="bottom"),
      C.cylinder("stool_ring", 0.16, 0.015, (STOOL[0], STOOL[1], 0.24), mat=M_CHROME, segments=32),
      C.cylinder("stool_seat", 0.19, 0.08, (STOOL[0], STOOL[1], 0.61), mat=M_VINYL, segments=40, origin="bottom"),
      C.cylinder("stool_seat_rim", 0.195, 0.025, (STOOL[0], STOOL[1], 0.62), mat=M_CHROME, segments=40)]

# change machine against the back wall (right)
CM = (2.45, 0.45)
C.box("change_body", (0.62, 0.55, 1.55), (CM[0], CM[1], 0), mat=C.material("painted", "arc_change", color="#8c8f94", rough=0.4,
      metal=0.4, grime=0.6, wear=0.6, panels=None, space="world", scale=0.4), origin="bottom", bevel=0.02)
C.box("change_panel", (0.5, 0.02, 0.32), (CM[0], CM[1] - 0.28, 1.18), mat=C.material("emissive", "arc_change_lit",
      color="#ffe9b0", strength=0.9, base="#ffe9b0"), bevel=0, role="keep")
C.text("change_txt", "兌幣 CHANGE", 0.06, (CM[0], CM[1] - 0.292, 1.2), (90, 0, 0), C.material("flat", "arc_change_ink",
       color="#b3121a", rough=0.6), C.FONT_TC)
C.box("change_tray", (0.22, 0.12, 0.08), (CM[0], CM[1] - 0.32, 0.55), mat=M_CHROME, bevel=0.01)

# posters
P1 = poster("arc_poster_1")
P2 = poster("arc_poster_2", top="#03203a", mid="#18d0ff", bottom="#03081a", sun="#ff2d9a", age=0.7)
C.plane("poster_1", (0.6, 0.85), (XL + 0.012, -1.25, 1.55), (90, 0, 90), P1)
C.text("poster_1_t", "HIGH SCORE", 0.07, (XL + 0.014, -1.25, 1.84), (90, 0, 90), C.material("flat", "arc_poster_ink",
       color="#fff2c0", rough=0.6), C.FONT_STENCIL)
C.plane("poster_2", (0.55, 0.78), (0.95, BACK - 0.012, 1.55), (90, 0, 0), P2)
C.text("poster_2_t", "INSERT COIN", 0.06, (0.95, BACK - 0.014, 1.82), (90, 0, 0), C.material("flat", "arc_poster_ink"),
       C.FONT_STENCIL)
C.plane("poster_3", (0.5, 0.7), (XR - 0.012, -1.0, 1.5), (90, 0, -90), P1)
for k, (x, y, z, r) in enumerate(((0.69, BACK - 0.014, 1.93, 8), (1.2, BACK - 0.014, 1.95, -6))):   # tape corners
    C.plane(f"tape_{k}", (0.06, 0.02), (x, y, z), (90, r, 0), M_TAPE)

# ceiling: a single can light above the cabinets, and a dead fluorescent fixture
C.cylinder("can_1", 0.11, 0.08, (0.55, -0.9, H - 0.04), mat=M_CHROME, segments=24)
C.cylinder("can_1_lens", 0.08, 0.005, (0.55, -0.9, H - 0.081), mat=C.material("emissive", "arc_can_lens", color="#fff1dc",
           strength=12.0), segments=24, role="keep")
C.box("fluo", (1.2, 0.2, 0.06), (-0.2, -2.2, H - 0.03), mat=M_CHROME, bevel=0.01)
C.box("fluo_tube", (1.1, 0.05, 0.03), (-0.2, -2.2, H - 0.07), mat=C.material("plastic", "arc_dead_tube", color="#b8b8b0",
      rough=0.3), bevel=0.01)

# ---------------------------------------------------------------- lighting
C.world("#020104", 1.0)
C.spot("key_can", (0.55, -0.9, H - 0.09), (0.0, -0.1, 0.9), 260, C.kelvin(5200), 55, 0.7, 0.05)
C.area("rim_pink", (-1.3, 0.55, 2.4), (0, 0.0, 1.3), 90, "#ff3fa8", 0.8)
C.area("rim_cyan", (1.4, 0.6, 2.2), (0, 0.0, 1.2), 45, "#3fd8ff", 0.6)
C.area("fill_cyan", (2.9, -1.2, 1.4), (0, -0.2, 1.0), 40, "#3fd8ff", 1.2)
C.area("fill_front", (-0.6, -3.6, 1.6), (0, 0, 1.0), 25, "#8a7cff", 2.0)
C.haze("haze", ((XL + XR) / 2, (BACK + FRONT) / 2, H / 2), (XR - XL - 0.05, BACK - FRONT - 0.05, H - 0.02), 0.03,
       "#e0d0ff", 0.4)

for nm in ("arc_coinlamp", "arc_title2", "arc_can_lens", "arc_title_b"):
    mm = bpy.data.materials.get(nm)
    if mm is not None:
        mm.cycles.emission_sampling = "NONE"

# ---------------------------------------------------------------- shots
SHOTS = [
    C.Shot("hero", dict(loc=(0.95, -2.1, 0.5), target=(-0.1, 0.0, 1.25), lens=24, fstop=2.8, focus=(0.0, -0.3, 1.1)),
           "低角度仰看遊戲機：映像管與招牌燈箱發亮，背後的粉紅、青色霓虹照著磚牆與地毯。", kind="hero"),
    C.Shot("card", dict(loc=(1.55, -2.6, 1.5), target=(0.0, 0.0, 0.95), lens=34),
           "三分之四前側視角，遊戲機立在夜裡的遊樂場角落。", kind="card"),
    C.Shot("s1", dict(loc=(-0.95, -3.3, 1.35), target=(0.05, 0.0, 0.95), lens=30),
           "三分之四前視：招牌、弧面映像管、控制台與投幣口，左邊是另一台機台。"),
    C.Shot("s2", dict(loc=(2.4, -1.0, 1.35), target=(0.0, 0.05, 0.95), lens=24),
           "側面：側板的斜條彩繪、刮痕與邊角掉漆，背景是兌幣機與海報。"),
    C.Shot("s3", dict(loc=(0.42, -0.98, 1.38), target=(0.0, -0.25, 1.0), lens=50, fstop=2.0, focus=(0.08, -0.3, 1.0)),
           "控制台特寫：搖桿、按鈕與被手磨舊的面板。"),
    C.Shot("s4", dict(loc=(-0.5, -0.95, 1.5), target=(0.0, -0.15, 1.45), lens=42, fstop=2.2, focus=(-0.05, -0.2, 1.5)),
           "映像管與招牌特寫：螢幕上的像素畫面、掃描線與玻璃反光。"),
]
CAPTIONS = {"clay": "白模：與三分之四前視同一鏡頭，只看造型與比例。",
            "wire": "線框：同一鏡頭顯示模型的實際四邊形佈線。"}
TURN = dict(loc=(0.0, -3.2, 1.3), target=(0.0, 0.0, 0.95), lens=34)
for o in st:
    o["hide_turn"] = True

C.run(args, "arcade", model, SHOTS, clay_wire_of="s1", turn=TURN, turn_mode="model", captions_extra=CAPTIONS)
