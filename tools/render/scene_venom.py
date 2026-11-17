"""Digital-sculpt bust (key 'venom', 猛毒雕刻.fbx, 1.71M tris) on a stone plinth in a dark sculptor's studio.

  & $blender -b --factory-startup --python tools\\render\\scene_venom.py -- --quality draft [--only hero,s1] [--turn] [--out DIR]

Full-resolution sculpt for every still (1.35M-tri body + 92 teeth: ~0.8 GB peak, BVH build is quick).
Wire pass: the body is a single remeshed island (no multires base to recover, Un-Subdivide fails), so the
wire shot uses a Collapse-decimated copy of the body (~26k tris, dark 'blueprint' body) and an Un-Subdivided
copy of the teeth (true quads); the caption says so. The full 1.35M body under a Wireframe modifier is a solid
white blob at 1600 px and peaked at ~5 GB RAM. Clay and wire are rendered here (not by C.run) so they can use
their own exposure: the lights are set for a near-black material. The turntable (EEVEE) uses the full mesh.
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402
import common as C  # noqa: E402
import modellib as ML  # noqa: E402

args = C.parse_args()
C.reset()

PLINTH_H = 1.0

# ====================================================================== model
model = C.load("venom", size=0.8, location=(0, 0, PLINTH_H))
mn, mx = model.bounds
C.log("venom bounds", [round(v, 3) for v in mn], [round(v, 3) for v in mx])
BODY = model.by_name("角色"); TEETH = model.by_name("牙"); BASE = model.by_name("我沒有黏在一起")

# ---------------------------------------------------------------- mouth region as a point attribute
# The body is one remeshed island and the eyes are not sculpted as separate forms, so only the mouth is
# separable: body vertices inside the (slightly grown) convex hull of the 92 teeth = gums, mouth cavity and the
# base of the tongue -> 'mouth' attribute (0..1, soft edge) used by the body shader.
def verts_np(o):
    co = np.empty(len(o.data.vertices) * 3, dtype=np.float32)
    o.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def mouth_attr(body, teeth, grow=1.12, soft=0.012, lift=(0.0, 0.0, 0.0)):
    tv = verts_np(teeth)
    ctr = tv.mean(axis=0)
    bm = bmesh.new()
    for p in tv[::7]:
        bm.verts.new(((p - ctr) * grow + ctr + np.array(lift)).tolist())
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    bm.faces.ensure_lookup_table(); bm.normal_update()
    P = np.array([f.verts[0].co[:] for f in bm.faces], np.float32)
    Nn = np.array([f.normal[:] for f in bm.faces], np.float32)
    # make normals point outwards
    s = np.sign(((P - ctr) * Nn).sum(axis=1)); s[s == 0] = 1; Nn *= s[:, None]
    bm.free()
    co = verts_np(body)
    d = np.full(len(co), -1e9, np.float32)
    for i in range(0, len(co), 50000):
        c = co[i:i + 50000]
        d[i:i + 50000] = ((c[:, None, :] - P[None]) * Nn[None]).sum(axis=2).max(axis=1)
    m = np.clip(0.5 - d / soft, 0, 1).astype(np.float32)
    at = body.data.attributes.get("mouth") or body.data.attributes.new("mouth", "FLOAT", "POINT")
    at.data.foreach_set("value", m)
    C.log(f"mouth region: {int((m > 0.5).sum())} of {len(m)} verts")


mouth_attr(BODY, TEETH)


# ====================================================================== materials
def symbiote_mat(name):
    """Wet black symbiote: near-black base with a faint blue shift, clear coat, roughness breakup (slimy vs
    drier patches), fine skin grain (thin-film iridescence was tried: it tints everything green/gold); mouth region -> dark wet red flesh with SSS."""
    m, nt, out = C.new_mat(name)
    v = C.coords(nt, "object")
    n_big = C.noise(nt, v, 7.0, 5, 0.6)
    n_mid = C.noise(nt, v, 28.0, 6, 0.6)
    vor = C.N(nt, "TexVoronoi", {"Vector": v, "Scale": 700.0}, feature="F1").outputs["Distance"]
    base = C.mix(nt, C.maprange(nt, n_big, 0.35, 0.7), C.col("#020203"), C.col("#0a0c13"))
    rough = C.maprange(nt, n_mid, 0.3, 0.7, 0.32, 0.6)          # satin black base ...
    coat_r = C.maprange(nt, n_big, 0.35, 0.7, 0.02, 0.14)       # ... under a sharp wet coat
    tongue = C.N(nt, "Attribute", attribute_name="mouth", attribute_type="GEOMETRY").outputs["Fac"]
    tcol = C.mix(nt, C.maprange(nt, n_mid, 0.3, 0.7), C.col("#2a070b"), C.col("#561722"))
    # deeper in the mouth -> darker (occlusion)
    ao = C.N(nt, "AmbientOcclusion", {"Distance": 0.05}, samples=2, only_local=True).outputs["AO"]
    tcol = C.mix(nt, C.maprange(nt, ao, 0.9, 0.3, 0.0, 0.85), tcol, C.col("#080203"))
    col_ = C.mix(nt, tongue, base, tcol)
    rough = C.mixf(nt, tongue, rough, 0.28)
    h = C.mathn(nt, "ADD", C.mathn(nt, "MULTIPLY", vor, 0.6), C.mathn(nt, "MULTIPLY", n_mid, 0.25))
    b = C.principled(nt, out, color=col_, rough=rough, coat=0.55, coat_rough=coat_r, spec=0.3,
                     sss=C.mathn(nt, "MULTIPLY", tongue, 0.12), sss_radius=(0.8, 0.2, 0.15), sss_scale=0.003,
                     normal=C.bump(nt, h, 0.12, 0.0006))
    return m


def teeth_mat(name):
    m, nt, out = C.new_mat(name)
    v = C.coords(nt, "object")
    n = C.noise(nt, v, 220.0, 4, 0.6)
    ao = C.N(nt, "AmbientOcclusion", {"Distance": 0.012}, samples=4, only_local=False).outputs["AO"]
    col_ = C.mix(nt, C.maprange(nt, n, 0.3, 0.7, 0.0, 0.35), C.col("#e6dcc4"), C.col("#bfa880"))
    col_ = C.mix(nt, C.maprange(nt, ao, 0.9, 0.4, 0.0, 0.8), col_, C.col("#5a3d2c"))
    C.principled(nt, out, color=col_, rough=C.maprange(nt, n, 0.3, 0.7, 0.18, 0.32), sss=0.25,
                 sss_radius=(1.0, 0.7, 0.45), sss_scale=0.002, coat=0.6, coat_rough=0.08,
                 normal=C.bump(nt, n, 0.08, 0.0003))
    return m


def stone_mat(name, color="#2b2a28", color2="#121212", vein="#6b6760", rough=0.42, space="world", scale=1.0, speck=0.6):
    """Honed dark stone (basalt / nero marble): speckle, soft veins, roughness breakup, chipped edges."""
    m, nt, out = C.new_mat(name)
    v = C.coords(nt, space, 1.0 / scale)
    n_big = C.noise(nt, v, 2.2, 6, 0.62, distortion=0.8)
    vein_n = C.noise(nt, v, 3.5, 8, 0.7, distortion=2.5)
    vline = C.maprange(nt, C.mathn(nt, "ABSOLUTE", C.mathn(nt, "SUBTRACT", vein_n, 0.5)), 0.0, 0.012, 1.0, 0.0)
    speck = C.N(nt, "TexVoronoi", {"Vector": v, "Scale": 260.0}, feature="F1").outputs["Distance"]
    wn = C.N(nt, "TexWhiteNoise", {"Vector": C.vmath(nt, "FLOOR", C.vmath(nt, "MULTIPLY", v, (300, 300, 300)))},
             noise_dimensions="3D").outputs["Value"]
    col_ = C.mix(nt, C.maprange(nt, n_big, 0.35, 0.7), C.col(color), C.col(color2))
    col_ = C.mix(nt, C.mathn(nt, "MULTIPLY", C.maprange(nt, wn, 0.9, 1.0), speck), col_, C.col("#6a6660"))
    col_ = C.mix(nt, C.mathn(nt, "MULTIPLY", vline, 0.55), col_, C.col(vein))
    e = C.mathn(nt, "MULTIPLY", C.edge_mask(nt, 0.006), C.maprange(nt, n_big, 0.4, 0.6), clamp=True)
    col_ = C.mix(nt, C.mathn(nt, "MULTIPLY", e, 0.5), col_, C.col("#55524c"))
    r = C.maprange(nt, n_big, 0.3, 0.7, rough - 0.12, rough + 0.15)
    r = C.mixf(nt, e, r, 0.7)
    h = C.mathn(nt, "ADD", C.mathn(nt, "MULTIPLY", speck, 0.15), C.mathn(nt, "MULTIPLY", vline, -0.1))
    C.principled(nt, out, color=col_, rough=r, spec=0.5, normal=C.bump(nt, h, 0.15, 0.0008))
    return m


def backdrop_mat(name, color="#0d0d0e", mottle="#1d1a17", mottle2="#06070a"):
    """Old painted canvas backdrop: large soft mottling, fine weave, matte."""
    m, nt, out = C.new_mat(name)
    v = C.coords(nt, "world")
    n1 = C.noise(nt, v, 0.6, 6, 0.65, distortion=0.5)
    n2 = C.noise(nt, v, 2.5, 5, 0.6)
    col_ = C.mix(nt, C.maprange(nt, n1, 0.4, 0.7), C.col(color), C.col(mottle))
    col_ = C.mix(nt, C.maprange(nt, n2, 0.55, 0.75, 0.0, 0.7), col_, C.col(mottle2))
    wa = C.N(nt, "TexWave", {"Vector": v, "Scale": 300.0}, wave_type="BANDS", bands_direction="X").outputs["Factor"]
    wb = C.N(nt, "TexWave", {"Vector": v, "Scale": 300.0}, wave_type="BANDS", bands_direction="Z").outputs["Factor"]
    C.principled(nt, out, color=col_, rough=0.85, spec=0.25, sheen=0.3,
                 normal=C.bump(nt, C.mathn(nt, "ADD", C.mathn(nt, "MULTIPLY", wa, wb), n2), 0.2, 0.002))
    return m


M_BODY = symbiote_mat("vn_symbiote")
M_TEETH = teeth_mat("vn_teeth_m")
M_BASEPLATE = stone_mat("vn_baseplate", "#1c1b1a", "#0b0b0b", "#4a4742", rough=0.3, space="object")
C.assign(BODY, M_BODY); C.assign(TEETH, M_TEETH); C.assign(BASE, M_BASEPLATE)

# ====================================================================== set: sculptor's studio
M_STONE = stone_mat("plinth_stone", "#1a1918", "#0b0b0b", "#4a4640", rough=0.38, speck=0.25)
M_STONE_L = stone_mat("plinth_stone_light", "#3a3835", "#1c1b1a", "#8a857c", rough=0.5)
M_FLOOR = C.material("concrete", "studio_floor", color="#1d1d1e", wet=0.25, rough=0.5, joints=1.2)
M_BACK = backdrop_mat("backdrop")
M_WOOD = C.material("wood", "studio_wood", color="#4a3121", rough=0.6, grain=5.0, axis="X", coat=0.1, space="world")
M_WOOD_Z = C.material("wood", "studio_wood_z", color="#4a3121", rough=0.6, grain=5.0, axis="Z", coat=0.1, space="world")
M_IRON = C.material("metal", "studio_iron", color="#2a2a2c", rough=0.5, grime=0.5, space="world")
M_CLAY_RAW = C.material("clay", "raw_clay", color="#6b5a4a", rough=0.85)
M_PLASTER = C.material("clay", "plaster", color="#9a958c", rough=0.8)
M_CLOTH = C.material("fabric", "drape", color="#1c1916", rough=0.9, weave=160.0, space="world")

C.floor(30.0, M_FLOOR)
# plinth: plinth base step, shaft, top cap
C.box("plinth_foot", (0.78, 0.78, 0.08), (0, 0, 0), mat=M_STONE, origin="bottom", bevel=0.012)
C.box("plinth_shaft", (0.6, 0.6, 0.84), (0, 0, 0.08), mat=M_STONE, origin="bottom", bevel=0.006)
C.box("plinth_cap", (0.7, 0.7, 0.08), (0, 0, 0.92), mat=M_STONE, origin="bottom", bevel=0.012)
# small blank bronze plaque on the plinth front
C.box("plaque", (0.22, 0.008, 0.07), (0, -0.304, 0.72), mat=C.material("metal", "bronze", color="#8a6a3e", rough=0.35,
                                                                    grime=0.7, space="world"), bevel=0.002)

# cyclorama sweep behind (floor -> wall), old painted canvas
def sweep(name, y0=1.4, radius=1.2, width=9.0, height=5.0, x=0.0, segs=16):
    bm = bmesh.new()
    prof = [(y0 - 1.6, 0.002)]
    for i in range(segs + 1):
        a = math.pi / 2 * i / segs
        prof.append((y0 + math.sin(a) * radius, radius - math.cos(a) * radius + 0.002))
    prof.append((y0 + radius, height))
    rows = []
    for (yy, zz) in prof:
        rows.append([bm.verts.new((x - width / 2, yy, zz)), bm.verts.new((x + width / 2, yy, zz))])
    for i in range(len(rows) - 1):
        bm.faces.new((rows[i][0], rows[i][1], rows[i + 1][1], rows[i + 1][0]))
    o = C._obj_from_bm(name, bm, M_BACK, role="keep", smooth=True)
    return o


sweep("cyc", y0=1.5, radius=1.3, width=10.0, height=5.0)

# studio props in the dark: shelf with jars & maquettes (back left), covered work on a stand (back right)
R = random.Random(5)
SHX, SHY = -2.9, 2.1
for k in range(4):
    C.box(f"shelf_{k}", (1.6, 0.4, 0.03), (SHX, SHY, 0.35 + k * 0.55), (0, 0, 8), mat=M_WOOD, bevel=0.004)
for sx in (-0.78, 0.78):
    C.box(f"shelf_side_{sx}", (0.03, 0.4, 2.0), (SHX + sx, SHY + sx * 0.14, 0.0), (0, 0, 8), mat=M_WOOD_Z, origin="bottom",
          bevel=0.004)
for k in range(3):
    z = 0.365 + k * 0.55
    xx = SHX - 0.6
    while xx < SHX + 0.6:
        kind = R.random()
        if kind < 0.4:
            h = R.uniform(0.1, 0.22)
            C.cylinder(f"jar_{k}_{xx:.2f}", R.uniform(0.04, 0.07), h, (xx, SHY - 0.05, z), mat=M_PLASTER if R.random() < 0.5
                       else M_CLAY_RAW, origin="bottom", segments=16)
        elif kind < 0.7:
            C.box(f"block_{k}_{xx:.2f}", (R.uniform(0.08, 0.15), 0.12, R.uniform(0.06, 0.2)), (xx, SHY - 0.05, z),
                  (0, 0, R.uniform(-20, 20)), mat=M_CLAY_RAW, origin="bottom", bevel=0.01)
        else:
            bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=R.uniform(0.06, 0.1))
            o = C._obj_from_bm(f"head_{k}_{xx:.2f}", bm, M_PLASTER, (xx, SHY - 0.05, z + 0.08), smooth=True)
            o.scale = (0.85, 0.95, 1.15)
        xx += R.uniform(0.15, 0.3)

# ====================================================================== lights
C.world("#020203", 1.0)
HEAD = Vector((-0.06, -0.18, PLINTH_H + 0.64))
CEN = Vector((0.0, 0.0, PLINTH_H + 0.42))
# No narrowed 'spread' on these: Cycles keeps the power when the spread shrinks, so the in-beam intensity jumps
# and on this glossy coat the rims mirrored as big saturated sheets. A narrow key strip keeps the black black
# (small, crisp highlights that follow the sculpt instead of a chrome-like wash).
C.area("key", (-1.5, -1.2, 2.55), tuple(CEN + Vector((0, -0.1, 0.12))), 170.0, C.kelvin(5200), 0.4, 1.1)
C.area("rim_cool", (1.15, 1.35, 2.05), tuple(CEN + Vector((0, 0, 0.15))), 80.0, "#9cc8ff", 0.25, 1.4)
C.area("rim_toxic", (-0.4, 1.75, 1.55), tuple(CEN + Vector((0, 0, 0.1))), 18.0, "#9dff5a", 0.2, 1.0)
C.area("fill", (0.6, -2.6, 1.3), tuple(CEN), 12.0, C.kelvin(6500), 2.0)
C.spot("back_pool", (0.3, 0.4, 4.0), (0.2, 2.6, 1.0), 160.0, C.kelvin(3800), 35, 0.9, 0.2)
C.spot("plinth_top", (0.4, -0.8, 3.4), (0, 0, 0.9), 35.0, C.kelvin(5000), 22, 0.6, 0.05)
C.haze("studio_haze", (0, 0.5, 2.0), (8, 6, 4), 0.003, "#c8ccd0", 0.4)

# ====================================================================== shots
SHOTS = [
    C.Shot("hero", dict(loc=(-0.95, -1.65, 1.25), target=(-0.04, -0.05, 1.48), lens=50, fstop=4.0, focus=tuple(HEAD)),
           "數位雕刻胸像：低角度仰望張開的大口，冷色與毒綠色輪廓光勾出黏稠的表面。", kind="hero"),
    C.Shot("card", dict(loc=(1.25, -1.85, 1.6), target=(0.0, 0.0, 1.32), lens=45),
           "三分之四視角：胸像立在石台上。", kind="card"),
    C.Shot("s1", dict(loc=(-1.3, -1.95, 1.65), target=(0.0, 0.0, 1.32), lens=45),
           "三分之四前視：肌肉走向、纏繞的觸手與張開的大口。"),
    C.Shot("s2", dict(loc=(1.6, 1.5, 1.6), target=(0.0, 0.0, 1.35), lens=45),
           "後側視角：背部的觸手與輪廓光。"),
    C.Shot("s3", dict(loc=(-0.3, -0.95, 1.66), target=(-0.07, -0.2, 1.62), lens=85, fstop=4.0,
                      focus=(-0.08, -0.25, 1.67)),
           "大口特寫：一顆顆雕出的牙齒與濕亮的表面。"),
    C.Shot("s4", dict(loc=(-0.45, -0.95, 1.4), target=(-0.02, -0.27, 1.3), lens=85, fstop=8.0, focus=(-0.04, -0.31, 1.31)),
           "胸口特寫：側光掠過雕刻的肌理與纏繞的觸手。", exposure=0.3),
]
CAPTIONS = {"clay": "白模：與三分之四前視同一鏡頭，只看雕刻的造型。",
            "wire": "線框：同一鏡頭，以減面副本顯示網格（原始高模約 171 萬面，直接顯示會密成一片）。"}
TURN = dict(loc=(0.0, -2.6, 1.7), target=(0.0, 0.0, 1.38), lens=50)


# ---------------------------------------------------------------- custom wire pass (decimated copy)
def wire_lowpoly():
    lows = []
    for o, mode, val in ((BODY, "COLLAPSE", 26000), (TEETH, "UNSUBDIV", 3), (BASE, None, None)):
        if mode is None:
            c = o.copy(); c.data = o.data.copy()
        else:
            md = o.modifiers.new("lw", "DECIMATE"); md.decimate_type = mode
            if mode == "COLLAPSE":
                o.data.calc_loop_triangles(); md.ratio = val / len(o.data.loop_triangles)
            else:
                md.iterations = val
            dg = bpy.context.evaluated_depsgraph_get()
            me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
            o.modifiers.remove(md)
            c = bpy.data.objects.new(o.name + "_low", me)
        C.link(c); c.parent = o.parent; c.matrix_world = o.matrix_world.copy()
        c.data.materials.clear(); c.data.materials.append(o.data.materials[0])
        C.tag(c, "model"); lows.append(c)
        C.log(f"wire copy {o.name}: {len(c.data.polygons)} faces")
        o.hide_render = True
    return lows


REF = next(s for s in SHOTS if s.name == "s1")
CLAY_EXPOSURE = -1.6      # the lights are set for a near-black material: light clay needs ~1.5 stops less


def render_clay():
    saved = C.clay_pass("#b4afa6", "#3a3b3d")
    C.render_shot(C.Shot("clay", REF.cam, kind="still", exposure=CLAY_EXPOSURE), args,
                  os.path.join(C.out_dir(args, "venom"), "clay.jpg"))
    C._restore(saved)


def render_wire():
    lows = wire_lowpoly()
    proxy = C.Model("venom", lows, model.pivot)
    st = C.wire_pass(proxy, thickness=0.00022, body_color="#14171b", wire_strength=1.6)
    C.render_shot(C.Shot("wire", REF.cam, kind="still", exposure=-0.6), args,
                  os.path.join(C.out_dir(args, "venom"), "wire.jpg"))
    C.end_wire(st)
    for c in lows:
        me = c.data; bpy.data.objects.remove(c, do_unlink=True); bpy.data.meshes.remove(me)
    for o in (BODY, TEETH, BASE):
        o.hide_render = False


want_clay, want_wire = C.wanted(args, "clay"), C.wanted(args, "wire")
all_names = [s.name for s in SHOTS] + ["clay", "wire"]
args.only = [n for n in (args.only or all_names) if n not in ("clay", "wire")] or ["-"]
C.run(args, "venom", model, SHOTS, clay_wire_of="s1", turn=TURN, turn_mode="model", captions_extra=CAPTIONS)
if want_clay:
    render_clay()
if want_wire:
    render_wire()
