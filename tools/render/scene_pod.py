"""Bio pod / stasis capsule (key 'pod', 生物倉.fbx) in a dim laboratory bay: a row of identical pods receding
into teal haze, grated service trench, hoses on the wet floor, status monitors, amber warning beacon.

  & $blender -b --factory-startup --python tools\\render\\scene_pod.py -- --quality draft [--only hero,s1] [--turn] [--out DIR]
"""
import sys, os, math, random, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402
import common as C  # noqa: E402
import modellib as ML  # noqa: E402

args = C.parse_args()
C.reset()
R = random.Random(11)

# ---------------------------------------------------------------- model
model = C.load("pod", size=2.4)
# the pod axis sits 8 cm off the bbox centre (the side box sticks out to -X): put the axis on the pivot
ML.transform(model.objs, Matrix.Translation((-0.08, 0.0, 0.0)))
PLINTH_H = 0.08
model.pivot.location = (0, 0, PLINTH_H)
GLASS_R, GLASS_Z0, GLASS_Z1 = 0.295, 0.78, 2.02      # measured (model space, after the shift)


# ---------------------------------------------------------------- scene-specific materials
def thin_glass(name, tint="#d8fff6", rough=0.03, dirt=0.35):
    """Single-surface glass (the pod's glass is one open cylinder): fresnel mix of a tinted transparent
    and a glossy reflection, with condensation streaks breaking up the roughness. No refraction."""
    m, nt, out = C.new_mat(name)
    v = C.coords(nt)
    streak = C.noise(nt, C.vmath(nt, "MULTIPLY", v, (14.0, 14.0, 1.2)), 1.0, 5, 0.6)
    spots = C.noise(nt, v, 22.0, 4, 0.6)
    dmask = C.mathn(nt, "MULTIPLY", C.maprange(nt, streak, 0.5, 0.75), dirt, clamp=True)
    r = C.mixf(nt, dmask, rough, 0.35)
    r = C.mixf(nt, C.maprange(nt, spots, 0.62, 0.7, 0, 0.6), r, 0.2)
    fres = C.N(nt, "LayerWeight", {"Blend": 0.12}).outputs["Fresnel"]
    fac = C.mathn(nt, "ADD", C.mathn(nt, "MULTIPLY", fres, 0.9), C.mathn(nt, "MULTIPLY", dmask, 0.12), clamp=True)
    tr = C.N(nt, "BsdfTransparent", {"Color": C.col(tint)})
    gl = C.N(nt, "BsdfGlossy", {"Roughness": r, "Color": C.col("#ffffff")})
    mx = C.N(nt, "MixShader")
    C._sock_set(mx.inputs[0], fac)
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    for k, val in (("surface_render_method", "BLENDED"), ("use_backface_culling", False)):
        try:
            setattr(m, k, val)
        except Exception:
            pass
    m["recipe"] = "glass"
    return m


