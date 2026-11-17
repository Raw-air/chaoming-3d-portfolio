"""CRASH cockpit control console (key 'console', 操控台.fbx) on the bridge of the ship, storm outside.

  & $blender -b --factory-startup --python tools\\render\\scene_console.py -- --quality draft [--only hero,s1] [--turn] [--out DIR]

The console is a pedestal helm (1.35 m): base plate, column with red side insets, a sloped key desk with two amber
lamps, and a tilted screen with a red back panel. The screen face and the desk top get procedural HUD / keypad
materials (assigned per face here, the source mesh has a single material per part).
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402
import common as C  # noqa: E402

args = C.parse_args()
C.reset()

# ---------------------------------------------------------------- model
model = C.load("console", size=1.35)
mn, mx = model.bounds
C.log("console bounds", [round(v, 3) for v in mn], [round(v, 3) for v in mx])
SC = 0.4   # texture scale for a small prop (finer grime/wear than the 12 m ship)
LOOKS = {
    "con_body": ("painted", dict(color="#56636b", rough=0.4, metal=0.25, grime=0.65, wear=0.75, panels=None, scale=SC,
                                 grime_color="#1a1612", under="#b8bec4", streaks=0.6)),
    "con_panel": ("painted", dict(color="#323a42", rough=0.45, metal=0.3, grime=0.6, wear=0.8, panels=None, scale=SC,
                                  grime_color="#120f0c", under="#a9b0b6")),
    "con_accent": ("painted", dict(color="#9a2b22", rough=0.38, grime=0.55, wear=0.7, panels=None, scale=SC,
                                   grime_color="#1d0f0a", under="#a3a7ab")),
    "metal_dark": ("metal", dict(color="#3a3f45", rough=0.38, grime=0.5, scale=SC, brushed=0.3)),
    "emit_red": ("emissive", dict(color="#ff2a1f", strength=7.0, base="#200404")),
    "emit_amber": ("emissive", dict(color="#ffa22e", strength=14.0, base="#2a1503")),
}
C.apply_looks(model.objs, LOOKS)


# ---------------------------------------------------------------- tiny node helpers (scene-local)
def _m(nt, op, a, b=None, clamp=False):
    return C.mathn(nt, op, a, b, clamp)


def inrange(nt, x, a, b):
    return _m(nt, "MULTIPLY", _m(nt, "GREATER_THAN", x, a), _m(nt, "LESS_THAN", x, b))


def line_mask(nt, x, w):
    """1 near the integer grid of x (thin lines of half-width w in [0,0.5])."""
    f = _m(nt, "ABSOLUTE", _m(nt, "SUBTRACT", _m(nt, "FRACT", x), 0.5))
    return C.maprange(nt, f, 0.5 - w * 1.6, 0.5 - w * 0.6, 0.0, 1.0)


def wnoise(nt, a, b):
    v = C.N(nt, "CombineXYZ", {"X": a, "Y": b, "Z": 0.37}).outputs[0]
    return C.N(nt, "TexWhiteNoise", {"Vector": v}, noise_dimensions="3D").outputs["Value"]


def face_frame(o, faces, t):
    """u = x, v = dot(p, t) range over the given faces (object-space metres)."""
    t = Vector(t).normalized()
    us = []; vs = []
    for p in faces:
        for vi in p.vertices:
            co = o.data.vertices[vi].co
            us.append(co.x); vs.append(co.dot(t))
    return min(us), max(us), min(vs), max(vs), t


def uv_nodes(nt, frame):
    u0, u1, v0, v1, t = frame
    P = C.coords(nt)
    x = C.N(nt, "SeparateXYZ", {"Vector": P}).outputs[0]
    d = C.vmath(nt, "DOT_PRODUCT", P, tuple(t), out=1)
    return C.maprange(nt, x, u0, u1), C.maprange(nt, d, v0, v1), (u1 - u0) / max(v1 - v0, 1e-6)


def hud_material(name, frame, strength=5.0):
    """Procedural flight HUD: grid, radar with sweep + blips, bar graph, text rows, red alert banner."""
    m, nt, out = C.new_mat(name)
    U, V, asp = uv_nodes(nt, frame)
    teal, amber, red, white = C.col("#2dfdd8"), C.col("#ffae3a"), C.col("#ff2b22"), C.col("#d8fff6")
    col = C.col("#021614")
    # grid
    g = _m(nt, "MAXIMUM", line_mask(nt, _m(nt, "MULTIPLY", U, 14.0), 0.03), line_mask(nt, _m(nt, "MULTIPLY", V, 9.0), 0.03))
    col = C.mix(nt, _m(nt, "MULTIPLY", g, 0.35), col, C.col("#0b6e60"))
    # radar
    cu, cv, R = 0.27 * asp, 0.47, 0.36
    ua = _m(nt, "SUBTRACT", _m(nt, "MULTIPLY", U, asp), cu)
    vb = _m(nt, "SUBTRACT", V, cv)
    r = C.vmath(nt, "LENGTH", C.N(nt, "CombineXYZ", {"X": ua, "Y": vb}).outputs[0], out=1)
    inside = _m(nt, "LESS_THAN", r, R)
    rings = _m(nt, "MULTIPLY", line_mask(nt, _m(nt, "MULTIPLY", r, 1.0 / (R / 3)), 0.04), inside)
    outer = C.maprange(nt, _m(nt, "ABSOLUTE", _m(nt, "SUBTRACT", r, R)), 0.012, 0.004)
    cross = _m(nt, "MULTIPLY", _m(nt, "MAXIMUM", C.maprange(nt, _m(nt, "ABSOLUTE", ua), 0.006, 0.002),
                                  C.maprange(nt, _m(nt, "ABSOLUTE", vb), 0.006, 0.002)), inside)
    ang = _m(nt, "ARCTAN2", vb, ua)
    sw = _m(nt, "FRACT", _m(nt, "ADD", _m(nt, "DIVIDE", ang, 2 * math.pi), 0.62))
    sweep = _m(nt, "MULTIPLY", _m(nt, "POWER", sw, 7.0), inside)
    blip = None
    for (bx, by) in ((0.12, 0.1), (-0.15, 0.17), (0.2, -0.13), (-0.05, -0.24)):
        d = C.vmath(nt, "LENGTH", C.N(nt, "CombineXYZ", {"X": _m(nt, "SUBTRACT", ua, bx),
                                                       "Y": _m(nt, "SUBTRACT", vb, by)}).outputs[0], out=1)
        b = C.maprange(nt, d, 0.022, 0.01)
        blip = b if blip is None else _m(nt, "MAXIMUM", blip, b)
    col = C.mix(nt, _m(nt, "MULTIPLY", sweep, 0.8), col, teal)
    col = C.mix(nt, _m(nt, "MAXIMUM", _m(nt, "MAXIMUM", rings, outer), cross), col, teal)
    col = C.mix(nt, blip, col, red)
    # bar graph (right, lower)
    bu = _m(nt, "MULTIPLY", U, 34.0)
    bi = _m(nt, "FLOOR", bu)
    h = _m(nt, "ADD", 0.14, _m(nt, "MULTIPLY", wnoise(nt, bi, 3.0), 0.3))
    bars = _m(nt, "MULTIPLY", _m(nt, "MULTIPLY", inrange(nt, U, 0.6, 0.95), inrange(nt, V, 0.12, 1.0)),
              _m(nt, "MULTIPLY", _m(nt, "LESS_THAN", V, h), inrange(nt, _m(nt, "FRACT", bu), 0.18, 0.82)))
    col = C.mix(nt, bars, col, C.mix(nt, C.maprange(nt, V, 0.2, 0.42), teal, amber))
    # text rows (right, upper)
    rows = _m(nt, "MULTIPLY", V, 30.0)
    ri = _m(nt, "FLOOR", rows)
    seg = _m(nt, "FLOOR", _m(nt, "MULTIPLY", U, 70.0))
    glyph = _m(nt, "GREATER_THAN", wnoise(nt, ri, seg), 0.3)
    word = _m(nt, "GREATER_THAN", wnoise(nt, ri, _m(nt, "FLOOR", _m(nt, "MULTIPLY", U, 11.0))), 0.22)
    rowlen = _m(nt, "LESS_THAN", U, _m(nt, "ADD", 0.66, _m(nt, "MULTIPLY", wnoise(nt, ri, 9.0), 0.29)))
    txt = _m(nt, "MULTIPLY", _m(nt, "MULTIPLY", glyph, word), rowlen)
    txt = _m(nt, "MULTIPLY", txt, _m(nt, "MULTIPLY", inrange(nt, _m(nt, "FRACT", rows), 0.25, 0.75),
                                      _m(nt, "MULTIPLY", inrange(nt, U, 0.6, 0.95), inrange(nt, V, 0.55, 0.83))))
    txt = _m(nt, "MULTIPLY", txt, inrange(nt, _m(nt, "FRACT", _m(nt, "MULTIPLY", U, 70.0)), 0.12, 0.88))
    col = C.mix(nt, txt, col, white)
    # red alert banner with hazard stripes (top)
    ban = _m(nt, "MULTIPLY", inrange(nt, V, 0.88, 0.96), inrange(nt, U, 0.04, 0.96))
    stripe = _m(nt, "LESS_THAN", _m(nt, "FRACT", _m(nt, "MULTIPLY", _m(nt, "ADD", _m(nt, "MULTIPLY", U, asp), V), 18.0)), 0.5)
    col = C.mix(nt, _m(nt, "MULTIPLY", ban, _m(nt, "ADD", 0.45, _m(nt, "MULTIPLY", stripe, 0.55))), col, red)
    # frame + vignette + scanlines
    edge = _m(nt, "MAXIMUM", _m(nt, "MAXIMUM", C.maprange(nt, U, 0.025, 0.015), C.maprange(nt, U, 0.975, 0.985)),
              _m(nt, "MAXIMUM", C.maprange(nt, V, 0.03, 0.02), C.maprange(nt, V, 0.97, 0.98)))
    col = C.mix(nt, edge, col, teal)
    scan = C.maprange(nt, line_mask(nt, _m(nt, "MULTIPLY", V, 160.0), 0.25), 0, 1, 1.0, 0.6)
    vig = C.maprange(nt, C.vmath(nt, "LENGTH", C.N(nt, "CombineXYZ", {"X": _m(nt, "SUBTRACT", U, 0.5),
                                                                       "Y": _m(nt, "SUBTRACT", V, 0.5)}).outputs[0], out=1),
                     0.35, 0.75, 1.0, 0.55)
    s = _m(nt, "MULTIPLY", _m(nt, "MULTIPLY", scan, vig), strength)
    C.principled(nt, out, color="#010203", rough=0.08, coat=1.0, coat_rough=0.04, emit=col, emit_strength=s)
    m["recipe"] = "screen"   # clay/wire keep it lit
    return m


def keypad_material(name, frame, base="#2b3238", cols=17, rows=5, strength=6.0, lit_frac=0.56):
    """Desk of backlit square keys: random red / amber / teal / dark caps, raised (bump), worn base."""
    m, nt, out = C.new_mat(name)
    U, V, asp = uv_nodes(nt, frame)
    ku = _m(nt, "MULTIPLY", U, float(cols)); kv = _m(nt, "MULTIPLY", V, float(rows))
    fu = _m(nt, "ABSOLUTE", _m(nt, "SUBTRACT", _m(nt, "FRACT", ku), 0.5))
    fv = _m(nt, "ABSOLUTE", _m(nt, "SUBTRACT", _m(nt, "FRACT", kv), 0.5))
    box = C.maprange(nt, _m(nt, "MAXIMUM", fu, fv), 0.36, 0.3)
    inner = _m(nt, "MULTIPLY", inrange(nt, U, 0.03, 0.97), inrange(nt, V, 0.06, 0.94))
    key = _m(nt, "MULTIPLY", box, inner)
    rnd = wnoise(nt, _m(nt, "FLOOR", ku), _m(nt, "FLOOR", kv))
    P = C.coords(nt)
    n_f = C.noise(nt, P, 60.0, 5, 0.6)
    shade = C.mix(nt, C.maprange(nt, n_f, 0.3, 0.7, 0.0, 0.35), C.col(base), "#0e0f10")
    cap = C.col("#191b1e")
    ecol = C.col("#000000")
    for lo, hi, c in ((0.0, 0.29, "#ff2b22"), (0.29, 0.64, "#ffa22e"), (0.64, 0.89, "#2dfdd8"), (0.89, 1.0, "#f1f6ff")):
        sel = inrange(nt, rnd, lo * lit_frac, hi * lit_frac)
        ecol = C.mix(nt, sel, ecol, C.col(c))
    lit = _m(nt, "LESS_THAN", rnd, lit_frac)
    # key legend: a small bright bar in the lit caps
    leg = _m(nt, "MULTIPLY", _m(nt, "LESS_THAN", fu, 0.2), _m(nt, "LESS_THAN", fv, 0.06))
    em = _m(nt, "MULTIPLY", key, _m(nt, "ADD", _m(nt, "MULTIPLY", lit, 0.55), _m(nt, "MULTIPLY", leg, 0.6)))
    shade = C.mix(nt, key, shade, cap)
    h = _m(nt, "MULTIPLY", key, 1.0)
    C.principled(nt, out, color=shade, rough=C.mixf(nt, key, C.maprange(nt, n_f, 0.3, 0.7, 0.35, 0.6), 0.3),
                 metal=C.mixf(nt, key, 0.4, 0.0), emit=ecol, emit_strength=_m(nt, "MULTIPLY", em, strength),
                 normal=C.bump(nt, h, 0.6, 0.002))
    m["recipe"] = "screen"
    return m


def faces_where(o, normal, min_area=0.0, tol=0.95):
    n = Vector(normal).normalized()
    return [p for p in o.data.polygons if p.normal.dot(n) > tol and p.area > min_area]


def assign_faces(o, faces, mat):
    o.data.materials.append(mat)
    k = len(o.data.materials) - 1
    for p in faces:
        p.material_index = k


SCREEN_N = (0.0, -0.94, 0.33)
DESK_N = (0.0, -0.63, 0.77)
scr = model.by_name("立方体.036")
f_scr = faces_where(scr, SCREEN_N, 0.02)
fr = face_frame(scr, f_scr, (0.0, 0.33, 0.94))
C.log("screen frame", [round(v, 3) for v in fr[:4]])
assign_faces(scr, f_scr, hud_material("con_hud", fr, 5.0))
desk = model.by_name("立方体.033")
f_desk = faces_where(desk, DESK_N, 0.005)
frd = face_frame(desk, f_desk, (0.0, 0.77, 0.63))
C.log("desk frame", [round(v, 3) for v in frd[:4]])
assign_faces(desk, f_desk, keypad_material("con_keys", frd, "#323a42", cols=19, rows=4, strength=6.0, lit_frac=0.42))
# the red back panel pokes through the screen face. Cycles emission is two-sided, so (1) the panel glows only from
# its front side (Backfacing), and (2) its faces that point at the operator become a dim red status strip.
red = model.by_name("平面.031")
rm_, nt, out = C.new_mat("con_red_oneside")
bf = C.N(nt, "NewGeometry").outputs["Backfacing"]
C.principled(nt, out, color="#200404", rough=0.3, emit=C.col("#ff2a1f"),
             emit_strength=C.mathn(nt, "MULTIPLY", C.mathn(nt, "SUBTRACT", 1.0, bf), 7.0))
rm_["recipe"] = "emissive"
red.data.materials[0] = rm_
assign_faces(red, faces_where(red, SCREEN_N, 0.0, 0.8), C.material("emissive", "con_red_strip", color="#ff2b22",
                                                                    strength=1.4, base="#200404"))

# screen / desk centres (model space == world space before the turntable rotates the pivot)
def centre(o, faces):
    c = Vector()
    for p in faces:
        c += p.center
    return c / max(len(faces), 1)


SCR_C = centre(scr, f_scr); DESK_C = centre(desk, f_desk)
C.log("screen centre", [round(v, 3) for v in SCR_C], "desk centre", [round(v, 3) for v in DESK_C])

# ---------------------------------------------------------------- materials for the set
W, BACK, H = 2.0, -2.8, 2.45          # half width, back wall y, ceiling height
WIN_Y0, WIN_Y1, WIN_Z0, WIN_Z1 = 1.75, 1.35, 0.95, 2.3   # windshield bottom / top y, bottom / top z
WX = 0.95                              # half width of the centre pane

M_DECK = C.material("painted", "deck", color="#2c3136", rough=0.5, metal=0.4, grime=0.75, wear=0.8,
                    panels=(0.6, 0.9, 1000), seam_width=0.006, space="world", scale=0.5, grime_color="#0e0c0a",
                    under="#9aa1a7")
M_WALL = C.material("painted", "wall", color="#3c4a4c", rough=0.55, grime=0.7, wear=0.4, panels=(1000, 0.6, 0.55),
                    seam_width=0.006, space="world", scale=0.5, streaks=0.8, grime_color="#141210")
M_RIB = C.material("painted", "rib", color="#2a3134", rough=0.45, metal=0.3, grime=0.6, wear=0.8, panels=None,
                   space="world", scale=0.5, under="#a0a6aa")
M_CEIL = C.material("painted", "ceil", color="#1f2527", rough=0.6, grime=0.6, wear=0.3, panels=(0.5, 0.7, 1000),
                    space="world", scale=0.5)
M_SILL = C.material("painted", "sill", color="#2b3236", rough=0.45, metal=0.3, grime=0.6, wear=0.8, panels=(0.4, 0.4, 0.3),
                    seam_width=0.004, space="world", scale=0.5, under="#a0a6aa")
M_FRAME = C.material("painted", "frame", color="#1c2124", rough=0.4, metal=0.4, grime=0.5, wear=0.9, panels=None,
                     space="world", scale=0.5, under="#b1b6ba")
M_YEL = C.material("painted", "yel", color="#c99a1e", rough=0.45, grime=0.6, wear=0.8, panels=None, space="world", scale=0.4)
M_HAZ_K = C.material("flat", "haz_k", color="#111111", rough=0.6)
M_PIPE = C.material("metal", "pipe", color="#8a9097", rough=0.3, grime=0.5, space="world", brushed=0.5, axis="Y")
M_CU = C.material("metal", "pipe_cu", color="#b8703f", rough=0.35, grime=0.6, space="world")
M_RUB = C.material("rubber", "cable_k", color="#151517", rough=0.6, space="world")
M_RUB_R = C.material("rubber", "cable_r", color="#6e1712", rough=0.55, space="world")
M_RUB_Y = C.material("rubber", "cable_y", color="#a07816", rough=0.55, space="world")
M_LEATHER = C.material("leather", "seat_leather", color="#3b2a20", rough=0.5, space="world")
M_STRAP = C.material("fabric", "strap", color="#9c3a1c", rough=0.8, weave=600.0, space="world")
M_BUCKLE = C.material("metal", "buckle", color="#c7ccd1", rough=0.2, grime=0.2, space="world")
M_RED_LAMP = C.material("emissive", "red_lamp", color="#ff2516", strength=40.0)
M_RED_LENS = C.material("emissive", "red_lens", color="#ff2516", strength=6.0, base="#300303")
M_COOL_LAMP = C.material("emissive", "cool_lamp", color="#d6f2ff", strength=12.0)
M_SCREEN_SIDE = C.material("screen", "side_screen", color="#2dfdd8", strength=2.5, lines=260.0)
M_SCREEN_AMB = C.material("screen", "side_screen_amb", color="#ffa22e", strength=2.0, lines=260.0)
M_STENCIL = C.material("flat", "stencil", color="#d8d2bd", rough=0.7)


def bar(name, p0, p1, w, d, mat, role="set", bevel=0.01):
    """Box of cross-section w (horizontal) x d (vertical) running from p0 to p1."""
    p0 = Vector(p0); p1 = Vector(p1); v = p1 - p0
    o = C.box(name, (w, v.length, d), mat=mat, bevel=bevel, role=role)
    o.location = (p0 + p1) / 2
    o.rotation_euler = v.to_track_quat("Y", "Z").to_euler()
    return o


def ribbon(name, pts, width, mat, thick=0.003, offset=(0, 0, 0)):
    """Flat strap through [(point, surface_normal_hint), ...]: width spans cross(tangent, normal)."""
    P = [Vector(p) + Vector(offset) for p, _ in pts]; Nh = [Vector(n).normalized() for _, n in pts]
    bm = bmesh.new(); prev = None
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        s = t.cross(Nh[i]).normalized() * (width / 2)
        pair = (bm.verts.new(p - s + Nh[i] * thick), bm.verts.new(p + s + Nh[i] * thick))
        if prev:
            bm.faces.new((prev[0], prev[1], pair[1], pair[0]))
        prev = pair
    o = C._obj_from_bm(name, bm, mat)
    md = o.modifiers.new("solid", "SOLIDIFY"); md.thickness = thick; md.offset = 0
    return o


def diamond_plate(name, color="#5d656b", rough=0.32, scale=1.0):
    """Worn diamond tread plate (world space): raised lozenges, scuffed tops, dirt in the low areas."""
    m, nt, out = C.new_mat(name)
    P = C.coords(nt, "world", 1.0 / scale)
    sp = C.N(nt, "SeparateXYZ", {"Vector": P})
    x, y = sp.outputs[0], sp.outputs[1]
    k = 22.0
    u = _m(nt, "MULTIPLY", _m(nt, "ADD", x, y), k); v = _m(nt, "MULTIPLY", _m(nt, "SUBTRACT", x, y), k)
    fu = _m(nt, "ABSOLUTE", _m(nt, "SUBTRACT", _m(nt, "FRACT", u), 0.5))
    fv = _m(nt, "ABSOLUTE", _m(nt, "SUBTRACT", _m(nt, "FRACT", v), 0.5))
    par = _m(nt, "MODULO", _m(nt, "ADD", _m(nt, "FLOOR", u), _m(nt, "FLOOR", v)), 2.0)   # alternate orientation
    da = _m(nt, "ADD", _m(nt, "MULTIPLY", fu, 0.3), fv); db = _m(nt, "ADD", fu, _m(nt, "MULTIPLY", fv, 0.3))
    d = C.mixf(nt, par, da, db)
    loz = C.maprange(nt, d, 0.2, 0.14)
    n_big = C.noise(nt, P, 0.8, 6, 0.6); n_f = C.noise(nt, P, 18.0, 5, 0.6)
    dirt = _m(nt, "MULTIPLY", C.maprange(nt, n_big, 0.4, 0.7), _m(nt, "SUBTRACT", 1.0, loz), clamp=True)
    shade = C.mix(nt, dirt, C.col(color), "#15130f")
    shade = C.mix(nt, _m(nt, "MULTIPLY", loz, 0.35), shade, "#a9b0b5")
    r = C.maprange(nt, n_f, 0.3, 0.7, rough - 0.08, rough + 0.12)
    r = C.mixf(nt, loz, r, 0.2); r = C.mixf(nt, dirt, r, 0.75)
    C.principled(nt, out, color=shade, metal=1.0, rough=r, normal=C.bump(nt, loz, 0.6, 0.002))
    return m


def quad(name, pts, mat, role="set"):
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in pts]
    bm.faces.new(vs)
    return C._obj_from_bm(name, bm, mat, role=role)


# ---------------------------------------------------------------- shell: floor, walls, ceiling
C.box("deck", (2 * W + 0.4, (WIN_Y0 + 0.6) - BACK, 0.1), (0, (WIN_Y0 + 0.6 + BACK) / 2, -0.1), mat=M_DECK,
      origin="bottom", bevel=0)
# diamond tread plate under the console and the pilot's footwell, edged by a steel trim
C.box("tread", (1.7, 2.9, 0.012), (0, -0.55, 0), mat=diamond_plate("tread"), origin="bottom", bevel=0.004)
for sx in (-1, 1):
    C.box(f"tread_trim_{sx}", (0.04, 2.9, 0.016), (sx * 0.87, -0.55, 0), mat=M_RIB, origin="bottom", bevel=0.004)
for sx in (-1, 1):
    C.box(f"wall_{sx}", (0.1, 0.9 - BACK + 0.2, H + 0.2), (sx * (W + 0.05), (0.9 + BACK) / 2, -0.1), mat=M_WALL,
          origin="bottom", bevel=0)
C.box("wall_back", (2 * W + 0.2, 0.1, H + 0.2), (0, BACK - 0.05, -0.1), mat=M_WALL, origin="bottom", bevel=0)
C.box("ceiling", (2 * W + 0.2, WIN_Y1 - BACK + 0.4, 0.12), (0, (WIN_Y1 + BACK) / 2 + 0.1, H), mat=M_CEIL,
      origin="bottom", bevel=0)
# visor between ceiling and window top
quad("visor", [(-W, WIN_Y1 - 0.8, H), (W, WIN_Y1 - 0.8, H), (WX, WIN_Y1, WIN_Z1), (-WX, WIN_Y1, WIN_Z1)], M_CEIL)
for sx in (-1, 1):
    quad(f"visor_s{sx}", [(sx * W, WIN_Y1 - 0.8, H), (sx * WX, WIN_Y1, WIN_Z1), (sx * W, 0.6, WIN_Z1)], M_CEIL)

# ribs: side frames + ceiling beams
ys = [BACK + 0.35 + i * 0.62 for i in range(6)]
for i, y in enumerate(ys):
    for sx in (-1, 1):
        C.box(f"rib_{i}_{sx}", (0.14, 0.16, H), (sx * (W - 0.07), y, 0), mat=M_RIB, origin="bottom", bevel=0.015)
        C.box(f"rib_fl_{i}_{sx}", (0.03, 0.26, H), (sx * (W - 0.15), y, 0), mat=M_RIB, origin="bottom", bevel=0.008)
        bar(f"knee_{i}_{sx}", (sx * (W - 0.1), y, H - 0.55), (sx * (W - 0.55), y, H - 0.06), 0.14, 0.12, M_RIB)
    C.box(f"beam_{i}", (2 * W, 0.16, 0.14), (0, y, H - 0.14), mat=M_RIB, bevel=0.015)
    for k in range(-6, 7, 2):   # lightening holes look: bolt heads along the beam
        C.cylinder(f"bolt_{i}_{k}", 0.012, 0.02, (k * 0.28, y - 0.085, H - 0.08), (90, 0, 0), M_PIPE, segments=8)

# window frame: centre pane + two angled corner panes
BL, BR, TR, TL = (-WX, WIN_Y0, WIN_Z0), (WX, WIN_Y0, WIN_Z0), (WX, WIN_Y1, WIN_Z1), (-WX, WIN_Y1, WIN_Z1)
BL2, TL2, BR2, TR2 = (-W, 0.9, WIN_Z0), (-W, 0.6, WIN_Z1), (W, 0.9, WIN_Z0), (W, 0.6, WIN_Z1)
for nm, a, b, w, d in (("post_l", BL, TL, 0.16, 0.12), ("post_r", BR, TR, 0.16, 0.12), ("post_l2", BL2, TL2, 0.2, 0.14),
                       ("post_r2", BR2, TR2, 0.2, 0.14), ("top_c", TL, TR, 0.14, 0.16), ("top_l", TL, TL2, 0.14, 0.16),
                       ("top_r", TR, TR2, 0.14, 0.16), ("bot_c", BL, BR, 0.14, 0.1), ("bot_l", BL, BL2, 0.14, 0.1),
                       ("bot_r", BR, BR2, 0.14, 0.1)):
    bar("win_" + nm, a, b, w, d, M_FRAME, bevel=0.02)
# thin centre mullions (split the centre pane in three)
for sx in (-1, 1):
    x = sx * 0.34
    bar(f"win_mull_{sx}", (x, WIN_Y0, WIN_Z0), (x, WIN_Y1, WIN_Z1), 0.05, 0.05, M_FRAME, bevel=0.01)
# rivets along the posts
for nm, a, b in (("l", BL, TL), ("r", BR, TR)):
    a = Vector(a); b = Vector(b)
    for k in range(1, 9):
        p = a.lerp(b, k / 9) + Vector((0, -0.07, 0))
        C.cylinder(f"rivet_{nm}_{k}", 0.008, 0.012, tuple(p), (90, 0, 0), M_PIPE, segments=8)

# dashboard sill under the windshield (centre + corners) with sloped instrument top
C.box("sill_c", (2 * WX, 0.5, WIN_Z0), (0, WIN_Y0 - 0.05, 0), mat=M_SILL, origin="bottom", bevel=0.02)
for sx in (-1, 1):
    a = Vector((sx * WX, WIN_Y0 - 0.05, WIN_Z0 / 2)); b = Vector((sx * W, 0.85, WIN_Z0 / 2))
    bar(f"sill_{sx}", a, b, 0.5, WIN_Z0, M_SILL, bevel=0.02)
dash = quad("dash_top", [(-WX + 0.05, WIN_Y0 - 0.32, WIN_Z0 - 0.02), (WX - 0.05, WIN_Y0 - 0.32, WIN_Z0 - 0.02),
                         (WX - 0.05, WIN_Y0 - 0.1, WIN_Z0 + 0.08), (-WX + 0.05, WIN_Y0 - 0.1, WIN_Z0 + 0.08)], M_SILL)
C.box("dash_shelf", (2 * WX - 0.05, 0.3, 0.06), (0, WIN_Y0 - 0.25, WIN_Z0 - 0.06), (-24, 0, 0), mat=M_SILL, bevel=0.01)
# dashboard gauges (round, emissive faces) and two little screens
for k, x in enumerate((-0.75, -0.55, 0.55, 0.75)):
    p = (x, WIN_Y0 - 0.37, WIN_Z0 - 0.17)
    C.cylinder(f"gauge_rim_{k}", 0.075, 0.04, p, (90, 0, 0), M_BUCKLE, segments=28)
    C.cylinder(f"gauge_face_{k}", 0.064, 0.042, p, (90, 0, 0), M_SCREEN_AMB if k % 2 else M_SCREEN_SIDE,
               segments=28, role="keep")
for k, x in enumerate((-0.3, 0.3)):
    C.box(f"dash_scr_bez_{k}", (0.34, 0.03, 0.22), (x, WIN_Y0 - 0.36, WIN_Z0 - 0.2), mat=M_FRAME, bevel=0.01)
    C.box(f"dash_scr_{k}", (0.3, 0.032, 0.18), (x, WIN_Y0 - 0.362, WIN_Z0 - 0.2), mat=M_SCREEN_SIDE, bevel=0,
          role="keep")

# side consoles along both walls (sloped keypads + small screens)
for sx in (-1, 1):
    x = sx * (W - 0.38)
    C.box(f"sidecon_{sx}", (0.55, 1.5, 0.8), (x, 0.05, 0), mat=M_SILL, origin="bottom", bevel=0.02)
    C.box(f"sidecon_top_{sx}", (0.5, 1.45, 0.05), (x - sx * 0.02, 0.05, 0.84), (0, -sx * 18, 0), mat=M_SILL, bevel=0.01)
    C.box(f"sidecon_keys_{sx}", (0.42, 1.3, 0.012), (x - sx * 0.02, 0.05, 0.87), (0, -sx * 18, 0),
          mat=keypad_material(f"side_keys_{sx}", (-0.21, 0.21, -0.65, 0.65, Vector((0, 1, 0))), "#2b3236",
                              cols=7, rows=16, strength=3.0, lit_frac=0.3), bevel=0)
    C.box(f"sidecon_mon_{sx}", (0.06, 0.6, 0.42), (sx * (W - 0.12), -0.35, 1.25), (0, 0, 0), mat=M_FRAME, bevel=0.02)
    C.box(f"sidecon_mon_scr_{sx}", (0.02, 0.54, 0.36), (sx * (W - 0.16), -0.35, 1.25), mat=M_SCREEN_SIDE if sx < 0 else
          M_SCREEN_AMB, bevel=0, role="keep")
    # lower vent grille on the side console
    for k in range(6):
        C.box(f"sidecon_vent_{sx}_{k}", (0.02, 0.9, 0.025), (x - sx * 0.28, 0.05, 0.15 + k * 0.06), mat=M_HAZ_K, bevel=0)

# wall pipes + brackets
for sx in (-1, 1):
    for j, (z, r, m) in enumerate(((0.32, 0.045, M_CU), (0.42, 0.03, M_PIPE), (2.02, 0.05, M_PIPE), (2.12, 0.03, M_CU))):
        C.pipe(f"wpipe_{sx}_{j}", (sx * (W - 0.24), BACK + 0.1, z), (sx * (W - 0.24), -0.7, z), r, m)
    for i, y in enumerate(ys):
        C.box(f"wclamp_{sx}_{i}", (0.2, 0.04, 0.2), (sx * (W - 0.2), y + 0.12, 0.37), mat=M_RIB, bevel=0.005)
        C.box(f"wclamp2_{sx}_{i}", (0.2, 0.04, 0.2), (sx * (W - 0.2), y + 0.12, 2.07), mat=M_RIB, bevel=0.005)

# hanging cable loops between the ceiling beams (sagging bundles)
rng = random.Random(11)
for i in range(len(ys) - 1):
    for sx in (-1, 1):
        for k, mt in enumerate((M_RUB, M_RUB_R, M_RUB, M_RUB_Y)):
            x = sx * (W - 0.45 - k * 0.06)
            y0 = ys[i] + 0.08; y1 = ys[i + 1] - 0.08
            sag = rng.uniform(0.12, 0.32)
            C.cable(f"loop_{i}_{sx}_{k}", [(x, y0, H - 0.2), (x + sx * rng.uniform(-0.03, 0.03), (y0 + y1) / 2,
                                                             H - 0.2 - sag), (x, y1, H - 0.2)],
                    rng.uniform(0.012, 0.02), mt)
# overhead switch panel (sloped, above and ahead of the pilot)
oh = C.box("overhead", (1.3, 0.75, 0.16), (0, -0.25, H - 0.15), (-12, 0, 0), mat=M_SILL, bevel=0.02)
C.box("overhead_keys", (1.2, 0.68, 0.01), (0, -0.25, H - 0.235), (-12, 0, 0),
      mat=keypad_material("oh_keys", (-0.6, 0.6, -0.34, 0.34, Vector((0, 1, 0))), "#252b30", cols=20, rows=7,
                          strength=4.0), bevel=0)
for k in range(10):   # toggle switches hanging below the panel
    x = -0.54 + k * 0.12
    C.cylinder(f"toggle_{k}", 0.008, 0.06, (x, 0.08, H - 0.29), (12, 0, 0), M_BUCKLE, segments=8)

# red alert beacons (ceiling corners) + caged cool work lights
for k, (x, y) in enumerate(((-1.45, -0.95), (1.45, 0.35), (0.0, BACK + 0.25))):
    z = H - 0.12 if k < 2 else 2.0
    C.cylinder(f"beacon_base_{k}", 0.09, 0.05, (x, y, z), mat=M_FRAME)
    C.cylinder(f"beacon_lens_{k}", 0.07, 0.12, (x, y, z - 0.09), mat=M_RED_LENS, role="keep")
    C.cylinder(f"beacon_core_{k}", 0.03, 0.08, (x, y, z - 0.09), mat=M_RED_LAMP, role="keep")
    for a in range(4):
        aa = math.radians(a * 90 + 45)
        C.pipe(f"beacon_cage_{k}_{a}", (x + math.cos(aa) * 0.085, y + math.sin(aa) * 0.085, z - 0.02),
               (x + math.cos(aa) * 0.085, y + math.sin(aa) * 0.085, z - 0.16), 0.005, M_FRAME, segments=6)
    bl = C.point(f"beacon_l_{k}", (x, y, z - 0.2), 35.0 if k < 2 else 30.0, "#ff2a1a", 0.05)
    bl.visible_glossy = False   # no hot specular dot on the glossy screens
for k, y in enumerate((-2.2, -1.0)):
    C.box(f"ceil_light_{k}", (0.9, 0.12, 0.04), (0, y, H - 0.02), mat=M_COOL_LAMP, bevel=0.005, role="keep")

# back wall: hatch with yellow frame + hazard strip, stencil sign
C.box("hatch_frame", (1.0, 0.06, 1.95), (0.0, BACK + 0.03, 0.05), mat=M_YEL, origin="bottom", bevel=0.04)
C.box("hatch_door", (0.82, 0.08, 1.8), (0.0, BACK + 0.05, 0.12), mat=M_RIB, origin="bottom", bevel=0.05)
wh = C.cable("hatch_wheel", [(0.15 * math.cos(a * math.pi / 4), BACK + 0.14, 1.05 + 0.15 * math.sin(a * math.pi / 4))
                             for a in range(8)], 0.014, M_PIPE)
wh.data.splines[0].use_cyclic_u = True
for a in range(3):
    aa = a * math.pi / 3
    C.pipe(f"hatch_spoke_{a}", (-0.15 * math.cos(aa), BACK + 0.14, 1.05 - 0.15 * math.sin(aa)),
           (0.15 * math.cos(aa), BACK + 0.14, 1.05 + 0.15 * math.sin(aa)), 0.01, M_PIPE, segments=8)
C.cylinder("hatch_hub", 0.035, 0.06, (0.0, BACK + 0.13, 1.05), (90, 0, 0), M_PIPE, segments=16)
C.text("sign_bridge", "BRIDGE  ·  艦橋", 0.12, (1.2, BACK + 0.01, 1.7), (90, 0, 180), M_STENCIL, C.FONT_TC)
C.text("sign_alert", "警報", 0.16, (-1.2, BACK + 0.01, 1.7), (90, 0, 180), M_RED_LENS, C.FONT_TC, role="keep")

# hazard stripes on the deck in front of the sill
def hazard(name, x0, x1, y0, y1, w=0.12):
    bm = bmesh.new(); n = int((x1 - x0) / w)
    for i in range(n):
        a = x0 + i * (x1 - x0) / n; b = a + (x1 - x0) / n * 0.5; dy = y1 - y0
        q = [(a, y0), (b, y0), (b + dy, y1), (a + dy, y1)]
        q = [(min(max(p[0], x0), x1), p[1]) for p in q]
        vs = [bm.verts.new((p[0], p[1], 0.003)) for p in q]
        bm.faces.new(vs)
    C._obj_from_bm(name, bm, C.material("floor_paint", "haz_y", color="#d9a21b", wet=0.0, wear=0.6))
    C.box(name + "_bg", (x1 - x0, y1 - y0, 0.002), ((x0 + x1) / 2, (y0 + y1) / 2, 0.001), mat=M_HAZ_K, bevel=0)


hazard("deck_haz", -WX + 0.05, WX - 0.05, WIN_Y0 - 0.48, WIN_Y0 - 0.32)

# ---------------------------------------------------------------- pilot seat (faces +Y, toward the console)
SEAT = Vector((0.0, -1.05, 0.0))
seat_objs = []


def S(o):
    seat_objs.append(o); return o


S(C.cylinder("seat_plate", 0.28, 0.03, tuple(SEAT), mat=M_RIB, origin="bottom"))
S(C.cylinder("seat_post", 0.06, 0.38, tuple(SEAT), mat=M_PIPE, origin="bottom"))
S(C.box("seat_frame", (0.56, 0.52, 0.06), tuple(SEAT + Vector((0, 0, 0.4))), mat=M_RIB, origin="bottom", bevel=0.01))
S(C.box("seat_pan", (0.52, 0.5, 0.11), tuple(SEAT + Vector((0, 0.01, 0.46))), mat=M_LEATHER, origin="bottom", bevel=0.04))
S(C.box("seat_back", (0.52, 0.12, 0.78), tuple(SEAT + Vector((0, -0.27, 0.95))), (10, 0, 0), M_LEATHER, bevel=0.04))
S(C.box("seat_back_shell", (0.58, 0.06, 0.84), tuple(SEAT + Vector((0, -0.35, 0.94))), (10, 0, 0), M_RIB, bevel=0.02))
S(C.box("seat_head", (0.34, 0.12, 0.2), tuple(SEAT + Vector((0, -0.37, 1.45))), (10, 0, 0), M_LEATHER, bevel=0.04))
for sx in (-1, 1):
    S(C.box(f"seat_arm_{sx}", (0.07, 0.42, 0.06), tuple(SEAT + Vector((sx * 0.31, 0.0, 0.7))), mat=M_LEATHER, bevel=0.02))
    S(C.box(f"seat_arm_post_{sx}", (0.04, 0.04, 0.24), tuple(SEAT + Vector((sx * 0.31, -0.12, 0.46))), mat=M_PIPE,
            origin="bottom", bevel=0.005))
    # harness straps (flat webbing): over the shoulder, down the back cushion, across the pan to the buckle
    S(ribbon(f"strap_{sx}", [((sx * 0.12, -0.44, 1.36), (0, -0.3, 1)), ((sx * 0.12, -0.27, 1.37), (0, 0.6, 1)),
                             ((sx * 0.115, -0.26, 1.25), (0, 1, 0.17)), ((sx * 0.1, -0.2, 0.92), (0, 1, 0.17)),
                             ((sx * 0.085, -0.17, 0.72), (0, 1, 0.17)), ((sx * 0.07, -0.12, 0.585), (0, 0.4, 1)),
                             ((sx * 0.04, 0.1, 0.578), (0, 0, 1)), ((sx * 0.02, 0.19, 0.578), (0, 0, 1))], 0.05, M_STRAP, offset=SEAT))
    S(ribbon(f"lapstrap_{sx}", [((sx * 0.27, -0.14, 0.62), (sx, 0, 0.3)), ((sx * 0.25, -0.05, 0.578), (0, 0, 1)),
                                ((sx * 0.12, 0.12, 0.578), (0, 0, 1)), ((sx * 0.04, 0.2, 0.578), (0, 0, 1))], 0.045, M_STRAP, offset=SEAT))
S(C.box("seat_buckle", (0.08, 0.03, 0.06), tuple(SEAT + Vector((0, 0.21, 0.58))), mat=M_BUCKLE, bevel=0.008))
# headset hung on the headrest
S(C.cable("headset_band", [tuple(SEAT + Vector((-0.2, -0.33, 1.47))), tuple(SEAT + Vector((-0.2, -0.36, 1.58))),
                           tuple(SEAT + Vector((-0.2, -0.43, 1.47)))], 0.008, M_RUB))
for dy in (-0.31, -0.45):
    S(C.cylinder(f"headset_cup_{dy}", 0.045, 0.03, tuple(SEAT + Vector((-0.2, dy, 1.44))), (90, 0, 0), M_LEATHER, 20))
for o in seat_objs:
    o["hide_turn"] = True
C.cable("seat_cable", [tuple(SEAT + Vector((0.0, -0.38, 0.5))), tuple(SEAT + Vector((0.2, -0.6, 0.05))),
                       (0.9, -1.8, 0.02), (W - 0.3, -2.2, 0.02)], 0.018, M_RUB)["hide_turn"] = True


# ---------------------------------------------------------------- outside: storm sky, lightning, rain on the glass
def storm_sky(name, loc, size, flash=(3.0, 7.0), strength=1.0):
    m, nt, out = C.new_mat(name + "_mat")
    P = C.coords(nt, "world")
    sp = C.N(nt, "SeparateXYZ", {"Vector": P})
    v = C.N(nt, "CombineXYZ", {"X": sp.outputs[0], "Y": C.mathn(nt, "MULTIPLY", sp.outputs[2], 1.7), "Z": 0.0}).outputs[0]
    n1 = C.noise(nt, v, 0.09, 10, 0.62, distortion=0.5)
    n2 = C.noise(nt, v, 0.35, 8, 0.6)
    dens = C.maprange(nt, C.mathn(nt, "ADD", C.mathn(nt, "MULTIPLY", n1, 0.8), C.mathn(nt, "MULTIPLY", n2, 0.25)),
                      0.46, 0.7)
    d = C.vmath(nt, "LENGTH", C.vmath(nt, "SUBTRACT", C.N(nt, "CombineXYZ", {"X": sp.outputs[0], "Y": sp.outputs[2]}).outputs[0],
                                      (flash[0], flash[1], 0.0)), out=1)
    glow = C.mathn(nt, "POWER", C.maprange(nt, d, 0.0, 16.0, 1.0, 0.0), 1.6)
    zc = C.maprange(nt, sp.outputs[2], -6.0, 18.0)
    base = C.mix(nt, zc, "#123f3a", "#020909")
    c = C.mix(nt, dens, base, "#010404")
    lit = C.mathn(nt, "MULTIPLY", glow, C.maprange(nt, dens, 0.0, 1.0, 1.0, 0.35))
    c = C.mix(nt, C.mathn(nt, "MULTIPLY", lit, 1.2, clamp=True), c, "#8ff7e2")
    em = C.N(nt, "Emission", {"Color": c, "Strength": C.mathn(nt, "ADD", strength, C.mathn(nt, "MULTIPLY", lit, 4.0))})
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    o = C.plane(name, size, loc, (90, 0, 0), m, role="keep")
    o.visible_shadow = False
    return o


SKY_Y = 16.0
storm_sky("sky", (0, SKY_Y, 5.0), (70, 40), flash=(2.5, 7.0), strength=0.8)


def bolt(name, start, length, seed, segs=14, spread=0.9, radius=0.05, branches=2):
    R = random.Random(seed)
    pts = [Vector(start)]
    for i in range(segs):
        p = pts[-1] + Vector((R.uniform(-spread, spread), 0, -length / segs))
        pts.append(p)
    core = C.material("emissive", "bolt_core", color="#ffe8e4", strength=60.0)
    glow_m, nt, out = C.new_mat("bolt_glow")
    em = C.N(nt, "Emission", {"Color": C.col("#ff3a2a"), "Strength": 5.0})
    tr = C.N(nt, "BsdfTransparent")
    mxs = C.N(nt, "MixShader", {"Fac": 0.5})
    nt.links.new(tr.outputs[0], mxs.inputs[1]); nt.links.new(em.outputs[0], mxs.inputs[2])
    nt.links.new(mxs.outputs[0], out.inputs["Surface"])
    objs = [C.cable(name, [tuple(p) for p in pts], radius, core, resolution=1, role="keep"),
            C.cable(name + "_g", [tuple(p) for p in pts], radius * 5, glow_m, resolution=1, role="keep")]
    for b in range(branches):
        i = R.randint(2, segs - 4)
        q = [pts[i]]
        sgn = R.choice((-1, 1))
        for j in range(5):
            q.append(q[-1] + Vector((sgn * R.uniform(0.3, 1.0), 0, -R.uniform(0.3, 0.8))))
        objs.append(C.cable(f"{name}_b{b}", [tuple(p) for p in q], radius * 0.6, core, resolution=1, role="keep"))
    for o in objs:
        o.visible_shadow = False
    return objs


bolt("bolt", (2.8, SKY_Y - 1.0, 12.0), 13.0, 5, segs=26, spread=0.45, radius=0.022, branches=3)


def rain_on_glass(name, n, seed=4):
    """Short diagonal streaks just outside the windshield (emissive-ish water catching the storm light)."""
    R = random.Random(seed)
    bm = bmesh.new()
    a = Vector(BL); b = Vector(BR); c = Vector(TL)
    for i in range(n):
        side = R.random()
        if side < 0.7:
            base = a + (b - a) * R.random() + (c - a) * R.random()
        else:
            sx = R.choice((-1, 1))
            p0 = Vector((sx * WX, WIN_Y0, WIN_Z0)); p1 = Vector((sx * W, 0.9, WIN_Z0)); p2 = Vector((sx * WX, WIN_Y1, WIN_Z1))
            base = p0 + (p1 - p0) * R.random() + (p2 - p0) * R.random()
        base += Vector((0, 0.06, 0))
        L = R.uniform(0.03, 0.12); w = 0.0018
        vs = [bm.verts.new(base + v) for v in (Vector((-w, 0, 0)), Vector((w, 0, 0)), Vector((w + 0.25 * L, 0, L)),
                                               Vector((-w + 0.25 * L, 0, L)))]
        bm.faces.new(vs)
    m, nt, out = C.new_mat(name + "_mat")
    em = C.N(nt, "Emission", {"Color": C.col("#bff7ee"), "Strength": 2.5})
    tr = C.N(nt, "BsdfTransparent")
    mxs = C.N(nt, "MixShader", {"Fac": 0.45})
    nt.links.new(tr.outputs[0], mxs.inputs[1]); nt.links.new(em.outputs[0], mxs.inputs[2])
    nt.links.new(mxs.outputs[0], out.inputs["Surface"])
    o = C._obj_from_bm(name, bm, m, role="keep")
    o.visible_shadow = False
    return o


rain_on_glass("glass_rain", 900)
# far rain sheets between the glass and the sky
R = random.Random(9)
bm = bmesh.new()
for i in range(1400):
    x = R.uniform(-14, 14); y = R.uniform(3.0, 12.0); z = R.uniform(-4, 9); L = R.uniform(0.4, 1.0); w = 0.006 + 0.004 * (y - 3) / 9
    vs = [bm.verts.new(p) for p in ((x - w, y, z), (x + w, y, z), (x + w + 0.3 * L, y, z + L), (x - w + 0.3 * L, y, z + L))]
    bm.faces.new(vs)
rm, nt, out = C.new_mat("rain_far_mat")
em = C.N(nt, "Emission", {"Color": C.col("#c9fff1"), "Strength": 1.2}); tr = C.N(nt, "BsdfTransparent")
mxs = C.N(nt, "MixShader", {"Fac": 0.35})
nt.links.new(tr.outputs[0], mxs.inputs[1]); nt.links.new(em.outputs[0], mxs.inputs[2]); nt.links.new(mxs.outputs[0], out.inputs["Surface"])
C._obj_from_bm("rain_far", bm, rm, role="keep").visible_shadow = False

# ---------------------------------------------------------------- lighting
C.world("#010203", 1.0)
# lightning flash through the windshield: big cool area outside, aimed into the cockpit
C.area("flash", (1.2, 4.5, 3.6), (0, -0.4, 0.9), 1000, "#b5f4ff", 4.0, 2.5, spread=70)
C.area("sky_fill", (0, 3.0, 1.8), (0, 0, 1.0), 150, "#4fd6c0", 3.5, 1.4, spread=90)
# key: the overhead work light, slightly warm-neutral, from front-left above the pilot
C.area("key", (-0.9, -1.4, 2.25), tuple(DESK_C), 110, C.kelvin(5200), 0.9, 0.35)
# instrument glow: teal light from the screen onto the seat / pilot area
C.area("screen_glow", tuple(SCR_C + Vector((0, -0.12, 0.02))), tuple(SCR_C + Vector((0, -1.5, -0.4))), 12, "#3ff5d6", 0.42, 0.25)
# red alert rakes
C.spot("alert_spot", (1.5, -2.2, 2.3), (-1.3, -1.4, 0.0), 300, "#ff2a1a", 40, 0.6, 0.05).visible_glossy = False
C.area("fill", (1.8, -2.4, 1.3), (0, 0, 0.9), 40, "#8fb6c8", 1.5)
C.haze("haze", (0, (WIN_Y0 + BACK) / 2, H / 2), (2 * W - 0.05, WIN_Y0 - BACK - 0.05, H - 0.05), 0.008, "#cfe3e0", 0.5)

# ---------------------------------------------------------------- shots
SC_ = tuple(SCR_C); DC = tuple(DESK_C)
SHOTS = [
    C.Shot("hero", dict(loc=(-0.62, -1.2, 0.92), target=(0.12, 0.3, 1.22), lens=24, fstop=4.0, focus=DC),
           "暴風雨中的駕駛艙：操控台的螢幕與按鍵發光，擋風玻璃外閃電照亮雲層，紅色警示燈在艙內亮起。", kind="hero"),
    C.Shot("card", dict(loc=(1.25, -1.55, 1.45), target=(0.0, 0.0, 0.78), lens=30),
           "三分之四前側視角：操控台立在駕駛座前方。", kind="card"),
    C.Shot("s1", dict(loc=(-1.3, -1.7, 1.4), target=(0.0, 0.0, 0.74), lens=30),
           "三分之四前視：機身、斜面按鍵台與上方螢幕。"),
    C.Shot("s2", dict(loc=(1.35, 1.05, 1.25), target=(0.0, 0.0, 0.8), lens=26),
           "後側視角：螢幕背板的紅色警示面與側邊的紅色鑲板，背景是駕駛艙後段與艙門。"),
    C.Shot("s3", dict(loc=(SC_[0] - 0.22, SC_[1] - 0.5, SC_[2] + 0.06), target=SC_, lens=45, fstop=2.0, focus=SC_),
           "螢幕特寫：雷達掃描、數據列與紅色警報橫條。"),
    C.Shot("s4", dict(loc=(DC[0] + 0.42, DC[1] - 0.4, DC[2] + 0.12), target=DC, lens=55, fstop=1.8, focus=DC),
           "按鍵台特寫：背光按鍵、琥珀色指示燈與磨損的金屬邊角。"),
]
CAPTIONS = {"clay": "白模：與三分之四前視同一鏡頭，只看造型與比例。",
            "wire": "線框：同一鏡頭顯示模型的實際佈線。"}
TURN = dict(loc=(0.0, -2.5, 1.15), target=(0.0, 0.0, 0.68), lens=30)

# The console has a few razor-thin wedge faces; the Wireframe modifier's even-offset turns their sharp corners into
# long spikes (a white band across the wire shot). Scene-local: switch even offset off on the wire copies.
_wire_pass = C.wire_pass


def _wire_pass_no_spikes(*a, **k):
    st = _wire_pass(*a, **k)
    for c in st[1]:
        md = c.modifiers.get("wire")
        if md:
            md.use_even_offset = False
    return st


C.wire_pass = _wire_pass_no_spikes

C.run(args, "console", model, SHOTS, clay_wire_of="s1", turn=TURN, turn_mode="model", captions_extra=CAPTIONS)
