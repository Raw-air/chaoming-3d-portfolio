"""Jukebox (key 'jukebox', 點唱機.fbx) in the corner of a retro diner at blue hour: checker floor, wood wainscot
and mint subway tiles, red vinyl booth, a green enamel pendant lamp, warm neon, and a window with venetian blinds
throwing cool dusk light across the room.

  & $blender -b --factory-startup --python tools\\render\\scene_jukebox.py -- --quality draft [--only hero,s1] [--turn] [--out DIR]
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
model = C.load("jukebox", size=1.55)
DOME_Z0, DOME_Z1, DOME_X = 1.157, 1.535, 0.29        # measured (model space): arched top window
SEL_Z0, SEL_Z1, SEL_X = 0.965, 1.095, 0.29           # selection-card panel
TUBE_Z0, TUBE_Z1 = 0.22, 0.87


def _ops(nt):
    M = lambda op, a, b=None: C.mathn(nt, op, a, b)  # noqa: E731

    def wn(a, b, c=0.0):
        w = C.N(nt, "TexWhiteNoise", noise_dimensions="3D")
        C._sock_set(w.inputs["Vector"], C.N(nt, "CombineXYZ", {"X": a, "Y": b, "Z": c}).outputs[0])
        return w.outputs["Value"]
    return M, wn


# ---------------------------------------------------------------- jukebox materials
def dome_mat(name, strength=1.1):
    """Arched top window: back-lit sunburst (amber -> rose), glossy glass coat over it."""
    m, nt, out = C.new_mat(name)
    M, wn = _ops(nt)
    v = C.coords(nt)
    s = C.N(nt, "SeparateXYZ", {"Vector": v})
    x = s.outputs[0]; zr = M("SUBTRACT", s.outputs[2], DOME_Z0 - 0.02)
    ang = M("ARCTAN2", x, zr)                        # -pi/2..pi/2 across the arch
    rad = M("SQRT", M("ADD", M("MULTIPLY", x, x), M("MULTIPLY", zr, zr)))
    # moulded ribs fanning out from the hub: a rounded profile (used for bump and for light leaking through
    # the thinner rib valleys)
    rib = M("ABSOLUTE", M("SINE", M("MULTIPLY", ang, 15.0)))
    valley = M("SUBTRACT", 1.0, rib)
    rr = C.maprange(nt, rad, 0.04, 0.36)
    c = C.mix(nt, C.maprange(nt, rad, 0.03, 0.14), "#fff1c8", "#ffa424")
    c = C.mix(nt, C.maprange(nt, rad, 0.14, 0.36), c, "#ff2a4a")
    hot = C.maprange(nt, rad, 0.0, 0.34, 3.2, 0.45, "SMOOTHSTEP")   # hot centre with falloff
    k = M("MULTIPLY", hot, M("ADD", 0.6, M("MULTIPLY", valley, 0.55)))
    ring = M("MULTIPLY", C.maprange(nt, M("ABSOLUTE", M("SUBTRACT", rad, 0.21)), 0.01, 0.004), 0.5)
    k = M("ADD", k, ring)
    n = C.noise(nt, v, 30.0, 4, 0.6)
    nrm = C.bump(nt, M("ADD", M("MULTIPLY", rib, 1.0), M("MULTIPLY", n, 0.05)), 0.45, 0.004)
    C.principled(nt, out, color="#3a1608", rough=0.35, normal=nrm, coat=1.0, coat_rough=0.015,
                 sss=0.0, emit=c, emit_strength=M("MULTIPLY", k, strength))
    m["recipe"] = "emissive"
    return m


def tube_mat(name, strength=1.3):
    """The U bubble tube: colour cycling along its height (amber at the bottom -> rose -> violet at the top)
    with brighter bubble bands."""
    m, nt, out = C.new_mat(name)
    M, wn = _ops(nt)
    v = C.coords(nt)
    z = C.N(nt, "SeparateXYZ", {"Vector": v}).outputs[2]
    t = C.maprange(nt, z, TUBE_Z0, TUBE_Z1)
    c = C.mix(nt, C.maprange(nt, t, 0.0, 0.55), "#ff8a1c", "#ff3d6e")
    c = C.mix(nt, C.maprange(nt, t, 0.55, 1.0), c, "#b04dff")
    bands = C.N(nt, "TexWave", {"Vector": v, "Scale": 9.0, "Distortion": 2.0}, wave_type="BANDS",
                bands_direction="Z").outputs["Factor"]
    k = C.maprange(nt, bands, 0.0, 1.0, 0.65, 1.25)
    C.principled(nt, out, color="#3a1408", rough=0.1, coat=1.0, coat_rough=0.02, emit=c,
                 emit_strength=M("MULTIPLY", k, strength))
    m["recipe"] = "emissive"
    return m


def cloth_mat(name, strength=0.6):
    """Speaker cloth behind the chrome lattice, lit from inside: warm weave, glow brighter at the centre."""
    m, nt, out = C.new_mat(name)
    M, wn = _ops(nt)
    v = C.coords(nt)
    s = C.N(nt, "SeparateXYZ", {"Vector": v})
    p = 0.0055                                        # thread pitch (coarse grille cloth)
    gx = M("DIVIDE", s.outputs[0], p); gz = M("DIVIDE", s.outputs[2], p)
    wx = M("MULTIPLY", M("ABSOLUTE", M("SUBTRACT", M("FRACT", gx), 0.5)), 2.0)   # 0 thread centre .. 1 edge
    wz = M("MULTIPLY", M("ABSOLUTE", M("SUBTRACT", M("FRACT", gz), 0.5)), 2.0)
    par = M("MODULO", M("ABSOLUTE", M("ADD", M("FLOOR", gx), M("FLOOR", gz))), 2.0)   # over / under
    h = C.mixf(nt, par, M("SUBTRACT", 1.0, M("MULTIPLY", wx, wx)), M("SUBTRACT", 1.0, M("MULTIPLY", wz, wz)))
    holes = C.maprange(nt, M("MULTIPLY", wx, wz), 0.45, 0.8)                     # light leaks between threads
    gold = M("LESS_THAN", M("MODULO", M("ABSOLUTE", M("FLOOR", gx)), 5.0), 0.5)   # every 5th warp: metallic thread
    gold = M("MULTIPLY", gold, M("SUBTRACT", 1.0, par))
    cen = M("ADD", M("MULTIPLY", s.outputs[0], s.outputs[0]), M("MULTIPLY", M("SUBTRACT", s.outputs[2], 0.45), M("SUBTRACT", s.outputs[2], 0.45)))
    glow = C.maprange(nt, cen, 0.0, 0.14, 1.3, 0.4)
    c = C.mix(nt, C.maprange(nt, h, 0.2, 1.0), "#140705", "#3a160e")
    c = C.mix(nt, gold, c, "#b8904a")
    em = C.mix(nt, glow, "#ff3a20", "#ff9a3a")
    C.principled(nt, out, color=c, metal=M("MULTIPLY", gold, 0.9), rough=C.mixf(nt, gold, 0.8, 0.35), sheen=0.6,
                 sheen_rough=0.4, emit=em, emit_strength=M("MULTIPLY", M("MULTIPLY", holes, glow), strength * 6.0),
                 normal=C.bump(nt, h, 0.5, 0.0015))
    m["recipe"] = "emissive"
    return m


def cards_mat(name, strength=0.8):
    """Selection panel: two rows of back-lit title cards (paper with red/blue title strips and type lines)
    in a brushed-metal frame. Outside the card window it is plain brushed metal."""
    m, nt, out = C.new_mat(name)
    M, wn = _ops(nt)
    v = C.coords(nt)
    s = C.N(nt, "SeparateXYZ", {"Vector": v})
    u = C.maprange(nt, s.outputs[0], -SEL_X + 0.03, SEL_X - 0.03); w = C.maprange(nt, s.outputs[2], SEL_Z0 + 0.012, SEL_Z1 - 0.012)
    inside = M("MULTIPLY", M("MULTIPLY", M("GREATER_THAN", u, 0.001), M("LESS_THAN", u, 0.999)),
               M("MULTIPLY", M("GREATER_THAN", w, 0.001), M("LESS_THAN", w, 0.999)))
    cu = M("FRACT", M("MULTIPLY", u, 10.0)); cw = M("FRACT", M("MULTIPLY", w, 2.0))
    card = M("MULTIPLY", M("MULTIPLY", M("GREATER_THAN", cu, 0.06), M("LESS_THAN", cu, 0.94)),
             M("MULTIPLY", M("GREATER_THAN", cw, 0.1), M("LESS_THAN", cw, 0.9)))
    card = M("MULTIPLY", card, inside)
    # a gap in the middle of the panel for the selector knob
    card = M("MULTIPLY", card, M("GREATER_THAN", M("ABSOLUTE", M("SUBTRACT", u, 0.5)), 0.08))
    title = M("MULTIPLY", M("GREATER_THAN", cw, 0.62), M("LESS_THAN", cw, 0.78))
    lines = M("MULTIPLY", M("LESS_THAN", M("FRACT", M("MULTIPLY", cw, 9.0)), 0.35), M("LESS_THAN", cw, 0.55))
    lines = M("MULTIPLY", lines, M("GREATER_THAN", wn(M("FLOOR", M("MULTIPLY", u, 80.0)), M("FLOOR", M("MULTIPLY", w, 18.0))), 0.3))
    lines = M("MULTIPLY", lines, M("MULTIPLY", M("GREATER_THAN", cu, 0.15), M("LESS_THAN", cu, 0.85)))
    tcol = C.mix(nt, M("GREATER_THAN", wn(M("FLOOR", M("MULTIPLY", u, 10.0)), M("FLOOR", M("MULTIPLY", w, 2.0))), 0.5), "#c2241c", "#2a4fb0")
    c = C.mix(nt, 1.0, "#f3ead2", "#f3ead2")
    c = C.mix(nt, title, c, tcol)
    c = C.mix(nt, M("MULTIPLY", lines, 0.8), c, "#3a3530")
    n = C.noise(nt, v, 20.0, 4, 0.6)
    metal_c = C.mix(nt, C.maprange(nt, n, 0.4, 0.7, 0, 0.4), "#c8ccd2", "#7d8288")
    base = C.mix(nt, card, metal_c, c)
    C.principled(nt, out, color=base, metal=M("SUBTRACT", 1.0, card), rough=C.mixf(nt, card, 0.22, 0.5), coat=0.5,
                 coat_rough=0.05, emit=c, emit_strength=M("MULTIPLY", card, strength))
    return m


def grille_mat(name, strength=1.2):
    """The diamond lattice is one embossed plane: chrome on the raised (tilted) ridges, back-lit amber/rose
    panes in the flat diamond cells."""
    m, nt, out = C.new_mat(name)
    M, wn = _ops(nt)
    v = C.coords(nt)
    ny = C.N(nt, "SeparateXYZ", {"Vector": C.N(nt, "TexCoord").outputs["Normal"]}).outputs[1]
    flat = C.maprange(nt, M("ABSOLUTE", ny), 0.93, 0.985)
    z = C.N(nt, "SeparateXYZ", {"Vector": v}).outputs[2]
    t = C.maprange(nt, z, 0.17, 0.95)
    glow = C.mix(nt, t, "#ff7a14", "#e0183c")
    a = C.N(nt, "TexWave", {"Vector": v, "Scale": 300.0}, wave_type="BANDS", bands_direction="X").outputs["Factor"]
    b = C.N(nt, "TexWave", {"Vector": v, "Scale": 300.0}, wave_type="BANDS", bands_direction="Z").outputs["Factor"]
    weave = C.maprange(nt, M("MULTIPLY", a, b), 0.0, 1.0, 0.55, 1.0)       # speaker cloth seen through the pane
    cen = C.maprange(nt, M("ABSOLUTE", C.N(nt, "SeparateXYZ", {"Vector": v}).outputs[0]), 0.0, 0.22, 1.15, 0.6)
    strength = M("MULTIPLY", M("MULTIPLY", weave, cen), strength)
    n = C.noise(nt, v, 25.0, 4, 0.6)
    base = C.mix(nt, flat, "#e6e9ee", "#2a0c06")
    C.principled(nt, out, color=base, metal=M("SUBTRACT", 1.0, flat), rough=C.maprange(nt, n, 0.3, 0.7, 0.05, 0.14),
                 coat=flat, coat_rough=0.05, emit=glow, emit_strength=M("MULTIPLY", flat, strength))
    m["recipe"] = "grille"     # part of the modelled shape: clay/wire passes do replace it
    return m


M_DOME = dome_mat("jb_dome")
M_CHROME_RIM = C.material("metal", "jb_chrome_rim", color="#eef1f4", rough=0.05, grime=0.15, scale=0.3)
LOOKS = {
    "jb_wood": ("wood", dict(color="#5e2c12", color2="#2a1006", rough=0.36, grain=14.0, axis="Z", coat=0.5)),
    "jb_glass": M_DOME,
    "jb_cloth": cloth_mat("jb_cloth_lit"),
    "jb_tube": tube_mat("jb_tube_lit"),
    "chrome": M_CHROME_RIM,
    "metal_light": cards_mat("jb_cards"),
    "metal_mid": ("metal", dict(color="#3d3631", rough=0.28, brushed=0.6, grime=0.5, scale=0.3)),
}
C.apply_looks(model.objs, LOOKS)


def split_dome(objs):
    """The palette's 'glass' region includes the arch rim running over the top: make that chrome."""
    for o in objs:
        if o.name != "立方体":
            continue
        me = o.data
        me.materials.append(M_CHROME_RIM); ci = len(me.materials) - 1
        for p in me.polygons:
            if C.palette_of(me.materials[p.material_index]) == "jb_glass" and p.normal.y > -0.85:
                p.material_index = ci


