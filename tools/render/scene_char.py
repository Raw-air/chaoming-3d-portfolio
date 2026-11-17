"""CRASH protagonist (key 'char', 大專 男主 服裝.fbx) in the ship's crew quarters, storm outside the porthole.

  & $blender -b --factory-startup --python tools\\render\\scene_char.py -- --quality draft [--only hero,s1] [--turn] [--out DIR]

The model stands in an A-pose (1.8 m). Set: a narrow crew-quarters bay — lockers and a bench on the left, an open
bulkhead door with warm corridor light on the right, a round porthole with the teal storm behind him, pipes and a
caged bulb overhead. Portrait lighting: warm key from the door side, teal rim from the porthole, soft cool fill.
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402
import common as C  # noqa: E402
import modellib as ML  # noqa: E402

args = C.parse_args()
C.reset()

# ---------------------------------------------------------------- model
# modellib.set_slots() clears the material list, which resets every face's material_index to 0 — the eyes lose
# their iris and the goggles their lenses. Keep the per-face indices across the palette colouring (scene-local).
_color_char = ML.COLOR["char"]


def _color_keep_indices(objs):
    idx = {o.name: [p.material_index for p in o.data.polygons] for o in objs}
    _color_char(objs)
    for o in objs:
        ii = idx[o.name]
        if len(o.data.materials) > 1:
            o.data.polygons.foreach_set("material_index", ii)
            o.data.update()


ML.COLOR["char"] = _color_keep_indices
model = C.load("char", size=1.8)
ML.COLOR["char"] = _color_char
mn, mx = model.bounds
C.log("char bounds", [round(v, 3) for v in mn], [round(v, 3) for v in mx])
for o in model.objs:
    if len(o.data.materials) > 1:
        cnt = [0] * len(o.data.materials)
        for p in o.data.polygons:
            cnt[min(p.material_index, len(cnt) - 1)] += 1
        C.log("slots", o.name, [m.name for m in o.data.materials], cnt)


def seat_eyes():
    """The eyeballs come out of the FBX displaced (asymmetric in x, ~2.5 cm below the lash line, popping out of the
    face). Re-seat each eye under its half of the lash mesh, half sunk into the face surface, iris looking ahead."""
    from mathutils import Matrix
    lash = model.by_name("睫毛"); head = model.by_name("人.002")
    if not lash or not head:
        return
    hv = [v.co for v in head.data.vertices]
    for nm in ("眼睛", "眼睛.001"):
        o = model.by_name(nm)
        vs = [v.co.copy() for v in o.data.vertices]
        c = sum(vs, Vector()) / len(vs)
        r = max((v - c).length for v in vs)
        s = -1 if c.x < 0 else 1
        lv = [v.co for v in lash.data.vertices if v.co.x * s > 0]
        lx = (min(v.x for v in lv) + max(v.x for v in lv)) / 2
        lz = min(v.z for v in lv)
        tz = lz - r * 0.8
        near = [v.y for v in hv if abs(v.x - lx) < 0.008 and abs(v.z - tz) < 0.008]
        sy = min(near) if near else c.y
        tgt = Vector((lx, sy + r * 0.25, tz))
        ir = [p for p in o.data.polygons if p.material_index == 1]
        d = (sum((p.center for p in ir), Vector()) / max(len(ir), 1) - c).normalized()
        want = Vector((-s * 0.04, -1.0, -0.12)).normalized()      # very slight convergence, a touch downward
        q = d.rotation_difference(want)
        M = Matrix.Translation(tgt) @ q.to_matrix().to_4x4() @ Matrix.Translation(-c)
        o.data.transform(M); o.data.update()
        C.log("eye seat", nm, "from", [round(v, 4) for v in c], "to", [round(v, 4) for v in tgt], "surface y", round(sy, 4))


seat_eyes()


def eye_fallback(o):
    """If the iris faces were lost, take the cap of the eyeball that faces forward (-Y)."""
    me = o.data
    if len(me.materials) < 2 or any(p.material_index == 1 for p in me.polygons):
        return
    c = sum((p.center for p in me.polygons), Vector()) / len(me.polygons)
    for p in me.polygons:
        d = (p.center - c).normalized()
        p.material_index = 1 if d.dot(Vector((0.08 * (1 if c.x > 0 else -1), -1, 0.0)).normalized()) > 0.8 else 0
    C.log("eye fallback", o.name)


for nm in ("眼睛", "眼睛.001"):
    o = model.by_name(nm)
    if o:
        eye_fallback(o)


def eye_iris(name):
    """Iris + pupil from the facing angle of the cap (the iris faces form a cap; pupil = its centre)."""
    m, nt, out = C.new_mat(name)
    P = C.coords(nt)
    n = C.noise(nt, P, 900.0, 3, 0.5)
    nrm = C.N(nt, "TexCoord").outputs["Normal"]          # object space: stays put while the turntable spins
    f = C.vmath(nt, "DOT_PRODUCT", nrm, (0.0, -0.9928, -0.1191), out=1)
    pupil = C.maprange(nt, f, 0.975, 0.985)
    ring = C.maprange(nt, f, 0.9, 0.88)
    c = C.mix(nt, C.maprange(nt, n, 0.3, 0.7, 0.0, 0.5), C.col("#5a3a1e"), C.col("#2a1608"))
    c = C.mix(nt, ring, c, C.col("#120903"))
    c = C.mix(nt, pupil, c, C.col("#020202"))
    C.principled(nt, out, color=c, rough=0.15, coat=1.0, coat_rough=0.02, spec=0.6)
    return m


def _m(nt, op, a, b=None, clamp=False):
    return C.mathn(nt, op, a, b, clamp)


def hair_mat(name, color="#1e140d"):
    """Dark curly hair: strand streaks, cavity darkening between the sculpted curls, soft anisotropic sheen."""
    m, nt, out = C.new_mat(name)
    P = C.coords(nt)
    st = C.noise(nt, C.vmath(nt, "MULTIPLY", P, (70.0, 70.0, 6.0)), 1.0, 3, 0.5)
    base = C.col(color)
    shade = C.mix(nt, C.maprange(nt, st, 0.35, 0.7, 0.0, 0.6), base, tuple(min(1, x * 2.0) for x in base[:3]))
    cav = _m(nt, "MULTIPLY", C.cavity_mask(nt, 0.03, 1.2), 1.6, clamp=True)
    shade = C.mix(nt, cav, shade, "#050302")
    C.principled(nt, out, color=shade, rough=C.mixf(nt, cav, 0.45, 0.7), aniso=0.5, spec=0.35, sheen=0.08,
                 normal=C.bump(nt, st, 0.3, 0.001))
    return m


def worn_leather(name, color, scuff=1.0):
    """Matte, scuffed leather: colour mottling, lighter worn edges/toes (Bevel), creases, pebble grain."""
    m, nt, out = C.new_mat(name)
    P = C.coords(nt)
    n_big = C.noise(nt, P, 7.0, 6, 0.6); n_mid = C.noise(nt, P, 30.0, 6, 0.65)
    crease = C.noise(nt, C.vmath(nt, "MULTIPLY", P, (25.0, 25.0, 140.0)), 1.0, 4, 0.6)
    grain = C.N(nt, "TexVoronoi", {"Vector": P, "Scale": 450.0}, feature="F1").outputs["Distance"]
    base = C.col(color)
    shade = C.mix(nt, C.maprange(nt, n_big, 0.35, 0.7, 0.0, 0.45), base, tuple(x * 0.45 for x in base[:3]))
    e = C.edge_mask(nt, 0.006)
    wear = _m(nt, "MULTIPLY", _m(nt, "MULTIPLY", e, C.maprange(nt, n_mid, 0.4, 0.65)), 1.6 * scuff, clamp=True)
    shade = C.mix(nt, wear, shade, tuple(min(1.0, x * 2.4) for x in base[:3]))
    cr = C.maprange(nt, crease, 0.55, 0.7)
    shade = C.mix(nt, _m(nt, "MULTIPLY", cr, 0.5), shade, tuple(x * 0.4 for x in base[:3]))
    r = C.maprange(nt, n_mid, 0.3, 0.7, 0.5, 0.72)
    r = C.mixf(nt, wear, r, 0.4)
    h = _m(nt, "ADD", _m(nt, "MULTIPLY", grain, 0.6), _m(nt, "MULTIPLY", cr, -0.8))
    C.principled(nt, out, color=shade, rough=r, coat=0.08, coat_rough=0.35, spec=0.4, normal=C.bump(nt, h, 0.3, 0.001))
    return m


LOOKS = {    "ch_skin": ("skin", dict(color="#c08562", rough=0.42, sss=0.3)),
    "ch_hair": hair_mat("look_ch_hair"),
    "ch_coat": ("fabric", dict(color="#62603a", rough=0.82, weave=260.0, sheen=0.25)),
    "ch_pants": ("fabric", dict(color="#6a3d2b", rough=0.86, weave=300.0, sheen=0.3)),
    "ch_boots": worn_leather("look_ch_boots", "#2e1d13"),
    "ch_belt": worn_leather("look_ch_belt", "#33221a", scuff=0.6),
    "ch_scarf": ("fabric", dict(color="#8f1f18", rough=0.9, weave=420.0, sheen=0.4)),
    "ch_shirt": ("fabric", dict(color="#2a2c30", rough=0.88, weave=500.0, sheen=0.4)),
    "ch_eye_white": ("plastic", dict(color="#e2dbd2", rough=0.12, coat=1.0)),
    "ch_eye_iris": eye_iris("look_ch_eye_iris"),
    "ch_teeth": ("plastic", dict(color="#e0d6c4", rough=0.3)),
    "ch_lens": ("tinted_glass", dict(color="#1d3a44", rough=0.03, glow="#ffab2e", glow_strength=0.0)),
    "brass": ("metal", dict(color="#c4964a", rough=0.28, grime=0.55)),
    "metal_light": ("metal", dict(color="#c3c8cc", rough=0.22, grime=0.3)),
    "metal_dark": ("metal", dict(color="#34383d", rough=0.35, grime=0.4)),
    "black_matte": ("flat", dict(color="#0c0a09", rough=0.7)),
}
C.apply_looks(model.objs, LOOKS)

HEAD = Vector((0.0, -0.06, 1.63))      # between the eyes
EYES = Vector((0.0, -0.095, 1.615))

# ---------------------------------------------------------------- set materials
W, BACK, FRONT, H = 1.8, 2.4, -4.6, 2.6
M_DECK = C.material("painted", "deck", color="#2c3134", rough=0.5, metal=0.4, grime=0.8, wear=0.8, panels=(0.6, 1.2, 1000),
                    seam_width=0.006, space="world", scale=0.5, grime_color="#0e0c0a", under="#9aa1a7")
M_WALL = C.material("painted", "wall", color="#263837", rough=0.55, grime=0.75, wear=0.45, panels=(0.9, 0.9, 0.7),
                    seam_width=0.006, space="world", scale=0.5, streaks=0.9, grime_color="#121010")
M_RIB = C.material("painted", "rib", color="#232a2d", rough=0.45, metal=0.3, grime=0.6, wear=0.8, panels=None,
                   space="world", scale=0.5, under="#a0a6aa")
M_CEIL = C.material("painted", "ceil", color="#1c2224", rough=0.6, grime=0.6, wear=0.3, panels=(0.6, 0.6, 1000),
                    space="world", scale=0.5)
M_LOCKER = C.material("painted", "locker", color="#5d6b4f", rough=0.42, metal=0.3, grime=0.6, wear=0.8, panels=None,
                      space="world", scale=0.4, grime_color="#17130e", under="#a6abaf")
M_LOCKER2 = C.material("painted", "locker2", color="#4f5d5f", rough=0.42, metal=0.3, grime=0.6, wear=0.8, panels=None,
                       space="world", scale=0.4, grime_color="#17130e", under="#a6abaf")
M_DARK = C.material("flat", "slot_dark", color="#070808", rough=0.8)
M_WOOD = C.material("wood", "bench_wood", color="#7b5636", rough=0.55, grain=5.0, coat=0.1, space="world")
M_STEEL = C.material("metal", "steel", color="#8a9097", rough=0.3, grime=0.5, space="world", brushed=0.5)
M_CU = C.material("metal", "copper", color="#b8703f", rough=0.33, grime=0.6, space="world")
M_RUB = C.material("rubber", "rubber", color="#151517", rough=0.6, space="world")
M_YEL = C.material("painted", "yel", color="#c99a1e", rough=0.45, grime=0.6, wear=0.8, panels=None, space="world", scale=0.4)
M_RED = C.material("painted", "red", color="#a3221b", rough=0.35, grime=0.4, wear=0.6, panels=None, space="world", scale=0.3)
M_STENCIL = C.material("flat", "stencil", color="#d8d2bd", rough=0.7)
M_CANVAS = C.material("fabric", "canvas", color="#5f5a44", rough=0.88, weave=180.0, space="world")
M_CANVAS2 = C.material("fabric", "canvas2", color="#2f3d45", rough=0.88, weave=180.0, space="world")
M_LEATHER = C.material("leather", "set_leather", color="#4a2e1c", rough=0.45, space="world")
M_BULB = C.material("emissive", "bulb", color=C.kelvin(2600), strength=40.0)
M_GLOW_DOOR = C.material("emissive", "door_glow", color=C.kelvin(3200), strength=4.0)


def bar(name, p0, p1, w, d, mat, role="set", bevel=0.01):
    p0 = Vector(p0); p1 = Vector(p1); v = p1 - p0
    o = C.box(name, (w, v.length, d), mat=mat, bevel=bevel, role=role)
    o.location = (p0 + p1) / 2
    o.rotation_euler = v.to_track_quat("Y", "Z").to_euler()
    return o


def ring(name, center, radius, tube, mat, axis="Y", n=24):
    """Torus-like ring (cyclic bezier tube) facing along axis."""
    c = Vector(center); pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        if axis == "Y":
            pts.append(c + Vector((radius * math.cos(a), 0, radius * math.sin(a))))
        else:
            pts.append(c + Vector((0, radius * math.cos(a), radius * math.sin(a))))
    o = C.cable(name, [tuple(p) for p in pts], tube, mat)
    o.data.splines[0].use_cyclic_u = True
    return o


def disc_hole_wall(name, x0, x1, z0, z1, y, holes, mat, thick=0.08, segs=32):
    """Wall panel (XZ plane at y) with circular holes [(cx, cz, r)], built as a mesh (no booleans)."""
    bm = bmesh.new()
    cx, cz, r = holes[0]
    a = r + 0.25
    P = lambda x, z: bm.verts.new((x, y, z))  # noqa: E731
    # square-to-circle ring around the hole
    inner = []; outer = []
    for i in range(segs):
        t = 2 * math.pi * i / segs
        ct, st = math.cos(t), math.sin(t)
        k = a / max(abs(ct), abs(st))
        inner.append(P(cx + r * ct, cz + r * st)); outer.append(P(cx + k * ct, cz + k * st))
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new((inner[i], inner[j], outer[j], outer[i]))
    # the rest of the wall as four rectangles
    for (xa, xb, za, zb) in ((x0, cx - a, z0, z1), (cx + a, x1, z0, z1), (cx - a, cx + a, z0, cz - a),
                             (cx - a, cx + a, cz + a, z1)):
        bm.faces.new((P(xa, za), P(xb, za), P(xb, zb), P(xa, zb)))
    o = C._obj_from_bm(name, bm, mat)
    md = o.modifiers.new("solid", "SOLIDIFY"); md.thickness = thick; md.offset = 1.0
    return o


# ---------------------------------------------------------------- shell
C.box("deck", (2 * W + 0.4, BACK - FRONT + 0.4, 0.1), (0, (BACK + FRONT) / 2, -0.1), mat=M_DECK, origin="bottom", bevel=0)
C.box("ceiling", (2 * W + 0.4, BACK - FRONT + 0.4, 0.12), (0, (BACK + FRONT) / 2, H), mat=M_CEIL, origin="bottom", bevel=0)
# side walls; the right one has a door opening (y -1.55 .. -0.65, up to z 2.0)
DOOR_Y0, DOOR_Y1, DOOR_Z = 0.25, 1.15, 2.0
C.box("wall_L", (0.1, BACK - FRONT, H), (-W - 0.05, (BACK + FRONT) / 2, 0), mat=M_WALL, origin="bottom", bevel=0)
C.box("wall_R_back", (0.1, BACK - DOOR_Y1, H), (W + 0.05, (BACK + DOOR_Y1) / 2, 0), mat=M_WALL, origin="bottom", bevel=0)
C.box("wall_R_front", (0.1, DOOR_Y0 - FRONT, H), (W + 0.05, (DOOR_Y0 + FRONT) / 2, 0), mat=M_WALL, origin="bottom", bevel=0)
C.box("wall_R_top", (0.1, DOOR_Y1 - DOOR_Y0, H - DOOR_Z), (W + 0.05, (DOOR_Y0 + DOOR_Y1) / 2, DOOR_Z), mat=M_WALL,
      origin="bottom", bevel=0)
C.box("wall_F", (2 * W, 0.1, H), (0, FRONT - 0.05, 0), mat=M_WALL, origin="bottom", bevel=0)
# back wall with a round porthole (storm outside)
PORT = (0.55, 1.55, 0.36)   # x, z, radius
disc_hole_wall("wall_back", -W, W, 0.0, H, BACK, [PORT], M_WALL, thick=0.12)
ring("port_rim", (PORT[0], BACK - 0.03, PORT[1]), PORT[2] + 0.04, 0.045, M_STEEL)
ring("port_rim2", (PORT[0], BACK - 0.05, PORT[1]), PORT[2] + 0.11, 0.02, M_RIB)
for k in range(12):   # bolts around the porthole
    a = 2 * math.pi * k / 12
    C.cylinder(f"port_bolt_{k}", 0.014, 0.03, (PORT[0] + (PORT[2] + 0.11) * math.cos(a), BACK - 0.06,
                                              PORT[1] + (PORT[2] + 0.11) * math.sin(a)), (90, 0, 0), M_STEEL, segments=8)
# porthole glass: thin, slightly rough tinted pane (cheap: no thickness), sky beyond
pg, nt, out = C.new_mat("port_glass")
C.principled(nt, out, color=C.col("#a8e8e0"), rough=0.08, transmission=1.0, ior=1.2)
C.cylinder("port_glass", PORT[2] + 0.02, 0.004, (PORT[0], BACK + 0.04, PORT[1]), (90, 0, 0), pg, segments=40, role="keep")

# vertical ribs on the walls + ceiling beams
ys = [BACK - 0.35 - i * 0.7 for i in range(9)]
for i, y in enumerate(ys):
    for sx in (-1, 1):
        if sx == 1 and DOOR_Y0 - 0.1 < y < DOOR_Y1 + 0.1:
            continue
        C.box(f"rib_{i}_{sx}", (0.12, 0.14, H), (sx * (W - 0.06), y, 0), mat=M_RIB, origin="bottom", bevel=0.015)
    C.box(f"beam_{i}", (2 * W, 0.14, 0.12), (0, y, H - 0.12), mat=M_RIB, bevel=0.015)
for sx in (-1, 1):   # rib on the back wall corners
    C.box(f"back_post_{sx}", (0.14, 0.14, H), (sx * (W - 0.07), BACK - 0.07, 0), mat=M_RIB, origin="bottom", bevel=0.015)

# overhead pipe run along Y (copper + steel), cable tray, caged bulb
for j, (x, z, r, m) in enumerate(((-0.9, H - 0.25, 0.055, M_CU), (-0.75, H - 0.22, 0.035, M_STEEL),
                                  (0.95, H - 0.24, 0.06, M_STEEL), (1.1, H - 0.3, 0.03, M_CU))):
    C.pipe(f"ceil_pipe_{j}", (x, FRONT + 0.2, z), (x, BACK - 0.1, z), r, m)
C.box("tray", (0.35, BACK - FRONT - 0.4, 0.03), (0.0, (BACK + FRONT) / 2, H - 0.3), mat=M_RIB, bevel=0.005)
rng = random.Random(3)
for k in range(5):
    x = -0.12 + k * 0.06
    pts = [(x, FRONT + 0.3, H - 0.27)]
    for i in range(len(ys) - 1):
        pts.append((x + rng.uniform(-0.02, 0.02), (ys[i] + ys[i + 1]) / 2, H - 0.27))
    C.cable(f"tray_cable_{k}", pts, 0.014, M_RUB if k % 3 else C.material("rubber", "cable_r", color="#6e1712",
                                                                            space="world"))
# loose cable loop hanging from the tray near the back wall


BULB = Vector((-0.35, -0.75, H - 0.42))
C.cylinder("bulb_base", 0.06, 0.06, tuple(BULB + Vector((0, 0, 0.1))), mat=M_RIB)
C.cylinder("bulb", 0.035, 0.08, tuple(BULB), mat=M_BULB, role="keep")
for a in range(6):
    aa = math.radians(a * 60)
    C.pipe(f"bulb_cage_{a}", tuple(BULB + Vector((math.cos(aa) * 0.065, math.sin(aa) * 0.065, 0.08))),
           tuple(BULB + Vector((math.cos(aa) * 0.065, math.sin(aa) * 0.065, -0.08))), 0.004, M_STEEL, segments=6)
ring("bulb_cage_ring", tuple(BULB + Vector((0, 0, -0.08))), 0.065, 0.005, M_STEEL, axis="Z")
C.pipe("bulb_rod", tuple(BULB + Vector((0, 0, 0.13))), (BULB.x, BULB.y, H - 0.3), 0.012, M_STEEL)

# ---------------------------------------------------------------- left wall: lockers, bench, hanging gear
LX = -W + 0.12
lockers = []
for k in range(5):
    y = 0.95 - k * 0.52
    m = M_LOCKER if k % 2 == 0 else M_LOCKER2
    lk = C.box(f"locker_{k}", (0.5, 0.5, 1.95), (LX + 0.25, y, 0.1), mat=m, origin="bottom", bevel=0.012)
    C.box(f"locker_plinth_{k}", (0.46, 0.46, 0.1), (LX + 0.25, y, 0.0), mat=M_DARK, origin="bottom", bevel=0)
    fx = LX + 0.505
    if False:   # (an ajar door read as a flat slab; all closed)
        door = C.box(f"locker_door_{k}", (0.025, 0.46, 1.8), (fx + 0.15, y - 0.17, 0.17), (0, 0, -35), mat=m,
                     origin="bottom", bevel=0.008)
        C.box(f"locker_inside_{k}", (0.01, 0.44, 1.78), (fx - 0.005, y, 0.18), mat=M_DARK, origin="bottom", bevel=0)
        # a jacket sleeve / canvas bag peeking out
        C.cylinder(f"locker_bag_{k}", 0.13, 0.4, (fx - 0.12, y + 0.05, 1.05), (0, 0, 0), M_CANVAS2, segments=20)
        continue
    for v in range(5):   # vent slits
        C.box(f"locker_vent_{k}_{v}", (0.006, 0.3, 0.018), (fx, y, 1.62 + v * 0.045), mat=M_DARK, bevel=0)
        C.box(f"locker_vent_lo_{k}_{v}", (0.006, 0.3, 0.018), (fx, y, 0.3 + v * 0.045), mat=M_DARK, bevel=0)
    C.box(f"locker_handle_{k}", (0.03, 0.03, 0.16), (fx + 0.012, y - 0.17, 1.05), mat=M_STEEL, bevel=0.006)
    C.box(f"locker_plate_{k}", (0.004, 0.14, 0.07), (fx + 0.002, y, 1.4), mat=M_STENCIL, bevel=0)
    C.text(f"locker_no_{k}", f"0{k + 3}", 0.05, (fx + 0.006, y, 1.4), (90, 0, 90), M_DARK, C.FONT_STENCIL)
# helmet + coiled rope on top of the lockers
C.cylinder("helmet_shell", 0.14, 0.12, (LX + 0.25, 0.95, 2.11), mat=M_LEATHER, segments=24, origin="bottom")
ring("rope_coil_a", (LX + 0.25, -0.1, 2.1), 0.13, 0.018, M_CANVAS, axis="Z")
ring("rope_coil_b", (LX + 0.25, -0.1, 2.135), 0.12, 0.018, M_CANVAS, axis="Z")
# hooks on the wall between lockers and front, with hanging gear
HX = -W + 0.02
for k, y in enumerate((-1.75, -2.05, -2.35)):
    C.box(f"hook_plate_{k}", (0.02, 0.06, 0.1), (HX, y, 1.7), mat=M_STEEL, bevel=0.004)
    C.pipe(f"hook_{k}", (HX, y, 1.68), (HX + 0.1, y, 1.72), 0.008, M_STEEL, segments=8)
# satchel hanging from hook 0 (strap + bag)
C.cable("satchel_strap", [(HX + 0.09, -1.75, 1.71), (HX + 0.08, -1.62, 1.35), (HX + 0.1, -1.68, 1.1)], 0.012, M_LEATHER)
C.cable("satchel_strap2", [(HX + 0.09, -1.75, 1.71), (HX + 0.08, -1.88, 1.35), (HX + 0.1, -1.82, 1.1)], 0.012, M_LEATHER)
C.box("satchel", (0.12, 0.34, 0.26), (HX + 0.1, -1.75, 0.95), (0, 4, 0), mat=M_LEATHER, bevel=0.04)
C.box("satchel_flap", (0.03, 0.34, 0.16), (HX + 0.165, -1.75, 1.02), (0, 4, 0), mat=M_LEATHER, bevel=0.02)
C.box("satchel_buckle", (0.01, 0.04, 0.04), (HX + 0.183, -1.75, 0.98), mat=C.material("metal", "set_brass",
                                                                                     color="#c4964a", rough=0.3, space="world"), bevel=0.003)
# spare coat hanging on hook 2
coat = C.cylinder("spare_coat", 0.16, 0.85, (HX + 0.15, -2.35, 1.25), (0, 0, 0), M_CANVAS2, segments=20)
coat.scale = (0.6, 1.0, 1.0)
C.cylinder("spare_coat_collar", 0.1, 0.08, (HX + 0.14, -2.35, 1.69), mat=M_CANVAS2, segments=16)
# bench in front of the lockers
BX = -W + 0.85
C.box("bench_top", (0.38, 2.0, 0.05), (BX, -0.1, 0.43), mat=M_WOOD, origin="bottom", bevel=0.01)
for y in (-0.95, 0.75):
    for dx in (-0.14, 0.14):
        C.box(f"bench_leg_{y}_{dx}", (0.04, 0.04, 0.43), (BX + dx, y, 0), mat=M_RIB, origin="bottom", bevel=0.005)
    C.box(f"bench_brace_{y}", (0.32, 0.03, 0.03), (BX, y, 0.12), mat=M_RIB, bevel=0.004)
# on the bench: duffel bag, thermos, gloves
duf = C.cylinder("duffel", 0.15, 0.62, (BX + 0.02, 0.35, 0.62), (90, 0, 8), M_CANVAS, segments=24)
duf.scale = (1.0, 0.85, 1.0)
for dy in (-0.15, 0.15):
    ring(f"duffel_band_{dy}", (BX + 0.02, 0.35 + dy, 0.62), 0.152, 0.008, M_LEATHER, axis="X")
C.cable("duffel_handle", [(BX - 0.03, 0.25, 0.76), (BX + 0.02, 0.35, 0.82), (BX + 0.06, 0.45, 0.76)], 0.01, M_LEATHER)
C.cylinder("thermos", 0.04, 0.24, (BX - 0.05, -0.55, 0.48), mat=M_RED, origin="bottom", segments=20)
C.cylinder("thermos_cap", 0.042, 0.05, (BX - 0.05, -0.55, 0.72), mat=M_STEEL, origin="bottom", segments=20)
C.box("gloves", (0.11, 0.2, 0.03), (BX + 0.06, -0.8, 0.48), (0, 0, 20), mat=M_LEATHER, origin="bottom", bevel=0.015)

# ---------------------------------------------------------------- right wall: open bulkhead door with warm light
RX = W
C.box("door_frame_L", (0.16, 0.12, DOOR_Z), (RX - 0.02, DOOR_Y0 - 0.06, 0), mat=M_YEL, origin="bottom", bevel=0.03)
C.box("door_frame_R", (0.16, 0.12, DOOR_Z), (RX - 0.02, DOOR_Y1 + 0.06, 0), mat=M_YEL, origin="bottom", bevel=0.03)
C.box("door_frame_T", (0.16, DOOR_Y1 - DOOR_Y0 + 0.24, 0.14), (RX - 0.02, (DOOR_Y0 + DOOR_Y1) / 2, DOOR_Z), mat=M_YEL,
      origin="bottom", bevel=0.03)
C.box("door_sill", (0.2, DOOR_Y1 - DOOR_Y0, 0.08), (RX, (DOOR_Y0 + DOOR_Y1) / 2, 0), mat=M_YEL, origin="bottom", bevel=0.02)
# door leaf swung open into the corridor beyond
C.box("door_leaf", (0.06, 0.86, 1.9), (RX + 0.48, DOOR_Y1 + 0.35, 0.05), (0, 0, 62), mat=M_RIB, origin="bottom", bevel=0.03)
# corridor beyond the door: floor, far wall (warm-lit)
C.box("cor_floor", (2.0, 3.0, 0.1), (RX + 1.0, (DOOR_Y0 + DOOR_Y1) / 2, -0.1), mat=M_DECK, origin="bottom", bevel=0)
C.box("cor_wall", (0.1, 3.0, H), (RX + 1.3, (DOOR_Y0 + DOOR_Y1) / 2, 0), mat=M_WALL, origin="bottom", bevel=0)
C.box("cor_ceil", (2.0, 3.0, 0.1), (RX + 1.0, (DOOR_Y0 + DOOR_Y1) / 2, H), mat=M_CEIL, origin="bottom", bevel=0)
C.box("cor_wall_f", (2.0, 0.1, H), (RX + 1.0, DOOR_Y0 - 1.0, 0), mat=M_WALL, origin="bottom", bevel=0)
C.box("cor_wall_b", (2.0, 0.1, H), (RX + 1.0, DOOR_Y1 + 1.0, 0), mat=M_WALL, origin="bottom", bevel=0)
C.box("cor_lamp", (0.3, 0.6, 0.04), (RX + 0.8, (DOOR_Y0 + DOOR_Y1) / 2, H - 0.04), mat=M_GLOW_DOOR, bevel=0, role="keep")
C.area("cor_light", (RX + 0.8, (DOOR_Y0 + DOOR_Y1) / 2, H - 0.1), (RX + 0.6, (DOOR_Y0 + DOOR_Y1) / 2, 0), 220,
       C.kelvin(3200), 0.5, 0.9)
# door wheel + sign
ring("door_wheel", (RX + 0.48 - 0.05, DOOR_Y1 + 0.35, 1.1), 0.13, 0.012, M_STEEL, axis="X")
C.text("sign_crew", "船員艙  CREW", 0.1, (RX - 0.01, DOOR_Y1 + 0.42, 2.25), (90, 0, -90), M_STENCIL, C.FONT_TC)
# right wall: fire extinguisher, fuse box, vertical pipes
C.cylinder("extinguisher", 0.07, 0.45, (RX - 0.12, -1.0, 0.55), mat=M_RED, origin="bottom", segments=24)
C.cylinder("ext_head", 0.03, 0.08, (RX - 0.12, -1.0, 1.0), mat=M_STEEL, origin="bottom", segments=12)
C.cable("ext_hose", [(RX - 0.1, -1.0, 1.05), (RX - 0.06, -0.92, 0.95), (RX - 0.07, -0.9, 0.7)], 0.01, M_RUB)
C.box("ext_bracket", (0.04, 0.18, 0.04), (RX - 0.05, -1.0, 0.75), mat=M_RIB, bevel=0.005)
C.box("fusebox", (0.12, 0.4, 0.5), (RX - 0.06, -1.6, 1.3), mat=M_LOCKER2, bevel=0.015)
C.box("fusebox_lamp", (0.01, 0.03, 0.03), (RX - 0.125, -1.7, 1.47), mat=C.material("emissive", "fuse_led", color="#ff2516",
                                                                                     strength=20), bevel=0, role="keep")
C.box("fusebox_lamp2", (0.01, 0.03, 0.03), (RX - 0.125, -1.64, 1.47), mat=C.material("emissive", "fuse_led_g",
                                                                                      color="#2dfdd8", strength=12),
      bevel=0, role="keep")
for j, x in enumerate((RX - 0.2, RX - 0.28)):
    C.pipe(f"vpipe_{j}", (x, -0.35, 0), (x, -0.35, H), 0.035 if j else 0.05, M_CU if j else M_STEEL)

# floor: drain grate + scuffed hazard line by the door
C.box("grate", (0.6, 0.6, 0.012), (0.95, 0.75, 0), mat=M_RIB, origin="bottom", bevel=0.004)
for k in range(9):
    C.box(f"grate_slot_{k}", (0.52, 0.025, 0.004), (0.95, 0.51 + k * 0.06, 0.011), mat=M_DARK, origin="bottom", bevel=0)
C.box("door_haz", (0.35, DOOR_Y1 - DOOR_Y0, 0.003), (RX - 0.25, (DOOR_Y0 + DOOR_Y1) / 2, 0), mat=C.material(
    "floor_paint", "haz_y", color="#d9a21b", wet=0.0, wear=0.7), origin="bottom", bevel=0)


# ---------------------------------------------------------------- outside the porthole: storm
def storm_sky(name, loc, size, flash=(3.0, 7.0), strength=1.0):
    m, nt, out = C.new_mat(name + "_mat")
    P = C.coords(nt, "world")
    sp = C.N(nt, "SeparateXYZ", {"Vector": P})
    v = C.N(nt, "CombineXYZ", {"X": sp.outputs[0], "Y": _m(nt, "MULTIPLY", sp.outputs[2], 1.7), "Z": 0.0}).outputs[0]
    n1 = C.noise(nt, v, 0.25, 10, 0.62, distortion=0.5)
    dens = C.maprange(nt, n1, 0.45, 0.68)
    d = C.vmath(nt, "LENGTH", C.vmath(nt, "SUBTRACT", C.N(nt, "CombineXYZ", {"X": sp.outputs[0], "Y": sp.outputs[2]}).outputs[0],
                                      (flash[0], flash[1], 0.0)), out=1)
    glow = _m(nt, "POWER", C.maprange(nt, d, 0.0, 6.0, 1.0, 0.0), 1.5)
    c = C.mix(nt, dens, "#1b5a52", "#020808")
    lit = _m(nt, "MULTIPLY", glow, C.maprange(nt, dens, 0.0, 1.0, 1.0, 0.4))
    c = C.mix(nt, _m(nt, "MULTIPLY", lit, 1.2, clamp=True), c, "#9ff8e6")
    em = C.N(nt, "Emission", {"Color": c, "Strength": _m(nt, "ADD", strength, _m(nt, "MULTIPLY", lit, 3.0))})
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    o = C.plane(name, size, loc, (90, 0, 0), m, role="keep")
    o.visible_shadow = False
    return o


storm_sky("sky", (PORT[0], BACK + 3.0, PORT[1]), (8, 6), flash=(PORT[0] + 0.6, PORT[1] + 0.5), strength=0.7)

# ---------------------------------------------------------------- lighting (portrait: key + rim + fill)
C.world("#010203", 1.0)
KEY = C.area("key", (1.2, -1.85, 1.95), tuple(HEAD + Vector((0, 0, -0.3))), 190, C.kelvin(4800), 1.0, 0.8)
RIM_P = C.area("rim_port", (PORT[0], BACK - 0.25, PORT[1]), tuple(HEAD + Vector((0, 0, -0.2))), 220, "#9af2e6", 0.7)
RIM_T = C.area("rim_top", (-0.8, 1.0, 2.35), (0, 0, 1.2), 140, "#8fe8e0", 1.2, 0.5)
FILL = C.area("fill", (-1.4, -2.6, 1.3), (0, 0, 1.0), 35, "#9fb8c8", 1.6, 1.2)
FACE_FILL = C.area("face_fill", (-0.35, -1.5, 1.45), tuple(HEAD), 18, C.kelvin(5200), 0.6)
BACK_KEY = C.area("back_key", (-1.2, 1.9, 1.9), (0, 0, 1.1), 0.0, C.kelvin(5200), 1.2, 0.8)


def rear_setup():
    """From behind, the rims become front lights: tame them and add a neutral key from the camera side."""
    RIM_P.data.energy = 0.0; RIM_T.data.energy = 15; BACK_KEY.data.energy = 40
    BULB_L.visible_glossy = False   # the tiny bulb right above the head left hot specks on the curls
    RIM_T.visible_glossy = False


def rear_teardown():
    RIM_P.data.energy = 220; RIM_T.data.energy = 140; BACK_KEY.data.energy = 0.0
    BULB_L.visible_glossy = True; RIM_T.visible_glossy = True


def hero_setup():
    """Low-key portrait: no front fill, hot teal rims from the porthole side, warm door key does the modelling."""
    FILL.data.energy = 0.0; FACE_FILL.data.energy = 5.0
    RIM_P.data.energy = 380; RIM_T.data.energy = 200; KEY.data.energy = 45   # narrow spread concentrates power
    DOOR_SPILL.data.energy = 22
    KEY.data.spread = math.radians(35)   # keep the key on him, off the back wall
    _haze_density(0.0015)        # low-key: keep the back wall dark, only the practicals glow


def hero_teardown():
    FILL.data.energy = 35; FACE_FILL.data.energy = 18
    RIM_P.data.energy = 220; RIM_T.data.energy = 140; KEY.data.energy = 190
    DOOR_SPILL.data.energy = 0.0
    KEY.data.spread = math.radians(180)
    _haze_density(0.006)


def _haze_density(d):
    nd = next(n for n in bpy.data.materials["haze_vol"].node_tree.nodes if n.type == "PRINCIPLED_VOLUME")
    nd.inputs["Density"].default_value = d


# hero only: warm corridor light washing the back-right corner (reads as the door glow behind him, out of focus)
DOOR_SPILL = C.area("door_spill", (W - 0.25, DOOR_Y1 - 0.1, 1.3), (W - 0.3, BACK, 1.3), 0.0, C.kelvin(3000), 0.3, 1.2, spread=50)

BULB_L = C.point("bulb_l", tuple(BULB + Vector((0, 0, -0.05))), 25, C.kelvin(2600), 0.03)
C.haze("haze", (0, (BACK + FRONT) / 2, H / 2), (2 * W - 0.05, BACK - FRONT - 0.1, H - 0.05), 0.006, "#cfe3e0", 0.5)

# ---------------------------------------------------------------- shots
# NOTE hero: the camera sits 5 cm from the left wall, so the leftmost ~250 px of the 1920 px frame are the unlit
# wall edge (a pure black strip). The published site/renders/char/hero.jpg has that strip cropped off
# (1670x1080); after re-rendering the hero, crop it again: Image.open(p).crop((250, 0, 1920, 1080)).
SHOTS = [
    C.Shot("hero", dict(loc=(-1.7, -3.25, 1.6), target=(0.0, -0.05, 1.5), lens=85, fstop=1.8, focus=tuple(EYES),
                        shift=(-0.14, 0.0)),
           "男主角的半身肖像：艙門的暖光打亮側臉，舷窗外的暴風雨在身後勾出青綠色輪廓。", kind="hero",
           setup=hero_setup, teardown=hero_teardown, exposure=-0.2),
    C.Shot("card", dict(loc=(-1.25, -2.7, 1.25), target=(0.05, 0.0, 0.92), lens=32),
           "三分之四前側全身：飛行夾克、紅圍巾、工裝褲與靴子，右後方艙門透出暖光。", kind="card"),
    C.Shot("s1", dict(loc=(1.25, -3.1, 1.15), target=(0.0, 0.0, 0.92), lens=35),
           "三分之四前視全身，身後是置物櫃與舷窗。"),
    C.Shot("s2", dict(loc=(-1.0, 2.2, 1.3), target=(0.0, 0.0, 0.92), lens=26),
           "背側視角：夾克背面、褲子與靴子的層次。", setup=rear_setup, teardown=rear_teardown),
    C.Shot("s3", dict(loc=(-0.4, -0.95, 1.56), target=(0.0, -0.05, 1.6), lens=70, fstop=2.0, focus=tuple(EYES)),
           "胸像特寫：額頭上的黃銅護目鏡、捲髮與紅圍巾。"),
    C.Shot("s4", dict(loc=(0.2, -0.48, 1.76), target=(-0.01, -0.11, 1.655), lens=85, fstop=2.2, focus=(0.0, -0.13, 1.66)),
           "護目鏡特寫：黃銅鏡框、鏡片反光、皮革綁帶與捲髮。"),
]
CAPTIONS = {"clay": "白模：與三分之四前視同一鏡頭，只看造型與比例。",
            "wire": "線框：同一鏡頭顯示角色身體、服裝與配件的實際佈線。"}
TURN = dict(loc=(0.0, -3.4, 1.1), target=(0.0, 0.0, 0.9), lens=32)

C.run(args, "char", model, SHOTS, clay_wire_of="s1", turn=TURN, turn_mode="model", captions_extra=CAPTIONS)
