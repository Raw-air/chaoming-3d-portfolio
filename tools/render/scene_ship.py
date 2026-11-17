"""CRASH aircraft (key 'ship', 飛船 重拆.obj) parked in a stormy hangar bay.

  & $blender -b --factory-startup --python tools\\render\\scene_ship.py -- --quality draft [--only hero,s1] [--turn] [--out DIR]
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402
import common as C  # noqa: E402
import modellib as ML  # noqa: E402

args = C.parse_args()
C.reset()

# ---------------------------------------------------------------- model
PROPS = ("圆环", "圆环.001")
GEAR = ("Cube.001", "Cube.002", "Cube.007")


def prep(objs):
    """Turn both propellers so no blade points at the floor (they reach below the gear in the source file)."""
    import numpy as np
    for o in objs:
        if o.name not in PROPS:
            continue
        a, b = ML.obb(o); c = (a + b) / 2
        best = None
        for deg in range(0, 90, 3):
            M = Matrix.Translation(c) @ Matrix.Rotation(math.radians(deg), 4, "Y") @ Matrix.Translation(-c)
            co = np.empty(len(o.data.vertices) * 3, dtype=np.float32); o.data.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3) - np.array(c)
            r = math.radians(deg)
            z = -math.sin(r) * co[:, 0] + math.cos(r) * co[:, 2]
            if best is None or z.min() > best[1]:
                best = (deg, z.min(), M)
        ML.transform([o], best[2])
        C.log(f"prop {o.name}: rotated {best[0]} deg")


model = C.load("ship", scale=2.2, ground=GEAR, prep=prep)
mn, mx = model.bounds
C.log("ship bounds", [round(v, 2) for v in mn], [round(v, 2) for v in mx])

LOOKS = {
    "ship_hull": ("painted", dict(color="#dedcd4", rough=0.4, grime=0.55, wear=0.4, panels=(1.5, 1.9, 1.1),
                                  seam_width=0.012, coat=0.15)),
    "ship_panel": ("painted", dict(color="#8a8f83", rough=0.45, grime=0.6, wear=0.5, panels=(0.8, 0.8, 0.8))),
    "ship_engine": ("painted", dict(color="#2d3338", metal=0.55, rough=0.38, grime=0.5, wear=0.6,
                                    panels=(0.9, 1.1, 0.7), grime_color="#14110d", under="#9aa0a6")),
    "ship_engine2": ("painted", dict(color="#3a4145", metal=0.55, rough=0.4, grime=0.5, wear=0.6,
                                     panels=(0.9, 1.1, 0.7), grime_color="#14110d", under="#9aa0a6")),
    "metal_dark": ("metal", dict(color="#2e3236", rough=0.42, grime=0.4)),
    "metal_mid": ("metal", dict(color="#7d848c", rough=0.3, brushed=0.6, grime=0.35)),
    "metal_light": ("metal", dict(color="#b9c0c8", rough=0.22, brushed=0.5, grime=0.2)),
    "copper": ("metal", dict(color="#c47a48", rough=0.3, grime=0.55)),
    "ship_vent": ("metal", dict(color="#2a2e32", rough=0.45, grime=0.5)),
    "ship_door": ("painted", dict(color="#a3302a", rough=0.38, grime=0.45, wear=0.5, panels=None)),
    "ship_glass": ("tinted_glass", dict(color="#0b2223", rough=0.03, glow="#1fd6c4", glow_strength=0.02)),
}
C.apply_looks(model.objs, LOOKS)

# ---------------------------------------------------------------- set: hangar bay
W, BACK, FRONT, H = 22.0, 20.0, -30.0, 18.0     # half width, back wall y (door), front y, roof height
DOOR_W, DOOR_H = 13.0, 13.5                      # half width / height of the door opening

M_FLOOR = C.material("concrete", "floor", color="#4a4d50", wet=0.85, rough=0.55, joints=4.0)
M_APRON = C.material("concrete", "apron", color="#3a3d40", wet=1.0, rough=0.5, joints=6.0)
M_WALL = C.material("painted", "wall", color="#2c2f30", rough=0.6, grime=0.7, wear=0.3, panels=(1.2, 1000, 3.0),
                    seam_width=0.02, space="world", streaks=0.9)
M_STEEL = C.material("painted", "steel", color="#3d4446", rough=0.5, grime=0.7, wear=0.6, panels=None, space="world")
M_YELLOW_STEEL = C.material("painted", "ysteel", color="#c99a1e", rough=0.45, grime=0.6, wear=0.7, panels=None,
                            space="world")
M_ROOF = C.material("painted", "roof", color="#1b2022", rough=0.7, grime=0.5, wear=0.1, panels=(1000, 1.0, 1000),
                    space="world")
M_PAINT_Y = C.material("floor_paint", "paint_y", color="#e0a51c", wet=0.85)
M_PAINT_W = C.material("floor_paint", "paint_w", color="#d8d8d2", wet=0.85)
M_PAINT_K = C.material("floor_paint", "paint_k", color="#111111", wet=0.85, wear=0.2)
M_CRATE_W = C.material("wood", "crate_wood", color="#8a6440", rough=0.62, grain=4.0, coat=0.0, space="world")
M_CRATE_G = C.material("painted", "crate_green", color="#4b5537", rough=0.5, grime=0.6, wear=0.6, panels=None,
                       space="world")
M_CRATE_O = C.material("painted", "crate_orange", color="#b5531f", rough=0.45, grime=0.55, wear=0.6, panels=None,
                       space="world")
M_BARREL_R = C.material("painted", "barrel_red", color="#8e231c", rough=0.4, grime=0.6, wear=0.7, panels=None,
                        space="world")
M_BARREL_B = C.material("painted", "barrel_blue", color="#1f4a6e", rough=0.4, grime=0.6, wear=0.7, panels=None,
                        space="world")
M_RUBBER = C.material("rubber", "rubber", space="world")
M_HOSE = C.material("rubber", "hose", color="#1d1d1f", rough=0.55, space="world")
M_STENCIL = C.material("flat", "stencil", color="#e8e2d0", rough=0.7)
M_STENCIL_K = C.material("flat", "stencil_k", color="#151515", rough=0.7)
M_SIGN = C.material("painted", "sign", color="#d9d2bd", rough=0.6, grime=0.6, wear=0.2, panels=None, space="world")
M_CHROME = C.material("metal", "chrome", color="#d0d4d8", rough=0.15, grime=0.1, space="world")
M_LAMP = C.material("emissive", "lamp_warm", color=C.kelvin(2700), strength=25.0)
M_LAMP_COOL = C.material("emissive", "lamp_cool", color="#cfeaff", strength=10.0)

C.floor(70.0, M_FLOOR).location = (0, -5, 0)
C.plane("apron", (90, 50), (0, BACK + 25, -0.005), mat=M_APRON)

# back wall with door opening
C.box("wall_back_L", (W - DOOR_W, 0.6, H), (-(W + DOOR_W) / 2, BACK + 0.3, 0), mat=M_WALL, origin="bottom", bevel=0)
C.box("wall_back_R", (W - DOOR_W, 0.6, H), ((W + DOOR_W) / 2, BACK + 0.3, 0), mat=M_WALL, origin="bottom", bevel=0)
C.box("wall_back_T", (2 * DOOR_W, 0.6, H - DOOR_H), (0, BACK + 0.3, DOOR_H), mat=M_WALL, origin="bottom", bevel=0)
C.box("wall_L", (0.6, BACK - FRONT, H), (-W - 0.3, (BACK + FRONT) / 2, 0), mat=M_WALL, origin="bottom", bevel=0)
C.box("wall_R", (0.6, BACK - FRONT, H), (W + 0.3, (BACK + FRONT) / 2, 0), mat=M_WALL, origin="bottom", bevel=0)
C.box("wall_F", (2 * W, 0.6, H), (0, FRONT - 0.3, 0), mat=M_WALL, origin="bottom", bevel=0)
C.box("roof", (2 * W + 2, BACK - FRONT + 2, 0.5), (0, (BACK + FRONT) / 2, H), mat=M_ROOF, origin="bottom", bevel=0)

# door frame: heavy yellow jambs + lintel beam with hazard stripes, door leaves slid open (partly visible)
for sx in (-1, 1):
    C.box(f"jamb_{sx}", (1.0, 1.4, DOOR_H), (sx * (DOOR_W + 0.3), BACK - 0.2, 0), mat=M_YELLOW_STEEL, origin="bottom",
          bevel=0.04)
    C.box(f"door_leaf_{sx}", (7.0, 0.5, DOOR_H - 0.3), (sx * (DOOR_W - 2.2), BACK + 1.2, 0.0), mat=M_STEEL,
          origin="bottom", bevel=0.05)
    for k in range(5):   # leaf ribs
        C.box(f"door_rib_{sx}_{k}", (7.0, 0.25, 0.25), (sx * (DOOR_W - 2.2), BACK + 0.85, 1.2 + k * 2.6),
              mat=M_STEEL, bevel=0.03)
C.box("lintel", (2 * DOOR_W + 2.6, 1.4, 1.2), (0, BACK - 0.2, DOOR_H), mat=M_YELLOW_STEEL, origin="bottom", bevel=0.04)


def hazard(name, x0, x1, y, z0, z1, n=None, w=0.6, plane="XZ", mat_y=M_PAINT_Y, mat_k=M_PAINT_K):
    """Diagonal yellow/black stripes as parallelogram quads on an XZ (wall) or XY (floor) plane."""
    bm = bmesh.new()
    L = x1 - x0; n = n or int(L / w)
    hgt = z1 - z0
    for i in range(n):
        a = x0 + i * L / n; b = a + L / n * 0.5
        quad = [(a, z0), (b, z0), (b + hgt * 0.6, z1), (a + hgt * 0.6, z1)]
        quad = [(min(max(p[0], x0), x1), p[1]) for p in quad]
        vs = [bm.verts.new((p[0], y, p[1]) if plane == "XZ" else (p[0], p[1], y)) for p in quad]
        bm.faces.new(vs)
    o = C._obj_from_bm(name, bm, mat_y)
    k = C.box(name + "_bg", (x1 - x0, 0.02, hgt) if plane == "XZ" else (x1 - x0, hgt, 0.004),
              ((x0 + x1) / 2, y + (0.012 if plane == "XZ" else 0), (z0 + z1) / 2) if plane == "XZ" else
              ((x0 + x1) / 2, (z0 + z1) / 2, y - 0.002), mat=mat_k, bevel=0)
    return o, k


hazard("lintel_haz", -DOOR_W - 0.9, DOOR_W + 0.9, BACK - 0.92, DOOR_H + 0.15, DOOR_H + 1.05, w=0.9)
# threshold stripes on the floor at the door
hazard("floor_haz", -DOOR_W, DOOR_W, 0.003, BACK - 2.2, BACK - 1.0, w=1.0, plane="XY")

# wall signage
C.text("sign_bay", "HANGAR 07", 2.2, (0, BACK - 0.95, DOOR_H + 2.9), (90, 0, 0), M_SIGN, C.FONT_STENCIL,
       extrude=0.03, spacing=1.15)
C.text("sign_tc", "七號機庫", 1.4, (-17.5, BACK - 0.05, 9.0), (90, 0, 0), M_SIGN, C.FONT_TC, extrude=0.02)
C.text("sign_warn", "注意 螺旋槳", 0.7, (17.5, BACK - 0.05, 3.0), (90, 0, 0), M_PAINT_Y, C.FONT_TC, extrude=0.01)
C.text("sign_side", "NO SMOKING  ·  禁止吸菸", 0.55, (W - 0.05, -6, 3.2), (90, 0, -90), M_SIGN, C.FONT_TC, extrude=0.01)
C.text("sign_side2", "BAY 07", 1.6, (-W + 0.05, 7.0, 10.0), (90, 0, 90), M_SIGN, C.FONT_STENCIL, extrude=0.02)

# structural ribs: portal frames + roof trusses
for i, y in enumerate(range(int(FRONT) + 4, int(BACK) - 1, 6)):
    for sx in (-1, 1):
        C.box(f"col_{i}_{sx}", (0.7, 0.9, H), (sx * (W - 0.5), y, 0), mat=M_STEEL, origin="bottom", bevel=0.03)
        C.box(f"col_flange_{i}_{sx}", (0.15, 0.9, H), (sx * (W - 0.95), y, 0), mat=M_STEEL, origin="bottom",
              bevel=0.02)
        C.box(f"knee_{i}_{sx}", (3.2, 0.5, 0.5), (sx * (W - 2.0), y, H - 2.3), (0, sx * 35, 0), mat=M_STEEL,
              bevel=0.03)
    C.box(f"truss_bot_{i}", (2 * W, 0.45, 0.45), (0, y, H - 3.2), mat=M_STEEL, bevel=0.03)
    C.box(f"truss_top_{i}", (2 * W, 0.5, 0.6), (0, y, H - 0.6), mat=M_STEEL, bevel=0.03)
    for k in range(-7, 8):     # diagonal web members
        x = k * 2.9
        C.box(f"web_{i}_{k}", (0.18, 0.25, 3.3), (x, y, H - 1.95), (0, 40 if k % 2 else -40, 0), mat=M_STEEL, bevel=0)
    # cool strip light under every truss
    C.strip(f"truss_light_{i}", (-W + 3, y, H - 3.5), (W - 3, y, H - 3.5), 0.12, "#bfe4ff", 6.0)

# catwalk along the left wall
CW_Z, CW_X = 6.5, -W + 1.6
C.box("catwalk_deck", (2.2, BACK - FRONT - 4, 0.12), (CW_X, (BACK + FRONT) / 2, CW_Z), mat=M_STEEL, bevel=0.01)
for k in range(int(FRONT) + 3, int(BACK) - 2, 3):
    C.pipe(f"cw_post_{k}", (CW_X + 1.05, k, CW_Z), (CW_X + 1.05, k, CW_Z + 1.1), 0.035, M_YELLOW_STEEL)
    C.box(f"cw_bracket_{k}", (2.2, 0.12, 0.25), (CW_X, k, CW_Z - 0.2), mat=M_STEEL, bevel=0.01)
C.pipe("cw_rail", (CW_X + 1.05, FRONT + 2, CW_Z + 1.1), (CW_X + 1.05, BACK - 2, CW_Z + 1.1), 0.04, M_YELLOW_STEEL)
C.pipe("cw_rail2", (CW_X + 1.05, FRONT + 2, CW_Z + 0.55), (CW_X + 1.05, BACK - 2, CW_Z + 0.55), 0.03, M_YELLOW_STEEL)
# warm caged bulbs on the catwalk
for k, y in enumerate(range(-20, 18, 7)):
    C.cylinder(f"cw_bulb_{k}", 0.09, 0.2, (CW_X - 0.9, y, CW_Z + 2.0), mat=M_LAMP, role="keep")
    C.point(f"cw_bulb_l_{k}", (CW_X - 0.7, y, CW_Z + 1.9), 120, C.kelvin(2400), 0.08)

# wall pipes along the right wall (copper + steel) with a hose reel
for j, (z, r, m) in enumerate(((3.6, 0.12, "copper"), (4.0, 0.08, "steel"), (4.35, 0.08, "steel"))):
    mm = C.material("metal", "wallpipe_cu", color="#b8703f", rough=0.35, grime=0.6, space="world") if m == "copper" else M_CHROME
    C.pipe(f"wallpipe_{j}", (W - 0.6, FRONT + 1, z), (W - 0.6, BACK - 1, z), r, mm)

# pendant work lamps over the ship
for k, (x, y) in enumerate(((-6.5, -4.0), (6.5, -4.0), (0.0, 6.0))):
    C.pipe(f"pend_rod_{k}", (x, y, H - 3.2), (x, y, 11.5), 0.03, M_STEEL)
    C.cylinder(f"pend_shade_{k}", 0.6, 0.45, (x, y, 11.3), mat=M_STEEL, segments=24)
    C.cylinder(f"pend_bulb_{k}", 0.45, 0.04, (x, y, 11.06), mat=M_LAMP, segments=24, role="keep")
    C.spot(f"pend_spot_{k}", (x, y, 11.0), (x * 0.6, y * 0.6, 0), 2000, C.kelvin(4300), 75, 0.6, 0.4)

# tripod flood lights in front of the ship (warm practicals)
TRIPODS = [(-12.5, -5.5, (-2.0, -2.0, 2.0), 3200), (12.0, -4.0, (2.0, -2.0, 2.0), 1000)]
for k, (x, y, tgt, pw) in enumerate(TRIPODS):
    for a in range(3):
        ang = math.radians(a * 120 + 30)
        C.pipe(f"tri_leg_{k}_{a}", (x + math.cos(ang) * 0.8, y + math.sin(ang) * 0.8, 0), (x, y, 2.6), 0.03, M_STEEL)
    head = C.box(f"tri_head_{k}", (0.75, 0.5, 0.32), (x, y, 2.8), mat=M_YELLOW_STEEL, bevel=0.04)
    C.look_at(head, tgt)
    d = (Vector(tgt) - Vector((x, y, 2.8))).normalized()
    face = C.box(f"tri_face_{k}", (0.62, 0.38, 0.02), Vector((x, y, 2.8)) + d * 0.165, mat=M_LAMP, bevel=0, role="keep")
    face.rotation_euler = head.rotation_euler.copy()
    C.spot(f"tri_spot_{k}", tuple(Vector((x, y, 2.8)) + d * 0.3), tgt, pw, C.kelvin(4800), 60, 0.5, 0.25)
    C.cable(f"tri_cable_{k}", [(x, y, 2.5), (x + 0.3, y - 0.2, 0.03), (x + 2.5, y - 4.0, 0.03), (x * 1.6, FRONT + 4, 0.03)],
            0.02, M_RUBBER)

# crates & barrels (kept > 11 m from the ship centre so the turntable can spin)
rng = __import__("random").Random(7)


def crate(name, loc, size, mat, rotz=0.0, label=None, label_tc=False):
    o = C.box(name, size, loc, (0, 0, rotz), mat=mat, origin="bottom", bevel=0.03)
    if mat is M_CRATE_W:  # plank battens
        for zz in (0.12, size[2] - 0.12):
            C.box(name + f"_bat{zz:.1f}", (size[0] + 0.04, size[1] + 0.04, 0.12),
                  (loc[0], loc[1], loc[2] + zz), (0, 0, rotz), mat=mat, bevel=0.01)
    if label:
        r = math.radians(rotz)
        n = Vector((math.sin(r), -math.cos(r), 0))  # front face normal (-Y rotated)
        p = Vector(loc) + n * (size[1] / 2 + 0.006) + Vector((0, 0, size[2] * 0.55))
        C.text(name + "_lbl", label, min(size[0], size[2]) * (0.22 if not label_tc else 0.2), tuple(p), (90, 0, rotz),
               M_STENCIL_K if mat is M_CRATE_W else M_STENCIL, C.FONT_TC if label_tc else C.FONT_STENCIL)
    return o


crate("crate_a", (-15.5, -6.0, 0), (2.4, 1.6, 1.6), M_CRATE_W, 8, "AX-07  FRAGILE")
crate("crate_b", (-15.2, -6.2, 1.63), (1.6, 1.2, 1.2), M_CRATE_G, -4, "零件")
crate("crate_c", (-17.8, -3.0, 0), (1.8, 1.8, 1.8), M_CRATE_O, 22, "易燃", True)
crate("crate_d", (14.5, 9.5, 0), (2.6, 1.8, 1.4), M_CRATE_G, -12, "SPARE PARTS")
crate("crate_e", (15.0, 9.6, 1.43), (1.4, 1.2, 1.0), M_CRATE_W, -3, "AX-07")
crate("crate_f", (17.5, 6.5, 0), (1.6, 1.6, 2.0), M_CRATE_W, 40)
crate("crate_g", (-14.0, 12.5, 0), (2.0, 1.4, 1.2), M_CRATE_O, 5, "CRASH")
for k, (x, y) in enumerate(((13.5, -9.0), (14.3, -9.4), (13.9, -10.2), (15.2, -8.6), (-13.2, 9.5), (-12.6, 10.2))):
    m = M_BARREL_R if k % 3 else M_BARREL_B
    C.cylinder(f"barrel_{k}", 0.32, 0.92, (x, y, 0), (0, 0, rng.uniform(0, 90)), m, origin="bottom")
    for zz in (0.25, 0.65):
        C.cylinder(f"barrel_{k}_hoop{zz}", 0.335, 0.03, (x, y, zz), mat=m)

# fuel cart + hose snaking across the wet floor into the fuselage (hidden during the turntable)
CART = (-10.0, 3.5)
C.box("fuel_cart", (2.6, 1.4, 1.2), (CART[0], CART[1], 0.45), (0, 0, 75), mat=M_CRATE_O, origin="bottom", bevel=0.06)
C.cylinder("fuel_tank", 0.55, 2.2, (CART[0], CART[1], 1.55), (0, 90, 75), M_BARREL_R)
for k, (dx, dy) in enumerate(((-0.9, -0.7), (0.9, -0.7), (-0.9, 0.7), (0.9, 0.7))):
    r = math.radians(75); x = CART[0] + dx * math.cos(r) - dy * math.sin(r); y = CART[1] + dx * math.sin(r) + dy * math.cos(r)
    C.cylinder(f"cart_wheel_{k}", 0.25, 0.18, (x, y, 0.25), (90, 0, 75), M_RUBBER)
hose = C.cable("fuel_hose", [(CART[0] - 0.4, CART[1] - 0.5, 1.2), (CART[0] - 1.2, CART[1] - 1.0, 0.06),
                             (-7.5, 1.0, 0.06), (-5.0, -0.2, 0.06), (-3.2, 0.4, 0.06), (-2.3, 0.6, 0.9), (-2.0, 0.8, 1.9)],
               0.07, M_HOSE)
hose["hide_turn"] = True
for o in [o for o in bpy.context.scene.objects if o.name.startswith(("fuel_", "cart_"))]:
    o["hide_turn"] = True
# wheel chocks at the gear
for k, (gx, gy) in enumerate(((0.0, -2.65), (-3.4, 0.0), (3.4, 0.0))):
    for s in (-1, 1):
        ch = C.box(f"chock_{k}_{s}", (0.7, 0.25, 0.22), (gx, gy + s * 1.15, 0), mat=M_CRATE_O, origin="bottom", bevel=0.03)
        ch.parent = model.pivot   # chocks spin with the aircraft on the turntable

# floor markings: centre line, parking ring, bay number
C.plane("mark_centre", (0.3, BACK - FRONT), (0, (BACK + FRONT) / 2, 0.002), mat=M_PAINT_Y)
bm = bmesh.new()
segs = 128
outer = [bm.verts.new((math.cos(2 * math.pi * i / segs) * 10.4, math.sin(2 * math.pi * i / segs) * 10.4, 0.003)) for i in range(segs)]
inner = [bm.verts.new((math.cos(2 * math.pi * i / segs) * 10.1, math.sin(2 * math.pi * i / segs) * 10.1, 0.003)) for i in range(segs)]
for i in range(segs):
    j = (i + 1) % segs
    bm.faces.new((outer[i], outer[j], inner[j], inner[i]))
C._obj_from_bm("mark_ring", bm, M_PAINT_W)
C.text("mark_07", "07", 3.2, (-4.5, -12.2, 0.004), (0, 0, 180), M_PAINT_W, C.FONT_STENCIL)
C.text("mark_bay", "BAY", 1.0, (-4.5, -14.3, 0.004), (0, 0, 180), M_PAINT_W, C.FONT_STENCIL, spacing=1.3)
C.plane("mark_stop", (5.0, 0.3), (0, -8.2, 0.002), mat=M_PAINT_Y)
for k in range(3):
    y = 13.0 - k * 1.6
    for s in (-1, 1):
        o = C.plane(f"chev_{k}_{s}", (1.6, 0.3), (s * 0.55, y, 0.002), (0, 0, s * -35), M_PAINT_Y)

# ---------------------------------------------------------------- storm outside + lighting
C.world("#020406", 1.0)
C.sky_card("sky", (0, 95, 22), (240, 90), (90, 0, 0), top="#020707", bottom="#5fd8c4", strength=1.3, clouds=1.0)
# distant silhouettes on the apron (another hangar, a mast) to give depth
C.box("far_mast", (0.6, 0.6, 30), (22, 60, 0), mat=M_ROOF, origin="bottom", bevel=0)
C.point("mast_beacon", (22, 60, 30.4), 400, "#ff2a1a", 0.2)

KEY = C.sun("storm_key", (0.25, -1.0, -0.42), 2.2, "#7fe6d6", angle=4)
C.area("door_fill", (0, BACK + 3, DOOR_H / 2), (0, 0, 2), 4000, "#5fd4c8", 2 * DOOR_W, DOOR_H, spread=60)
C.area("rim_top", (4, 10, 14), (0, 0, 2), 3000, "#9fe8ff", 6, 3)
C.area("front_bounce", (-2, -24, 6), (0, 0, 2), 1200, C.kelvin(6000), 10, 4)
C.haze("haze", (0, (BACK + FRONT) / 2 + 3, H / 2), (2 * W + 4, BACK - FRONT + 6, H + 2), 0.0035, "#cfe3e0", 0.45)
C.haze("haze_out", (0, BACK + 14, 12), (90, 24, 24), 0.003, "#a9d6cf", 0.3)
C.spot("storm_shaft", (6, BACK + 22, 26), (-1, -2, 0), 60000, "#8ff0e0", 22, 0.35, 0.5)

# rain sheets beyond the door (thin emissive/transparent streaks)
def rain(name, n, x0, x1, y0, y1, z1, seed=3):
    import random
    R = random.Random(seed)
    bm = bmesh.new()
    for i in range(n):
        x = R.uniform(x0, x1); y = R.uniform(y0, y1); z = R.uniform(0, z1); L = R.uniform(0.8, 1.8); w = 0.012 + 0.01 * (y - y0) / (y1 - y0)
        dx = 0.25 * L
        vs = [bm.verts.new(p) for p in ((x - w, y, z), (x + w, y, z), (x + w + dx, y, z + L), (x - w + dx, y, z + L))]
        bm.faces.new(vs)
    m, nt, out = C.new_mat(name + "_mat")
    em = C.N(nt, "Emission", {"Color": C.col("#c9fff1"), "Strength": 1.6})
    tr = C.N(nt, "BsdfTransparent")
    mx = C.N(nt, "MixShader", {"Fac": 0.35})
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    o = C._obj_from_bm(name, bm, m, role="keep")
    o.visible_shadow = False
    return o


rain("rain", 1400, -30, 30, BACK + 3, BACK + 45, 24)

# ---------------------------------------------------------------- shots
NOSE = (0.0, -5.6, 1.9)
SHOTS = [
    C.Shot("hero", dict(loc=(-3.2, -19.0, 1.25), target=(0.3, 0.0, 2.75), lens=35, fstop=4.0, focus=(0.0, -6.0, 2.0)),
           "停機庫內的 CRASH 飛機：暴風雨的青綠天光從敞開的機庫大門灌入，與工作燈的暖光在濕地面上交會。", kind="hero"),
    C.Shot("card", dict(loc=(-13.0, -15.0, 5.0), target=(0.5, 0.3, 1.7), lens=36),
           "三分之四前側視角，飛機停在七號停機位。", kind="card"),
    C.Shot("s1", dict(loc=(12.5, -15.0, 3.8), target=(0.0, 0.0, 1.8), lens=36),
           "三分之四前視：米白機身、深色引擎艙與前後四具渦輪。"),
    C.Shot("s2", dict(loc=(11.5, 16.5, 1.8), target=(0.0, 0.0, 2.4), lens=30),
           "後側視角：機尾雙渦輪與引擎艙，背景是機庫內部的走道與暖色燈。"),
    C.Shot("s3", dict(loc=(8.8, -9.0, 1.1), target=(5.7, -2.2, 1.5), lens=65, fstop=2.0, focus=(5.9, -2.4, 1.5)),
           "引擎特寫：螺旋槳、引擎艙與銅管細節。"),
    C.Shot("s4", dict(loc=(-4.6, -10.0, 4.4), target=(0.0, -4.0, 2.5), lens=80, fstop=2.2, focus=(0.0, -4.3, 2.6)),
           "駕駛艙特寫：深青色座艙玻璃的反光與機鼻的面板接縫。"),
]
CAPTIONS = {"clay": "白模：與三分之四前視同一鏡頭，只看造型與比例。",
            "wire": "線框：同一鏡頭顯示模型的實際四邊形佈線。"}
TURN = dict(loc=(0.0, -24.0, 5.5), target=(0.0, 0.0, 1.8), lens=38)

C.run(args, "ship", model, SHOTS, clay_wire_of="s1", turn=TURN, turn_mode="model", captions_extra=CAPTIONS)