split_dome(model.objs)
_g = model.by_name("平面")
_g.data.materials[0] = grille_mat("jb_grille")
_g.data.materials[0]["palette"] = "chrome"
# the internal light the glowing parts give off (parented: spins with the model)
L_IN = [C.area("jb_front_glow", (0, -0.45, 0.6), (0, -3.0, 0.3), 35, "#ff7a48", 0.45, 0.7),
        C.area("jb_floor_spill", (0, -0.42, 0.22), (0, -1.3, 0.0), 22, "#ff5a3a", 0.4, 0.15),
        C.area("jb_dome_glow", (0, -0.45, 1.3), (0, -3.0, 1.0), 18, "#ffa060", 0.55, 0.3)]
for o in L_IN:
    o.parent = model.pivot


# ---------------------------------------------------------------- set materials
def checker(name, size=0.3, a="#e6e0d0", b="#121212"):
    """Waxed black/white checker tiles (world space): per-tile tint, grout, scuffs, grime, roughness breakup."""
    m, nt, out = C.new_mat(name)
    M, wn = _ops(nt)
    v = C.coords(nt, "world")
    s = C.N(nt, "SeparateXYZ", {"Vector": v})
    gx = M("DIVIDE", s.outputs[0], size); gy = M("DIVIDE", s.outputs[1], size)
    ix = M("FLOOR", gx); iy = M("FLOOR", gy)
    chk = M("MODULO", M("ABSOLUTE", M("ADD", ix, iy)), 2.0)
    tint = C.maprange(nt, wn(ix, iy), 0, 1, 0.9, 1.05)
    c = C.mix(nt, chk, a, b)
    c = C.mix(nt, 1.0, c, C.N(nt, "CombineXYZ", {"X": tint, "Y": tint, "Z": tint}).outputs[0], blend="MULTIPLY")
    fx = M("ABSOLUTE", M("SUBTRACT", M("FRACT", gx), 0.5)); fy = M("ABSOLUTE", M("SUBTRACT", M("FRACT", gy), 0.5))
    grout = C.maprange(nt, M("MAXIMUM", fx, fy), 0.485, 0.495)
    n_big = C.noise(nt, v, 0.7, 5, 0.6); n_fine = C.noise(nt, v, 25.0, 5, 0.6)
    scuff = C.noise(nt, C.vmath(nt, "MULTIPLY", v, (1.0, 6.0, 1.0)), 4.0, 6, 0.65)
    scuffm = M("MULTIPLY", C.maprange(nt, scuff, 0.58, 0.7), 0.7)
    grime = M("MULTIPLY", C.maprange(nt, n_big, 0.45, 0.75), 0.55)
    c = C.mix(nt, grime, c, "#3a2c1e")
    c = C.mix(nt, M("MULTIPLY", scuffm, M("SUBTRACT", 1.0, chk)), c, "#8f8676")
    c = C.mix(nt, M("MULTIPLY", scuffm, chk), c, "#4a4640")
    c = C.mix(nt, grout, c, "#2a241c")
    r = C.maprange(nt, n_fine, 0.3, 0.7, 0.1, 0.24)
    r = C.mixf(nt, M("MAXIMUM", scuffm, grime), r, 0.5)
    r = C.mixf(nt, grout, r, 0.8)
    C.principled(nt, out, color=c, rough=r, coat=0.3, coat_rough=0.08,
                 normal=C.bump(nt, M("SUBTRACT", M("MULTIPLY", n_fine, 0.05), grout), 0.25, 0.002))
    return m