def liquid(name, color="#1fffd2", tint="#3fd9c0", strength=0.35, see=0.92, vol=1.6, vol_emit=0.75):
    """Glowing suspension fluid: half transparent (bubbles show inside), emission brighter at the bottom,
    with slow caustic-like bands; thin glossy fresnel skin on top."""
    m, nt, out = C.new_mat(name)
    v = C.coords(nt)
    z = C.N(nt, "SeparateXYZ", {"Vector": v}).outputs[2]
    grad = C.maprange(nt, z, GLASS_Z0 + 0.1, GLASS_Z1 - 0.15, 1.35, 0.55)
    w = C.N(nt, "TexWave", {"Vector": v, "Scale": 2.2, "Distortion": 7.0, "Detail": 3.0}, wave_type="BANDS",
            bands_direction="Z").outputs["Factor"]
    k = C.mathn(nt, "MULTIPLY", grad, C.maprange(nt, w, 0.0, 1.0, 0.75, 1.15))
    em = C.N(nt, "Emission", {"Color": C.col(color)})
    C._sock_set(em.inputs["Strength"], C.mathn(nt, "MULTIPLY", k, strength))
    tr = C.N(nt, "BsdfTransparent", {"Color": C.col(tint)})
    mx = C.N(nt, "MixShader", {"Fac": 1.0 - see})
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
    gl = C.N(nt, "BsdfGlossy", {"Roughness": 0.05})
    mx2 = C.N(nt, "MixShader")
    C._sock_set(mx2.inputs[0], C.mathn(nt, "MULTIPLY", C.N(nt, "LayerWeight", {"Blend": 0.1}).outputs["Fresnel"], 0.5))
    nt.links.new(mx.outputs[0], mx2.inputs[1]); nt.links.new(gl.outputs[0], mx2.inputs[2])
    nt.links.new(mx2.outputs[0], out.inputs["Surface"])
    if vol:
        # homogeneous glowing volume inside (cheap: constant density) -> real depth, bubbles fade with distance
        pv = C.N(nt, "VolumePrincipled", {"Color": C.col("#0e3a34"), "Density": vol, "Absorption Color": C.col("#5fe8d0"),
                                          "Emission Color": C.col(color), "Emission Strength": vol_emit,
                                          "Anisotropy": 0.3})
        nt.links.new(pv.outputs[0], out.inputs["Volume"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    m["recipe"] = "emissive"     # clay/wire passes leave it alone
    return m


def grating(name, pitch=0.045, bar=0.22, color="#3c4245"):
    """Floor grating: metal bars with real holes (transparent), world space."""
    m, nt, out = C.new_mat(name)
    v = C.coords(nt, "world")
    sep = C.N(nt, "SeparateXYZ", {"Vector": v})
    fx = C.mathn(nt, "FRACT", C.mathn(nt, "DIVIDE", sep.outputs[0], pitch))
    fy = C.mathn(nt, "FRACT", C.mathn(nt, "DIVIDE", sep.outputs[1], pitch * 3.0))
    bx = C.mathn(nt, "LESS_THAN", fx, bar)
    by = C.mathn(nt, "LESS_THAN", fy, bar / 3.0)
    solid = C.mathn(nt, "MAXIMUM", bx, by)
    n = C.noise(nt, v, 6.0, 4, 0.6)
    shade = C.mix(nt, C.maprange(nt, n, 0.4, 0.7, 0, 0.6), C.col(color), "#1b1714")
    b = C.N(nt, "BsdfPrincipled", {"Metallic": 0.85})
    C._sock_set(b.inputs["Base Color"], shade)
    C._sock_set(b.inputs["Roughness"], C.maprange(nt, n, 0.3, 0.7, 0.3, 0.6))
    tr = C.N(nt, "BsdfTransparent")
    mx = C.N(nt, "MixShader")
    C._sock_set(mx.inputs[0], solid)
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(b.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    try:
        m.surface_render_method = "DITHERED"
    except Exception:
        pass
    return m


def ui_screen(name, color="#38ffd8", accent="#ffb02e", strength=2.5, seed=0.0):
    """Status-monitor UI on a plane (Generated coords 0..1): grid, waveform trace, bar meters, scanlines."""
    m, nt, out = C.new_mat(name)
    g = C.N(nt, "TexCoord").outputs["Generated"]
    sep = C.N(nt, "SeparateXYZ", {"Vector": g})
    x, y = sep.outputs[0], sep.outputs[1]
    gx = C.mathn(nt, "LESS_THAN", C.mathn(nt, "FRACT", C.mathn(nt, "MULTIPLY", x, 12.0)), 0.06)
    gy = C.mathn(nt, "LESS_THAN", C.mathn(nt, "FRACT", C.mathn(nt, "MULTIPLY", y, 8.0)), 0.08)
    grid = C.mathn(nt, "MULTIPLY", C.mathn(nt, "MAXIMUM", gx, gy), 0.18)
    # waveform in the upper half
    wv = C.mathn(nt, "ADD", C.mathn(nt, "MULTIPLY", C.mathn(nt, "SINE", C.mathn(nt, "ADD", C.mathn(nt, "MULTIPLY", x, 31.0), seed)), 0.06),
                 C.mathn(nt, "MULTIPLY", C.mathn(nt, "SINE", C.mathn(nt, "MULTIPLY", x, 83.0)), 0.025))
    wv = C.mathn(nt, "ADD", wv, 0.72)
    trace = C.maprange(nt, C.mathn(nt, "ABSOLUTE", C.mathn(nt, "SUBTRACT", y, wv)), 0.018, 0.006)
    # bar meters in the lower half
    col_id = C.mathn(nt, "FLOOR", C.mathn(nt, "MULTIPLY", x, 14.0))
    hgt = C.N(nt, "TexWhiteNoise", noise_dimensions="3D")
    C._sock_set(hgt.inputs["Vector"], C.N(nt, "CombineXYZ", {"X": col_id, "Y": seed}).outputs[0])
    barh = C.maprange(nt, hgt.outputs["Value"], 0, 1, 0.08, 0.42)
    inbar = C.mathn(nt, "MULTIPLY", C.mathn(nt, "LESS_THAN", y, barh),
                    C.mathn(nt, "LESS_THAN", C.mathn(nt, "FRACT", C.mathn(nt, "MULTIPLY", x, 14.0)), 0.7))
    inbar = C.mathn(nt, "MULTIPLY", inbar, C.mathn(nt, "GREATER_THAN", y, 0.06))
    scan = C.maprange(nt, C.mathn(nt, "FRACT", C.mathn(nt, "MULTIPLY", y, 90.0)), 0, 1, 0.7, 1.0)
    c = C.mix(nt, C.mathn(nt, "MAXIMUM", grid, trace), C.col("#02100e"), C.col(color))
    hi = C.mathn(nt, "GREATER_THAN", barh, 0.36)
    barcol = C.mix(nt, hi, C.col(color), C.col(accent))
    c = C.mix(nt, C.mathn(nt, "MULTIPLY", inbar, 0.85), c, barcol)
    # plain emission (a glossy layer here rendered blown-out white in the EEVEE turntable)
    em = C.N(nt, "Emission")
    C._sock_set(em.inputs["Color"], c)
    C._sock_set(em.inputs["Strength"], C.mathn(nt, "MULTIPLY", scan, strength))
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    m["recipe"] = "screen"
    return m


# ---------------------------------------------------------------- model looks
LOOKS = {
    "pod_metal": ("painted", dict(color="#a9b3ae", rough=0.4, metal=0.25, grime=0.8, wear=0.6, panels=(0.55, 0.55, 0.3),
                                  seam_width=0.003, grime_color="#2a2620", under="#9aa1a6", scale=0.35, streaks=0.8)),
    "pod_base": ("painted", dict(color="#2b3236", rough=0.45, metal=0.5, grime=0.6, wear=0.7, panels=(0.3, 0.3, 0.2),
                                 seam_width=0.004, grime_color="#100e0b", under="#a0a6aa", scale=0.35)),
    "copper": ("metal", dict(color="#c47a48", rough=0.28, grime=0.55, scale=0.3)),
    "emit_red": ("emissive", dict(color="#ff2b1f", strength=14.0, base="#2a0605")),
    "pod_glass": thin_glass("pod_glass_thin"),
}
C.apply_looks(model.objs, LOOKS)

M_LIQ = liquid("pod_liquid")
M_BUBBLE = C.material("emissive", "bubble", color="#d6fff6", strength=3.0, base="#ffffff")


def pod_insides(parent, seed=0, n_bub=70):
    """Liquid column + rising bubbles inside the glass (parented so they spin with the pod)."""
    objs = []
    lq = C.cylinder("liquid", GLASS_R - 0.018, 0.96, (0, 0, PLINTH_H + 0.88 + 0.48), mat=M_LIQ, segments=48)
    objs.append(lq)
    rr = random.Random(seed)
    bm = bmesh.new()
    def bub(x, y, z, s):
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=s, matrix=Matrix.Translation((x, y, PLINTH_H + z)))
    # rising streams from a few vents in the base, bubbles growing and drifting as they rise
    for k in range(max(2, n_bub // 12)):
        a = rr.uniform(0, 2 * math.pi); rad = (GLASS_R - 0.06) * math.sqrt(rr.uniform(0.05, 1))
        x0, y0 = math.cos(a) * rad, math.sin(a) * rad
        z = 0.93
        while z < 1.82:
            t = (z - 0.93) / 0.9
            bub(x0 + 0.012 * math.sin(z * 37 + k), y0 + 0.012 * math.cos(z * 29 + k), z, 0.0025 + 0.005 * t * rr.uniform(0.6, 1.2))
            z += rr.uniform(0.025, 0.07) * (1 + t)
    for i in range(n_bub // 3):   # a few loose ones
        a = rr.uniform(0, 2 * math.pi); rad = (GLASS_R - 0.05) * math.sqrt(rr.uniform(0.02, 1))
        bub(math.cos(a) * rad, math.sin(a) * rad, rr.uniform(0.95, 1.8), rr.uniform(0.002, 0.006))
    objs.append(C._obj_from_bm("bubbles", bm, M_BUBBLE, role="keep"))
    for o in objs:
        o.visible_shadow = False
        o.parent = parent
        o.matrix_parent_inverse = parent.matrix_world.inverted()
    return objs


INSIDE = pod_insides(model.pivot)
for o in INSIDE:
    C.tag(o, "keep" if o.name.startswith("bubbles") else "set")
# the fluid glow, as a light: lights the cap underside, base rim and floor around the hero
GLOW = C.point("pod_glow", (0, 0, PLINTH_H + 1.35), 45, "#2fffd8", 0.2)
GLOW.data.shadow_soft_size = 0.22
GLOW.parent = model.pivot; GLOW.matrix_parent_inverse = model.pivot.matrix_world.inverted()

# ---------------------------------------------------------------- duplicate pods (set dressing)
M_LAMP_AMBER = C.material("emissive", "pod_amber_lamp", color="#ff9a1f", strength=14.0, base="#2a1503")
M_LAMP_GREEN = C.material("emissive", "pod_green_lamp", color="#3dff8a", strength=10.0, base="#062a12")
M_LIQ_DIM = liquid("pod_liquid_dim", strength=0.35, vol=4.0, vol_emit=0.6)
M_LIQ_OFF = liquid("pod_liquid_off", color="#0d5a52", strength=0.15, vol=6.0, vol_emit=0.15)


def dup_pod(name, loc, rotz=0.0, lamp=None, liq=None):
    piv = bpy.data.objects.new(name + "_pivot", None); C.link(piv)
    piv.location = (loc[0], loc[1], PLINTH_H); piv.rotation_euler.z = math.radians(rotz)
    for o in model.objs:
        c = o.copy(); C.link(c); c.parent = piv; c.matrix_parent_inverse = Matrix.Identity(4)
        c.matrix_basis = Matrix.Identity(4)
        # own mesh data: the clay/wire passes swap + restore materials per mesh, shared meshes would not restore
        c.data = o.data.copy()
        C.tag(c, "set")
        if lamp is not None and C.palette_of(o.material_slots[0].material) == "emit_red":
            c.data.materials.clear(); c.data.materials.append(lamp)
    for o in pod_insides(piv, seed=zlib.crc32(name.encode()) % 1000, n_bub=25):
        C.tag(o, "keep" if o.name.startswith("bubbles") else "set")
        if liq is not None and o.name.startswith("liquid"):
            o.data.materials.clear(); o.data.materials.append(liq)
    return piv


ROW_X = [-2.3 * k for k in range(1, 6)] + [2.3, 4.6]
LAMPS = [M_LAMP_GREEN, M_LAMP_GREEN, None, M_LAMP_AMBER, M_LAMP_GREEN, M_LAMP_GREEN, M_LAMP_AMBER]
LIQS = [None, None, M_LIQ_DIM, M_LIQ_OFF, M_LIQ_DIM, None, M_LIQ_OFF]
for k, x in enumerate(ROW_X):
    dup_pod(f"pod_{k}", (x, 0.0), 0.0, LAMPS[k], LIQS[k])
# opposite row across the aisle (seen in the rear shot)
ROW_B = (-5.75, -3.45, -1.15, 1.15, 3.45)
for k, x in enumerate(ROW_B):
    dup_pod(f"podB_{k}", (x, -5.2), 180.0, M_LAMP_GREEN if k % 2 else M_LAMP_AMBER, M_LIQ_DIM if k % 2 else None)

# ---------------------------------------------------------------- set: lab bay
BACK, FRONT, H, XL, XR = 2.7, -7.0, 4.2, -14.0, 8.5
TR_Y0, TR_Y1, TR_D = -1.55, -0.85, 0.32           # service trench in front of the row

M_FLOOR = C.material("concrete", "pod_floor", color="#3d4446", wet=0.9, rough=0.5, joints=1.8, scale=0.5)
M_WALL = C.material("painted", "pod_wall", color="#222b2d", rough=0.55, grime=0.75, wear=0.35, panels=(1.2, 1000, 1.0),
                    seam_width=0.012, space="world", streaks=1.0, grime_color="#121410")
M_DARK = C.material("painted", "pod_darksteel", color="#22282b", metal=0.5, rough=0.45, grime=0.6, wear=0.6, panels=None,
                    space="world", under="#8c9396")
M_PLINTH = C.material("painted", "pod_plinth", color="#3a4246", metal=0.6, rough=0.4, grime=0.5, wear=0.8, panels=None,
                      space="world", under="#b0b6ba", scale=0.4)
M_YEL = C.material("painted", "pod_yellow", color="#c99a1e", rough=0.45, grime=0.6, wear=0.7, panels=None, space="world",
                   scale=0.4)
M_HOSE = C.material("rubber", "pod_hose", color="#16191b", rough=0.5, space="world")
M_HOSE_TEAL = C.material("rubber", "pod_hose_teal", color="#174a48", rough=0.45, space="world")
M_PIPE = C.material("metal", "pod_pipe", color="#8b9297", rough=0.32, brushed=0.4, grime=0.5, space="world")
M_CU = C.material("metal", "pod_cu", color="#b8703f", rough=0.33, grime=0.6, space="world")
M_GRATE = grating("pod_grate")
M_GLOW_TEAL = C.material("emissive", "pod_glow_teal", color="#2fffe0", strength=6.0)
M_RING = C.material("emissive", "pod_ring", color="#36ffe0", strength=5.0)
M_STRIP = C.material("emissive", "pod_strip", color="#cdeef0", strength=7.0)
M_BEACON = C.material("emissive", "pod_beacon", color="#ff8a1c", strength=40.0, base="#401800")
M_SIGN = C.material("flat", "pod_sign", color="#cfd6d2", rough=0.7)
M_SIGN_GLOW = C.material("emissive", "pod_sign_glow", color="#7ffff0", strength=3.0)
M_PAINT_Y = C.material("floor_paint", "pod_paint_y", color="#d9a21b", wet=0.9, wear=0.6)
M_PAINT_W = C.material("floor_paint", "pod_paint_w", color="#c8d2d0", wet=0.9, wear=0.6)

# floor in two pieces around the trench
C.plane("floor_back", (XR - XL, BACK - TR_Y1), ((XL + XR) / 2, (BACK + TR_Y1) / 2, 0), mat=M_FLOOR)
C.plane("floor_front", (XR - XL, TR_Y0 - FRONT), ((XL + XR) / 2, (TR_Y0 + FRONT) / 2, 0), mat=M_FLOOR)
# trench: walls, bottom, pipes, glow strip, grating on top
C.box("trench_bot", (XR - XL, TR_Y1 - TR_Y0, 0.04), ((XL + XR) / 2, (TR_Y0 + TR_Y1) / 2, -TR_D), mat=M_DARK, bevel=0)
for y in (TR_Y0, TR_Y1):
    C.box(f"trench_wall_{y}", (XR - XL, 0.04, TR_D), ((XL + XR) / 2, y, -TR_D / 2), mat=M_DARK, bevel=0)
for k, (yy, r, m) in enumerate(((-1.42, 0.05, M_CU), (-1.28, 0.035, M_PIPE), (-1.0, 0.06, M_HOSE_TEAL), (-1.15, 0.03, M_PIPE))):
    C.pipe(f"trench_pipe_{k}", (XL, yy, -TR_D + 0.04 + r), (XR, yy, -TR_D + 0.04 + r), r, m)
C.strip("trench_glow", (XL, -0.9, -TR_D + 0.06), (XR, -0.9, -TR_D + 0.06), 0.03, "#2fffe0", 10.0, role="keep")
C.plane("grate", (XR - XL, TR_Y1 - TR_Y0), ((XL + XR) / 2, (TR_Y0 + TR_Y1) / 2, -0.004), mat=M_GRATE)
for y in (TR_Y0, TR_Y1):   # angle-iron edges
    C.box(f"grate_edge_{y}", (XR - XL, 0.05, 0.02), ((XL + XR) / 2, y, -0.005), mat=M_PLINTH, bevel=0.004)
# yellow safety line along the trench + bay numbers on the floor
C.plane("mark_line", (XR - XL, 0.08), ((XL + XR) / 2, TR_Y0 - 0.12, 0.002), mat=M_PAINT_Y)
C.plane("mark_line2", (XR - XL, 0.08), ((XL + XR) / 2, TR_Y1 + 0.12, 0.002), mat=M_PAINT_Y)
for k, x in enumerate([0.0] + ROW_X):
    num = f"B-{4 + round(-x / 2.3):02d}"
    C.text(f"floor_num_{k}", num, 0.2, (x, -2.0, 0.003), (0, 0, 0), M_PAINT_W, C.FONT_STENCIL, spacing=1.1)

# room shell
C.box("wall_back", (XR - XL, 0.3, H), ((XL + XR) / 2, BACK + 0.15, 0), mat=M_WALL, origin="bottom", bevel=0)
C.box("wall_front", (XR - XL, 0.3, H), ((XL + XR) / 2, FRONT - 0.15, 0), mat=M_WALL, origin="bottom", bevel=0)
C.box("wall_R", (0.3, BACK - FRONT, H), (XR + 0.15, (BACK + FRONT) / 2, 0), mat=M_WALL, origin="bottom", bevel=0)
C.box("wall_L", (0.3, BACK - FRONT, H), (XL - 0.15, (BACK + FRONT) / 2, 0), mat=M_WALL, origin="bottom", bevel=0)
C.box("ceiling", (XR - XL, BACK - FRONT, 0.2), ((XL + XR) / 2, (BACK + FRONT) / 2, H), mat=M_DARK, origin="bottom",
      bevel=0)

# pod plinths (round steel pads with a glowing ring), hero plinth included (rotationally symmetric)
for x, y in [(0.0, 0.0)] + [(x, 0.0) for x in ROW_X] + [(x, -5.2) for x in ROW_B]:
    C.cylinder(f"plinth_{x}_{y}", 0.62, PLINTH_H, (x, y, 0), mat=M_PLINTH, segments=48, origin="bottom")
    C.cylinder(f"plinth_glow_{x}_{y}", 0.635, 0.012, (x, y, PLINTH_H * 0.5), mat=M_RING, segments=48, role="keep")

# back wall: horizontal pipe runs, cable trays, control cabinets, monitors, signage, beacon
for k, (z, r, m) in enumerate(((3.35, 0.09, M_PIPE), (3.6, 0.06, M_CU), (3.8, 0.11, M_PIPE), (0.35, 0.07, M_PIPE))):
    C.pipe(f"wall_pipe_{k}", (XL, BACK - 0.25 - r, z), (XR, BACK - 0.25 - r, z), r, m)
    for x in range(int(XL) + 1, int(XR), 2):
        C.box(f"pipe_clamp_{k}_{x}", (0.05, 0.3, r * 2 + 0.05), (x + 0.3, BACK - 0.15 - r, z), mat=M_DARK, bevel=0.005)
C.box("cable_tray", (XR - XL, 0.35, 0.08), ((XL + XR) / 2, BACK - 0.35, 3.05), mat=M_DARK, bevel=0.01)
for i in range(5):
    C.pipe(f"tray_cable_{i}", (XL, BACK - 0.48 + i * 0.065, 3.12), (XR, BACK - 0.48 + i * 0.065, 3.12), 0.025,
           M_HOSE if i % 2 else M_HOSE_TEAL)

M_SCREENS = [ui_screen(f"pod_ui_{i}", seed=float(i) * 1.7,
                       color=("#38ffd8", "#3aa8ff", "#38ffd8")[i % 3]) for i in range(4)]


def monitor(name, loc, size=(0.42, 0.3), rotz=0.0, scr=0, arm=None):
    """Steel monitor housing with a UI screen inset; optional ceiling arm."""
    w, h = size
    r = math.radians(rotz)
    nrm = Vector((math.sin(r), -math.cos(r), 0))
    C.box(name, (w + 0.05, 0.09, h + 0.05), loc, (0, 0, rotz), mat=M_DARK, bevel=0.012)
    p = Vector(loc) + nrm * 0.047
    C.plane(name + "_scr", (w, h), tuple(p), (90, 0, rotz), mat=M_SCREENS[(scr % 2) * 2], role="keep")
    if arm:
        C.pipe(name + "_arm", (loc[0], loc[1], loc[2] + h / 2), (loc[0], loc[1], arm), 0.02, M_DARK)


for k, x in enumerate([0.0] + ROW_X):
    xx = x + 1.15
    if xx > XR - 0.5:
        continue
    # control cabinet against the back wall between pods, with a monitor and status lamps
    C.box(f"cab_{k}", (0.7, 0.45, 1.5), (xx, BACK - 0.25, 0), mat=M_PLINTH, origin="bottom", bevel=0.02)
    monitor(f"mon_{k}", (xx, BACK - 0.52, 1.85), (0.5, 0.32), 0.0, k)
    for j in range(3):
        lm = (M_GLOW_TEAL, M_LAMP_GREEN, M_LAMP_AMBER)[(j + k) % 3]
        C.cylinder(f"cab_led_{k}_{j}", 0.018, 0.01, (xx - 0.2 + j * 0.06, BACK - 0.48, 1.3), (90, 0, 0), lm, 12, "keep")
    C.text(f"cab_lbl_{k}", f"POD {4 + round(-x / 2.3):02d}", 0.06, (xx + 0.12, BACK - 0.476, 1.3), (90, 0, 0), M_SIGN,
           C.FONT_STENCIL)
    # thick hose from the pod's side box down to the floor and back into the cabinet
    hose = C.cable(f"pod_hose_{k}", [(x - 0.5, 0.25, PLINTH_H + 0.45), (x - 0.62, 0.45, 0.07), (x - 0.4, 1.1, 0.06),
                                     (xx - 0.2, 1.6, 0.06), (xx - 0.15, BACK - 0.45, 0.3)], 0.045,
                   M_HOSE if k % 2 else M_HOSE_TEAL)
    hose2 = C.cable(f"pod_hose2_{k}", [(x + 0.1, 0.35, PLINTH_H + 0.2), (x + 0.15, 0.7, 0.05), (xx + 0.15, 1.5, 0.05),
                                       (xx + 0.2, BACK - 0.45, 0.5)], 0.03, M_HOSE)
    # overhead umbilical from the cap to the ceiling tray
    up = C.cable(f"pod_umb_{k}", [(x - 0.05, 0.1, PLINTH_H + 2.36), (x - 0.1, 0.25, 2.95), (x - 0.2, 0.9, 3.6),
                                  (x - 0.25, BACK - 0.5, 3.15)], 0.035, M_HOSE)
    if x == 0.0:
        for o in (hose, hose2, up):
            o["hide_turn"] = True

# floor cable bundle running along the row behind the pods
for i in range(3):
    pts = [(x, 1.25 + i * 0.09 + 0.04 * math.sin(x * 1.3 + i), 0.04 + 0.005 * i) for x in
           [XL + 0.5 + j * 1.5 for j in range(int((XR - XL) / 1.5))]]
    C.cable(f"floor_bundle_{i}", pts, 0.04, M_HOSE if i != 1 else M_HOSE_TEAL)

# hanging monitor right of the hero (seen in hero / card)
monitor("mon_hang", (1.05, 0.55, 1.75), (0.36, 0.24), -28.0, 1, arm=H)

# signage
C.text("sign_bay", "BIO-STORAGE  BAY B", 0.22, (-3.0, BACK - 0.02, 2.55), (90, 0, 0), M_SIGN, C.FONT_STENCIL,
       spacing=1.15)
C.text("sign_tc", "生物倉 B 區", 0.26, (3.8, BACK - 0.02, 2.55), (90, 0, 0), M_SIGN_GLOW, C.FONT_TC)
C.text("sign_warn", "警告 低溫維生中 請勿開啟", 0.12, (-7.0, BACK - 0.02, 2.55), (90, 0, 0), M_YEL, C.FONT_TC)
C.box("haz_band", (XR - XL, 0.02, 0.12), ((XL + XR) / 2, BACK - 0.01, 2.3), mat=M_YEL, bevel=0)

# amber warning beacons (the warm accent)
for k, (x, pw) in enumerate(((1.6, 90.0), (-8.05, 70.0))):
    C.cylinder(f"beacon_base_{k}", 0.08, 0.06, (x, BACK - 0.08, 2.45), (90, 0, 0), M_DARK, 24)
    C.cylinder(f"beacon_{k}", 0.06, 0.12, (x, BACK - 0.16, 2.45), (90, 0, 0), M_BEACON, 24, "keep")
    C.spot(f"beacon_spot_{k}", (x, BACK - 0.3, 2.45), (x - 0.8, 0.0, 1.0), pw * 8, "#ff8a2a", 70, 0.6, 0.06)
    C.point(f"beacon_pt_{k}", (x, BACK - 0.3, 2.45), pw, "#ff8a2a", 0.05)

# ceiling: light strips + per-pod downlights (cones read in the haze)
for k, y in enumerate((-0.3, -3.0)):
    C.strip(f"ceil_strip_{k}", (XL + 0.5, y, H - 0.05), (XR - 0.5, y, H - 0.05), 0.08, "#cdeef0", 2.5)
for x in [0.0] + ROW_X:
    C.cylinder(f"downlight_{x}", 0.16, 0.12, (x, -0.1, H - 0.06), mat=M_DARK, segments=24)
    C.cylinder(f"downlight_lens_{x}", 0.12, 0.01, (x, -0.1, H - 0.125), mat=M_STRIP, segments=24, role="keep")
    C.spot(f"downlight_spot_{x}", (x, -0.1, H - 0.14), (x, 0.0, 0.0), 900 if x == 0.0 else 380, C.kelvin(7500), 34, 0.5,
           0.06)

# ---------------------------------------------------------------- lighting & atmosphere
C.world("#020506", 1.0)
C.area("key", (-2.0, -2.8, 2.4), (0, 0, 1.1), 420, "#d6f2f2", 1.2)            # cold key, front-left
C.area("fill", (2.2, -2.4, 0.5), (0, 0, 0.8), 60, "#7fd8d0", 1.0)             # dim teal fill (lifts the base)
# warm caged work lamp on the cabinet right of the hero (the warm practical seen in the hero shot)
C.box("worklamp_cage", (0.14, 0.1, 0.2), (1.55, BACK - 0.55, 1.62), mat=M_DARK, bevel=0.01)
C.cylinder("worklamp_bulb", 0.045, 0.12, (1.55, BACK - 0.61, 1.62), (90, 0, 0), C.material("emissive", "pod_bulb_warm",
           color=C.kelvin(2600), strength=30.0), 16, "keep")
C.point("worklamp", (1.55, BACK - 0.7, 1.62), 40, C.kelvin(3000), 0.04)
C.area("rim", (1.2, 2.1, 3.0), (0, 0, 1.4), 220, "#9ff0e8", 1.0)              # teal rim from behind
C.area("rim_warm", (2.0, 1.9, 1.3), (0, 0, 1.2), 200, "#ffa050", 0.6)          # warm kicker (beacon side)
C.haze("haze", ((XL + XR) / 2, (BACK + FRONT) / 2, H / 2), (XR - XL - 0.1, BACK - FRONT - 0.1, H - 0.02), 0.018,
       "#a8e6de", 0.35)

# small / decorative emitters: visible only, not sampled as lights (cheaper, less noise)
for nm in ("bubble", "pod_ring", "pod_green_lamp", "pod_amber_lamp", "pod_sign_glow", "pod_liquid_dim", "pod_liquid_off",
           "pod_glow_teal", "pod_strip", "look_emit_red") + tuple(f"pod_ui_{i}" for i in range(4)):
    m = bpy.data.materials.get(nm)
    if m is not None:
        try:
            m.cycles.emission_sampling = "NONE"
        except Exception as e:
            C.log("emission_sampling", e)

# ---------------------------------------------------------------- shots
SHOTS = [
    C.Shot("hero", dict(loc=(2.55, -3.55, 0.8), target=(-0.9, 0.25, 1.4), lens=26, fstop=2.8, focus=(0.0, -0.3, 1.3)),
           "低角度看生物倉：一整排相同的艙體沒入青綠色的霧裡，艙內液體發光，琥珀色警示燈在後牆閃著。", kind="hero"),
    C.Shot("card", dict(loc=(2.75, -4.3, 1.85), target=(0.0, 0.0, 1.2), lens=40),
           "三分之四前側視角，生物倉立在實驗室的圓形底座上。", kind="card"),
    C.Shot("s1", dict(loc=(-2.3, -4.9, 1.65), target=(0.1, 0.0, 1.28), lens=32),
           "三分之四前視：頂蓋、玻璃艙身與底座的比例，背景是同排的其他艙體。"),
    C.Shot("s2", dict(loc=(-2.35, 2.3, 1.45), target=(0.0, -0.1, 1.25), lens=21),
           "後側視角：側邊機箱與沿玻璃上行的銅管，背景是走道對面的另一排艙體。"),
    C.Shot("s3", dict(loc=(0.8, -1.55, 2.45), target=(0.0, -0.1, 2.1), lens=55, fstop=2.0, focus=(0.05, -0.33, 2.12)),
           "頂蓋特寫：紅色狀態燈、銅環與面板接縫的磨損。"),
    C.Shot("s4", dict(loc=(-1.0, -0.95, 0.62), target=(-0.15, 0.05, 0.98), lens=40, fstop=2.4, focus=(-0.3, -0.2, 0.85)),
           "底座與側邊機箱特寫：接進艙體的粗管線、銅管，以及玻璃裡上升的氣泡。"),
]
CAPTIONS = {"clay": "白模：與三分之四前視同一鏡頭，只看造型與比例。",
            "wire": "線框：同一鏡頭顯示模型的實際四邊形佈線。"}
TURN = dict(loc=(0.0, -4.9, 1.5), target=(0.0, 0.0, 1.2), lens=32)

C.run(args, "pod", model, SHOTS, clay_wire_of="s1", turn=TURN, turn_mode="model", captions_extra=CAPTIONS)