def subway_tile(name, plane="XZ", color="#5d8a74", grout="#2d2a24"):
    """Glazed subway tiles via the Brick texture on (x|y, z); crazing/grime toward the bottom, glossy glaze."""
    m, nt, out = C.new_mat(name)
    M, wn = _ops(nt)
    v = C.coords(nt, "world")
    s = C.N(nt, "SeparateXYZ", {"Vector": v})
    h = s.outputs[0] if plane == "XZ" else s.outputs[1]
    uv = C.N(nt, "CombineXYZ", {"X": h, "Y": s.outputs[2]}).outputs[0]
    br = C.N(nt, "TexBrick", {"Vector": uv, "Color1": C.col(color), "Color2": C.col(color), "Mortar": C.col(grout),
                              "Scale": 1.0, "Mortar Size": 0.004, "Mortar Smooth": 0.3, "Bias": 0.0,
                              "Brick Width": 0.15, "Row Height": 0.075}, offset=0.5, offset_frequency=2)
    mortar = br.outputs["Fac"]
    n_big = C.noise(nt, v, 1.2, 5, 0.6); n_fine = C.noise(nt, v, 40.0, 4, 0.6)
    tv = C.maprange(nt, C.noise(nt, C.vmath(nt, "MULTIPLY", uv, (6.6, 13.3, 1.0)), 2.0, 1, 0.5), 0.3, 0.7, 0.92, 1.05)
    c = C.mix(nt, 1.0, br.outputs["Color"], C.N(nt, "CombineXYZ", {"X": tv, "Y": tv, "Z": tv}).outputs[0], blend="MULTIPLY")
    grime = M("MULTIPLY", C.maprange(nt, n_big, 0.45, 0.8), 0.6)
    grime = M("MAXIMUM", grime, M("MULTIPLY", C.maprange(nt, s.outputs[2], 1.4, 1.05), 0.35))
    c = C.mix(nt, grime, c, "#4a3a22")
    r = C.mixf(nt, mortar, C.maprange(nt, n_fine, 0.3, 0.7, 0.08, 0.2), 0.85)
    r = C.mixf(nt, grime, r, 0.45)
    C.principled(nt, out, color=c, rough=r, coat=0.4, coat_rough=0.05,
                 normal=C.bump(nt, M("SUBTRACT", 0.0, mortar), 0.4, 0.003))
    return m


def wainscot(name, plane="XZ", color="#5a2e18", pitch=0.1):
    """Vertical beadboard: grooves every `pitch` m, wood streaks along Z, varnish worn near the floor."""
    m, nt, out = C.new_mat(name)
    M, wn = _ops(nt)
    v = C.coords(nt, "world")
    s = C.N(nt, "SeparateXYZ", {"Vector": v})
    h = s.outputs[0] if plane == "XZ" else s.outputs[1]
    fr = M("FRACT", M("DIVIDE", h, pitch))
    groove = C.maprange(nt, M("ABSOLUTE", M("SUBTRACT", fr, 0.5)), 0.47, 0.49)
    board = M("FLOOR", M("DIVIDE", h, pitch))
    streak = C.noise(nt, C.vmath(nt, "MULTIPLY", v, (30.0, 30.0, 1.2)), 2.0, 5, 0.6)
    tint = C.maprange(nt, wn(board, 1.0), 0, 1, 0.8, 1.15)
    c = C.mix(nt, C.maprange(nt, streak, 0.35, 0.7), color, tuple(x * 0.55 for x in C.col(color)[:3]))
    c = C.mix(nt, 1.0, c, C.N(nt, "CombineXYZ", {"X": tint, "Y": tint, "Z": tint}).outputs[0], blend="MULTIPLY")
    wear = M("MULTIPLY", C.maprange(nt, s.outputs[2], 0.35, 0.05), C.maprange(nt, C.noise(nt, v, 8.0, 5, 0.6), 0.4, 0.6))
    c = C.mix(nt, M("MULTIPLY", wear, 0.6), c, "#8a6a4a")
    c = C.mix(nt, groove, c, "#120804")
    r = C.mixf(nt, wear, C.maprange(nt, streak, 0.3, 0.7, 0.25, 0.4), 0.7)
    C.principled(nt, out, color=c, rough=r, coat=0.35, coat_rough=0.2,
                 normal=C.bump(nt, M("SUBTRACT", M("MULTIPLY", streak, 0.05), groove), 0.4, 0.004))
    return m


def dusk_card(name):
    """Blue-hour sky seen through the window: deep blue -> violet -> warm horizon, with out-of-focus street
    lights and lit windows across the street."""
    m, nt, out = C.new_mat(name)
    M, wn = _ops(nt)
    v = C.coords(nt, "world")
    s = C.N(nt, "SeparateXYZ", {"Vector": v})
    z = s.outputs[2]
    c = C.mix(nt, C.maprange(nt, z, 0.4, 1.6), "#d07a58", "#3a3a8a")
    c = C.mix(nt, C.maprange(nt, z, 1.6, 3.4), c, "#0b1640")
    # building silhouettes across the street with warm windows
    bx = M("FLOOR", M("DIVIDE", s.outputs[1], 0.9))
    bh = C.maprange(nt, wn(bx, 3.0), 0, 1, 0.9, 2.2)
    bld = M("LESS_THAN", z, bh)
    win = M("MULTIPLY", M("LESS_THAN", M("FRACT", M("DIVIDE", s.outputs[1], 0.18)), 0.5),
            M("LESS_THAN", M("FRACT", M("DIVIDE", z, 0.22)), 0.45))
    win = M("MULTIPLY", win, M("GREATER_THAN", wn(M("FLOOR", M("DIVIDE", s.outputs[1], 0.18)), M("FLOOR", M("DIVIDE", z, 0.22)), 5.0), 0.6))
    c = C.mix(nt, bld, c, "#0a0c18")
    c = C.mix(nt, M("MULTIPLY", bld, win), c, "#ffb860")
    em = C.N(nt, "Emission", {"Strength": 0.6})
    C._sock_set(em.inputs["Color"], c)
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- set: diner corner
BACK, FRONT, XL, XR, H = 0.62, -4.2, -1.85, 3.4, 2.8
WIN_Y0, WIN_Y1, WIN_Z0, WIN_Z1 = -2.2, -0.35, 0.95, 2.25     # window in the left wall
WAIN = 1.0

M_FLOOR = checker("jb_checker")
M_TILE_B = subway_tile("jb_tile_back", "XZ")
M_TILE_L = subway_tile("jb_tile_left", "YZ")
M_WAIN_B = wainscot("jb_wain_back", "XZ")
M_WAIN_L = wainscot("jb_wain_left", "YZ")
M_CREAM = C.material("painted", "jb_cream", color="#e3d6b8", rough=0.45, grime=0.6, wear=0.3, panels=None, space="world",
                     scale=0.5)
M_RED_BAND = C.material("painted", "jb_redband", color="#9e1f1a", rough=0.4, grime=0.5, wear=0.3, panels=None,
                        space="world", scale=0.5)
M_CEIL = C.material("painted", "jb_ceiling", color="#c9bea4", rough=0.7, grime=0.7, wear=0.0, panels=(0.6, 0.6, 1000),
                    seam_width=0.006, space="world")
M_CHROME = C.material("metal", "jb_set_chrome", color="#e2e6ea", rough=0.08, grime=0.25, space="world")
M_VINYL = C.material("leather", "jb_vinyl_red", color="#8e1a18", rough=0.32, space="world")
M_FORMICA = C.material("plastic", "jb_formica", color="#cfe0d2", rough=0.3, coat=0.3, space="world")
M_GREEN_ENAMEL = C.material("painted", "jb_enamel", color="#2f5a3e", rough=0.3, grime=0.4, wear=0.5, panels=None,
                            space="world", under="#3a3a3a", scale=0.3, coat=0.4)
M_BULB = C.material("emissive", "jb_bulb", color=C.kelvin(2500), strength=40.0)
M_NEON_RED = C.material("emissive", "jb_neon_red", color="#ff2a1a", strength=20.0, base="#ff2a1a")
M_NEON_AMBER = C.material("emissive", "jb_neon_amber", color="#ffaa3a", strength=16.0, base="#ffaa3a")
M_NEON_BLUE = C.material("emissive", "jb_neon_blue", color="#3a7aff", strength=16.0, base="#3a7aff")
M_DARKMETAL = C.material("painted", "jb_darkmetal", color="#1a1a1c", rough=0.45, metal=0.5, grime=0.4, wear=0.4,
                         panels=None, space="world")
M_BOARD = C.material("painted", "jb_board", color="#1d2a22", rough=0.7, grime=0.5, wear=0.2, panels=None, space="world")
M_CHALK = C.material("flat", "jb_chalk", color="#ece6d6", rough=0.8)
M_BLIND = C.material("plastic", "jb_blind", color="#e8e0cc", rough=0.45, space="world")

C.plane("floor", (XR - XL, BACK - FRONT), ((XL + XR) / 2, (BACK + FRONT) / 2, 0), mat=M_FLOOR)
# back wall: wainscot + chrome cap rail + tiles + red band
C.box("wall_back_wain", (XR - XL, 0.05, WAIN), ((XL + XR) / 2, BACK + 0.025, 0), mat=M_WAIN_B, origin="bottom", bevel=0)
C.box("wall_back_tile", (XR - XL, 0.05, H - WAIN), ((XL + XR) / 2, BACK + 0.03, WAIN), mat=M_TILE_B, origin="bottom", bevel=0)
C.box("rail_back", (XR - XL, 0.035, 0.035), ((XL + XR) / 2, BACK - 0.005, WAIN), mat=M_CHROME, bevel=0.008)
C.box("band_back", (XR - XL, 0.02, 0.1), ((XL + XR) / 2, BACK + 0.005, 2.25), mat=M_RED_BAND, bevel=0.004)
C.box("skirt_back", (XR - XL, 0.025, 0.09), ((XL + XR) / 2, BACK - 0.01, 0), mat=M_DARKMETAL, origin="bottom", bevel=0.004)
# left wall with a window opening
def lwall(name, y0, y1, z0, z1, mat):
    C.box(name, (0.12, y1 - y0, z1 - z0), (XL - 0.06, (y0 + y1) / 2, z0), mat=mat, origin="bottom", bevel=0)


for nm, z0, z1, mat in (("w", 0, WAIN, M_WAIN_L), ("t", WAIN, H, M_TILE_L)):
    lwall(f"wallL_a_{nm}", WIN_Y1, BACK, z0, z1, mat)
    lwall(f"wallL_b_{nm}", FRONT, WIN_Y0, z0, z1, mat)
lwall("wallL_sill", WIN_Y0, WIN_Y1, 0, WIN_Z0, M_WAIN_L)
lwall("wallL_head", WIN_Y0, WIN_Y1, WIN_Z1, H, M_TILE_L)
C.box("rail_left", (0.035, BACK - FRONT, 0.035), (XL + 0.005, (BACK + FRONT) / 2, WAIN), mat=M_CHROME, bevel=0.008)
C.box("band_left", (0.02, BACK - FRONT, 0.1), (XL - 0.005, (BACK + FRONT) / 2, 2.25), mat=M_RED_BAND, bevel=0.004)
# window frame, sill, blinds (half open: cool light falls through in stripes)
for k, (y, z, sy, sz) in enumerate(((WIN_Y0, (WIN_Z0 + WIN_Z1) / 2, 0.06, WIN_Z1 - WIN_Z0), (WIN_Y1, (WIN_Z0 + WIN_Z1) / 2, 0.06, WIN_Z1 - WIN_Z0),
                                    ((WIN_Y0 + WIN_Y1) / 2, WIN_Z1, WIN_Y1 - WIN_Y0 + 0.06, 0.06),
                                    ((WIN_Y0 + WIN_Y1) / 2, (WIN_Z0 + WIN_Z1) / 2, 0.04, WIN_Z1 - WIN_Z0))):
    C.box(f"winframe_{k}", (0.16, sy, sz), (XL - 0.04, y, z), mat=M_CREAM, bevel=0.008)
C.box("win_sill", (0.24, WIN_Y1 - WIN_Y0 + 0.16, 0.04), (XL + 0.02, (WIN_Y0 + WIN_Y1) / 2, WIN_Z0 - 0.02), mat=M_CREAM,
      bevel=0.01)
nsl = 26
for k in range(nsl):
    z = WIN_Z1 - 0.06 - k * (WIN_Z1 - WIN_Z0 - 0.12) / (nsl - 1)
    if k > 19:      # blind pulled up a little: open gap at the bottom
        continue
    C.box(f"slat_{k}", (0.05, WIN_Y1 - WIN_Y0 - 0.06, 0.004), (XL + 0.03, (WIN_Y0 + WIN_Y1) / 2, z), (0, 35, 0),
          mat=M_BLIND, bevel=0.0)
C.box("blind_rail", (0.06, WIN_Y1 - WIN_Y0 - 0.04, 0.03), (XL + 0.03, (WIN_Y0 + WIN_Y1) / 2, WIN_Z1 - 0.03),
      mat=M_BLIND, bevel=0.005)
# neon OPEN sign hanging in the window, facing the street (reads mirrored from inside)
C.text("neon_open", "OPEN", 0.16, (XL + 0.1, (WIN_Y0 + WIN_Y1) / 2 + 0.25, 1.15), (90, 0, 90), M_NEON_BLUE, C.FONT_LATIN,
       extrude=0.006, role="keep")
sky =C.plane("dusk", (14, 5), (XL - 3.5, -1.0, 1.6), (90, 0, 90), dusk_card("jb_dusk"), role="keep")
sky.visible_shadow = False
# ceiling
C.box("ceiling", (XR - XL + 0.3, BACK - FRONT + 0.3, 0.1), ((XL + XR) / 2, (BACK + FRONT) / 2, H), mat=M_CEIL,
      origin="bottom", bevel=0)
C.box("wall_right", (0.12, BACK - FRONT, H), (XR + 0.06, (BACK + FRONT) / 2, 0), mat=M_TILE_L, origin="bottom", bevel=0)
C.box("wall_front", (XR - XL + 0.3, 0.12, H), ((XL + XR) / 2, FRONT - 0.06, 0), mat=M_TILE_B, origin="bottom", bevel=0)

# booth on the right: red vinyl seat + back with chrome edging, formica table with chrome band and pedestal
BX0, BX1 = 1.4, 3.1
C.box("booth_base", (BX1 - BX0, 0.55, 0.42), ((BX0 + BX1) / 2, BACK - 0.3, 0), mat=M_DARKMETAL, origin="bottom", bevel=0.01)
C.box("booth_seat", (BX1 - BX0, 0.58, 0.1), ((BX0 + BX1) / 2, BACK - 0.32, 0.42), mat=M_VINYL, origin="bottom", bevel=0.04)
for k in range(4):   # channel-tufted back cushions
    w = (BX1 - BX0) / 4
    C.box(f"booth_back_{k}", (w - 0.015, 0.14, 0.62), (BX0 + w * (k + 0.5), BACK - 0.09, 0.5), (-6, 0, 0), mat=M_VINYL,
          origin="bottom", bevel=0.05)
C.box("booth_trim", (BX1 - BX0, 0.02, 0.025), ((BX0 + BX1) / 2, BACK - 0.61, 0.43), mat=M_CHROME, bevel=0.006)
C.box("booth_cap", (BX1 - BX0 + 0.04, 0.2, 0.04), ((BX0 + BX1) / 2, BACK - 0.08, 1.13), mat=M_CHROME, bevel=0.01)
C.box("booth_end", (0.06, 0.62, 1.16), (BX0 - 0.03, BACK - 0.3, 0), mat=M_RED_BAND, origin="bottom", bevel=0.02)
TB = ((BX0 + BX1) / 2 + 0.1, -0.55)
C.cylinder("table_ped", 0.04, 0.72, (TB[0], TB[1], 0), mat=M_CHROME, origin="bottom")
C.cylinder("table_foot", 0.25, 0.03, (TB[0], TB[1], 0), mat=M_CHROME, origin="bottom", segments=40)
C.box("table_top", (1.15, 0.72, 0.035), (TB[0], TB[1], 0.72), mat=M_FORMICA, origin="bottom", bevel=0.012)
C.box("table_band", (1.17, 0.74, 0.03), (TB[0], TB[1], 0.715), mat=M_CHROME, origin="bottom", bevel=0.01)
# table dressing: napkin dispenser, sugar pourer, ketchup, a coffee cup on its saucer
C.box("napkin", (0.12, 0.08, 0.13), (TB[0] - 0.3, TB[1] + 0.2, 0.755), mat=M_CHROME, origin="bottom", bevel=0.012)
C.cylinder("sugar", 0.035, 0.12, (TB[0] - 0.15, TB[1] + 0.24, 0.755), mat=C.material("glass", "jb_glass_set",
           color="#e8f0f0"), origin="bottom", segments=24)
C.cylinder("sugar_cap", 0.037, 0.04, (TB[0] - 0.15, TB[1] + 0.24, 0.875), mat=M_CHROME, origin="bottom", segments=24)
C.cylinder("ketchup", 0.03, 0.17, (TB[0] - 0.05, TB[1] + 0.22, 0.755), mat=C.material("plastic", "jb_ketchup",
           color="#a8140e", rough=0.25, coat=0.5, space="world"), origin="bottom", segments=24)
C.cylinder("saucer", 0.075, 0.012, (TB[0] - 0.2, TB[1] - 0.12, 0.755), mat=C.material("plastic", "jb_china",
           color="#efe9dc", rough=0.15, coat=0.6, space="world"), origin="bottom", segments=32)
C.cylinder("cup", 0.042, 0.075, (TB[0] - 0.2, TB[1] - 0.12, 0.767), mat=C.material("plastic", "jb_china"), origin="bottom",
           segments=32)

# bar stool in the left foreground (chrome + red vinyl, as in the diner study)
SX, SY = -1.3, -1.2
C.cylinder("stool_foot", 0.2, 0.03, (SX, SY, 0), mat=M_CHROME, origin="bottom", segments=32)
C.cylinder("stool_post", 0.032, 0.66, (SX, SY, 0.03), mat=C.material("metal", "jb_dark_chrome", color="#2a2a2c",
           rough=0.2, space="world"), origin="bottom", segments=16)
for k in range(4):
    C.cylinder(f"stool_band_{k}", 0.2 - k * 0.003, 0.025, (SX, SY, 0.66 + k * 0.026), mat=M_CHROME, segments=40,
               origin="bottom")
C.cylinder("stool_seat", 0.21, 0.07, (SX, SY, 0.765), mat=M_VINYL, segments=40, origin="bottom")

# green enamel pendant over the booth table and one by the jukebox
for k, (px, py, pz) in enumerate(((TB[0], TB[1], 1.75), (-0.35, -0.75, 2.05))):
    C.pipe(f"pend_cord_{k}", (px, py, H), (px, py, pz + 0.16), 0.006, M_DARKMETAL)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=32, radius1=0.24, radius2=0.06, depth=0.18)
    C._obj_from_bm(f"pend_cone_{k}", bm, M_GREEN_ENAMEL, (px, py, pz + 0.02), role="set", smooth=True)
    C.cylinder(f"pend_cap_{k}", 0.065, 0.04, (px, py, pz + 0.12), mat=M_GREEN_ENAMEL, segments=24)
    C.cylinder(f"pend_bulb_{k}", 0.045, 0.06, (px, py, pz - 0.06), mat=M_BULB, segments=16, role="keep")
    C.spot(f"pend_spot_{k}", (px, py, pz - 0.08), (px, py, 0.0), 150 if k == 0 else 6, C.kelvin(2900), 60, 0.5, 0.05)
    C.point(f"pend_pt_{k}", (px, py, pz - 0.05), 6 if k == 0 else 2, C.kelvin(2700), 0.05)

# neon signs on the back wall over the booth (warm: red + amber), menu board, a wall clock
C.box("neon_back", (1.3, 0.03, 0.5), ((BX0 + BX1) / 2, BACK - 0.03, 1.72), mat=M_DARKMETAL, bevel=0.01)
C.text("neon_diner", "DINER", 0.2, ((BX0 + BX1) / 2, BACK - 0.06, 1.82), (90, 0, 0), M_NEON_RED, C.FONT_STENCIL,
       extrude=0.008, spacing=1.15, role="keep")
C.text("neon_tc", "冰果室", 0.13, ((BX0 + BX1) / 2, BACK - 0.06, 1.58), (90, 0, 0), M_NEON_AMBER, C.FONT_TC, extrude=0.008,
       role="keep")
C.box("menu", (0.7, 0.03, 0.5), (-1.05, BACK - 0.02, 1.62), mat=M_BOARD, bevel=0.01)
C.box("menu_frame", (0.74, 0.02, 0.54), (-1.05, BACK - 0.005, 1.62), mat=C.material("wood", "jb_frame", color="#5a3520",
      rough=0.4, space="world"), bevel=0.01)
C.text("menu_t", "MENU  菜單", 0.06, (-1.05, BACK - 0.037, 1.79), (90, 0, 0), M_CHALK, C.FONT_TC)
C.text("menu_l", "咖啡 COFFEE ....... 25\n紅茶 BLACK TEA ... 20\n聖代 SUNDAE ...... 40\n三明治 SANDWICH . 35",
       0.032, (-1.05, BACK - 0.037, 1.58), (90, 0, 0), M_CHALK, C.FONT_TC)
C.cylinder("clock_rim", 0.17, 0.05, (0.0, BACK - 0.04, 2.0), (90, 0, 0), M_CHROME, 48)
C.cylinder("clock_face", 0.15, 0.052, (0.0, BACK - 0.04, 2.0), (90, 0, 0), M_CREAM, 48)
for k in range(12):
    a = math.radians(k * 30)
    C.box(f"clock_tick_{k}", (0.008, 0.004, 0.025), (0.125 * math.sin(a), BACK - 0.068, 2.0 + 0.125 * math.cos(a)),
          (0, a * 180 / math.pi, 0), mat=M_DARKMETAL, bevel=0)
C.box("clock_h", (0.012, 0.004, 0.08), (0.02, BACK - 0.07, 2.03), (0, 35, 0), mat=M_DARKMETAL, bevel=0)
C.box("clock_m", (0.008, 0.004, 0.12), (-0.03, BACK - 0.072, 2.04), (0, -40, 0), mat=M_DARKMETAL, bevel=0)

# ---------------------------------------------------------------- lighting
C.world("#020306", 1.0)
# cool dusk light through the window blinds (rim on the jukebox's left side, stripes on the floor)
C.area("window_sky", (XL - 1.2, (WIN_Y0 + WIN_Y1) / 2 + 0.6, 2.3), (0.0, 0.35, 1.0), 320, "#6f95ff", 1.2, 1.0)

# warm key on the jukebox front (tungsten, kept above 4000 K so the wood is not orange mush)
C.area("cab_kick", (1.5, -1.9, 2.4), (0.0, -0.1, 0.9), 14, C.kelvin(4200), 0.5)   # glossy highlights on the walnut

C.haze("haze", ((XL + XR) / 2, (BACK + FRONT) / 2, H / 2), (XR - XL - 0.05, BACK - FRONT - 0.05, H - 0.02), 0.01,
       "#ffeedd", 0.5)
for nm in ("jb_neon_blue", "jb_bulb"):
    mm = bpy.data.materials.get(nm)
    if mm is not None:
        mm.cycles.emission_sampling = "NONE"

# ---------------------------------------------------------------- shots
SHOTS = [
    C.Shot("hero", dict(loc=(2.1, -4.0, 1.0), target=(-0.32, 0.1, 0.8), lens=55, fstop=2.8, focus=(0.0, -0.35, 0.85)),
           "打烊後的冰果室：點唱機是屋裡最亮的東西，燈管與頂窗的彩光灑在格子地板上，窗外只剩一點藍色天光。", kind="hero"),
    C.Shot("card", dict(loc=(1.25, -2.35, 1.3), target=(0.0, 0.0, 0.8), lens=36),
           "三分之四前側視角，點唱機靠在老式冰果室的牆角。", kind="card"),
    C.Shot("s1", dict(loc=(-1.2, -3.0, 1.2), target=(0.05, 0.0, 0.8), lens=33),
           "三分之四前視：木質機身、鍍鉻橫條、菱格網與 U 形燈管。"),
    C.Shot("s2", dict(loc=(1.85, -1.55, 1.0), target=(-0.1, 0.1, 0.82), lens=24),
           "側面：從卡座這一側看過去，窗外的冷光在木頭機身與鍍鉻橫條上勾出輪廓。"),
    C.Shot("s3", dict(loc=(0.55, -0.95, 1.22), target=(0.0, -0.33, 1.07), lens=55, fstop=2.2, focus=(0.1, -0.37, 1.05)),
           "選曲面板特寫：鍍鉻橫條的反光、一張張曲目卡，上方是放射紋頂窗。", exposure=-1.45),
    C.Shot("s4", dict(loc=(0.55, -1.15, 0.62), target=(0.0, -0.32, 0.45), lens=45, fstop=2.8, focus=(0.12, -0.34, 0.45)),
           "菱格網特寫：鍍鉻菱格、後方透光的喇叭布與 U 形燈管的漸層色。", exposure=-1.2),
]
CAPTIONS = {"clay": "白模：與三分之四前視同一鏡頭，只看造型與比例。",
            "wire": "線框：同一鏡頭顯示模型的實際四邊形佈線。"}
TURN = dict(loc=(0.0, -2.9, 1.05), target=(0.0, 0.0, 0.78), lens=34)

# Turntable only: the room is dark and the cabinet's own glow faces forward, so its back half would spin past as
# a black silhouette. Two soft fills near the camera are switched on just for the turntable frames.
_turn_fills = [C.area("turn_fill_L", (-1.5, -3.3, 2.1), (0.0, 0.0, 0.9), 60, C.kelvin(4600), 1.6),
               C.area("turn_fill_R", (2.2, -2.8, 1.3), (0.0, 0.0, 0.8), 32, C.kelvin(5400), 1.2)]
for _o in _turn_fills:
    _o.hide_render = True
_render_turntable = C.render_turntable


def _turntable_with_fill(*a, **k):
    for o in _turn_fills:
        o.hide_render = False
    try:
        return _render_turntable(*a, **k)
    finally:
        for o in _turn_fills:
            o.hide_render = True


C.render_turntable = _turntable_with_fill

C.run(args, "jukebox", model, SHOTS, clay_wire_of="s1", turn=TURN, turn_mode="model", captions_extra=CAPTIONS)
