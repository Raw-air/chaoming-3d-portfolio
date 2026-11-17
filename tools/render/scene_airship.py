"""Hot-air-balloon sky ship (key 'airship', 飛船.fbx) moored at a sky fishing port above a sea of clouds.

  & $blender -b --factory-startup --python tools\\render\\scene_airship.py -- --quality draft [--only hero,s1] [--turn] [--out DIR]

Model: 255 parts, 334k tris; size=40 m (balloon 40 m long, hull ~22 m, deck at z~10.2). Bow = +Y, tail fins = -Y.
Set: wooden pier (finger pier + boardwalk on stilts that drop into the clouds), rope rails, lanterns, crates,
barrels, a shack and a cargo derrick; displaced opaque cloud sea + cumulus towers (no volumetric clouds),
thin homogeneous haze for aerial perspective, gradient sky world with a sun glow, low warm sun.
Everything that is part of the pier is hidden for the turntable (the ship spins in open sky).
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh  # noqa: E402
from mathutils import Vector, Matrix, noise as mnoise  # noqa: E402
import common as C  # noqa: E402
import modellib as ML  # noqa: E402

args = C.parse_args()
C.reset()

SUN_DIR = Vector((0.8, -0.47, -0.42)).normalized()      # direction the sunlight travels (sun low in the -X/+Y sky)

# ====================================================================== scene-specific materials
def attr_rnd(nt):
    """Per-piece random value stored as face attribute 'rnd' on generated set meshes (0 if missing)."""
    return C.N(nt, "Attribute", attribute_name="rnd", attribute_type="GEOMETRY").outputs["Fac"]


def wwood(name, color="#7b5a3e", color2="#4a3323", axis="X", space="world", grey=0.35, rough=0.72, rnd=True,
          scale=1.0, wear=0.5, grain=5.0, contrast=1.0):
    """Weathered wood: grain, per-plank tint (face attribute), silvered/grey weathering, cavity grime, pale worn edges."""
    m, nt, out = C.new_mat(name)
    v = C.coords(nt, space, 1.0 / scale)
    st = {"X": (0.12, 1, 1), "Y": (1, 0.12, 1), "Z": (1, 1, 0.12)}[axis]
    vv = C.vmath(nt, "MULTIPLY", v, st)
    w = C.N(nt, "TexWave", {"Vector": vv, "Scale": grain, "Distortion": 4.0, "Detail": 4.0, "Detail Scale": 2.0},
            wave_type="RINGS", rings_direction="SPHERICAL").outputs["Factor"]
    n = C.noise(nt, vv, 30.0, 6, 0.62)
    g = C.mathn(nt, "MULTIPLY", w, C.maprange(nt, n, 0.2, 0.8, 0.6, 1.25), clamp=True)
    shade = C.mix(nt, C.mathn(nt, "MULTIPLY", g, contrast), C.col(color), C.col(color2))
    if rnd:
        r = attr_rnd(nt)
        tv = C.maprange(nt, r, 0, 1, 0.72, 1.18)
        shade = C.mix(nt, 1.0, shade, C.N(nt, "CombineXYZ", {"X": tv, "Y": tv, "Z": tv}).outputs[0], blend="MULTIPLY")
        gr = C.mathn(nt, "MULTIPLY", C.maprange(nt, r, 0.55, 1.0), grey)
    else:
        gr = 0.0
    nb = C.noise(nt, v, 0.7, 5, 0.6)
    gtot = C.mathn(nt, "ADD", gr, C.mathn(nt, "MULTIPLY", C.maprange(nt, nb, 0.45, 0.75), grey), clamp=True)
    shade = C.mix(nt, gtot, shade, "#8d8579")
    cav = C.mathn(nt, "MULTIPLY", C.cavity_mask(nt, 0.12 * scale), 1.2, clamp=True)
    shade = C.mix(nt, cav, shade, "#1a130d")
    e = C.mathn(nt, "MULTIPLY", C.edge_mask(nt, 0.008 * scale), C.maprange(nt, n, 0.35, 0.6, 0.0, wear), clamp=True)
    shade = C.mix(nt, e, shade, "#b5a58c")
    rr = C.maprange(nt, g, 0, 1, rough - 0.1, rough + 0.12)
    crack = C.N(nt, "TexVoronoi", {"Vector": vv, "Scale": 9.0}, feature="DISTANCE_TO_EDGE").outputs["Distance"]
    ck = C.maprange(nt, crack, 0.0, 0.03, -0.6, 0.0)
    h = C.mathn(nt, "ADD", C.mathn(nt, "MULTIPLY", g, 0.25), ck)
    C.principled(nt, out, color=shade, rough=rr, normal=C.bump(nt, h, 0.35, 0.004 * scale), spec=0.4)
    return m


def rope_mat(name, color="#8a6a45", space="object"):
    m, nt, out = C.new_mat(name)
    v = C.coords(nt, space)
    w = C.N(nt, "TexWave", {"Vector": v, "Scale": 55.0, "Distortion": 1.5, "Detail": 2.0},
            wave_type="BANDS", bands_direction="DIAGONAL", wave_profile="SAW").outputs["Factor"]
    n = C.noise(nt, v, 80.0, 4, 0.6)
    nb = C.noise(nt, v, 1.5, 4, 0.6)
    shade = C.mix(nt, C.maprange(nt, nb, 0.3, 0.75, 0.0, 0.6), C.col(color), "#4a3a28")
    shade = C.mix(nt, C.maprange(nt, w, 0.0, 0.5, 0.35, 0.0), shade, "#2a1f14")
    C.principled(nt, out, color=shade, rough=C.maprange(nt, n, 0.3, 0.7, 0.8, 0.95), sheen=0.6, sheen_rough=0.5,
                 spec=0.3, normal=C.bump(nt, C.mathn(nt, "ADD", w, C.mathn(nt, "MULTIPLY", n, 0.4)), 0.6, 0.004))
    return m


def canvas_mat(name, color="#d8ccb0", stain="#8f7a58", seams=18, ring=4.4, center=(0.4, 24.7), patchy=0.1,
               transl=0.18):
    """Balloon canvas: longitudinal gore seams (angle around the Y axis) + circumferential panel seams,
    per-panel tint, tea stains / soot towards the bottom, weave bump, sheen, a little translucency."""
    m, nt, out = C.new_mat(name)
    v = C.coords(nt, "object")
    sep = C.N(nt, "SeparateXYZ", {"Vector": v})
    dx = C.mathn(nt, "SUBTRACT", sep.outputs[0], center[0])
    dz = C.mathn(nt, "SUBTRACT", sep.outputs[2], center[1])
    ang = C.mathn(nt, "ARCTAN2", dz, dx)                                       # -pi..pi
    a01 = C.mathn(nt, "MULTIPLY", C.mathn(nt, "ADD", ang, math.pi), seams / (2 * math.pi))
    fa = C.mathn(nt, "FRACT", a01)
    da = C.mathn(nt, "ABSOLUTE", C.mathn(nt, "SUBTRACT", fa, 0.5))
    seam_a = C.maprange(nt, da, 0.488, 0.497, 0.0, 1.0)
    fy = C.mathn(nt, "FRACT", C.mathn(nt, "DIVIDE", sep.outputs[1], ring))
    dy = C.mathn(nt, "ABSOLUTE", C.mathn(nt, "SUBTRACT", fy, 0.5))
    seam_y = C.maprange(nt, dy, 0.492, 0.499, 0.0, 1.0)
    seam = C.mathn(nt, "MAXIMUM", seam_a, seam_y)
    cell = C.N(nt, "CombineXYZ", {"X": C.mathn(nt, "FLOOR", a01),
                                  "Y": C.mathn(nt, "FLOOR", C.mathn(nt, "DIVIDE", sep.outputs[1], ring))}).outputs[0]
    rnd = C.N(nt, "TexWhiteNoise", {"Vector": cell}, noise_dimensions="3D").outputs["Value"]
    tv = C.maprange(nt, rnd, 0, 1, 1 - patchy, 1 + patchy * 0.6)
    shade = C.mix(nt, 1.0, C.col(color), C.N(nt, "CombineXYZ", {"X": tv, "Y": tv, "Z": tv}).outputs[0], blend="MULTIPLY")
    # stains: big blotches + vertical drip streaks, stronger low on the envelope
    nbig = C.noise(nt, v, 0.25, 6, 0.65, distortion=0.6)
    nstr = C.noise(nt, C.vmath(nt, "MULTIPLY", v, (2.5, 2.5, 0.12)), 1.0, 5, 0.6)
    low = C.maprange(nt, sep.outputs[2], center[1] + 4.0, center[1] - 8.0, 0.0, 1.0)
    st = C.mathn(nt, "MAXIMUM", C.maprange(nt, nbig, 0.52, 0.72, 0.0, 0.55),
                 C.mathn(nt, "MULTIPLY", C.maprange(nt, nstr, 0.5, 0.75), C.mathn(nt, "ADD", 0.25, low)))
    shade = C.mix(nt, C.mathn(nt, "MULTIPLY", st, 1.0, clamp=True), shade, C.col(stain))
    shade = C.mix(nt, C.mathn(nt, "MULTIPLY", seam, 0.4), shade, "#6a5840")
    weave = C.N(nt, "TexWave", {"Vector": v, "Scale": 120.0}, wave_type="BANDS", bands_direction="X").outputs["Factor"]
    weave2 = C.N(nt, "TexWave", {"Vector": v, "Scale": 120.0}, wave_type="BANDS", bands_direction="Y").outputs["Factor"]
    nf = C.noise(nt, v, 3.0, 6, 0.6)
    h = C.mathn(nt, "ADD", C.mathn(nt, "MULTIPLY", C.mathn(nt, "MULTIPLY", weave, weave2), 0.15),
                C.mathn(nt, "MULTIPLY", nf, 0.6))
    h = C.mathn(nt, "SUBTRACT", h, C.mathn(nt, "MULTIPLY", seam, 0.6))
    rough = C.maprange(nt, nf, 0.3, 0.7, 0.78, 0.92)
    b = C.N(nt, "BsdfPrincipled")
    for k, val in (("Base Color", shade), ("Roughness", rough), ("Sheen Weight", 0.5), ("Sheen Roughness", 0.5),
                   ("Specular IOR Level", 0.3), ("Normal", C.bump(nt, h, 0.3, 0.01))):
        C._sock_set(b.inputs[k], val)
    tr = C.N(nt, "BsdfTranslucent", {"Color": C.mix(nt, 1.0, shade, "#ffcf8a", blend="MULTIPLY")})
    mx = C.N(nt, "MixShader", {"Fac": transl})
    nt.links.new(b.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return m


def membrane_mat(name, color="#7e3426", color2="#4a1c12", transl=0.25):
    """Fish-fin membrane: radial ray veins, darker edges, translucent when back-lit."""
    m, nt, out = C.new_mat(name)
    v = C.coords(nt, "object")
    w = C.N(nt, "TexWave", {"Vector": v, "Scale": 6.0, "Distortion": 2.0, "Detail": 2.0},
            wave_type="BANDS", bands_direction="DIAGONAL", wave_profile="SIN").outputs["Factor"]
    n = C.noise(nt, v, 2.0, 6, 0.6)
    nf = C.noise(nt, v, 25.0, 4, 0.6)
    shade = C.mix(nt, C.maprange(nt, w, 0.6, 1.0, 0.0, 0.6), C.col(color), C.col(color2))
    shade = C.mix(nt, C.maprange(nt, n, 0.45, 0.75, 0.0, 0.5), shade, "#3b1a10")
    b = C.N(nt, "BsdfPrincipled")
    for k, val in (("Base Color", shade), ("Roughness", C.maprange(nt, nf, 0.3, 0.7, 0.5, 0.75)),
                   ("Sheen Weight", 0.3), ("Coat Weight", 0.1),
                   ("Normal", C.bump(nt, C.mathn(nt, "ADD", w, C.mathn(nt, "MULTIPLY", nf, 0.3)), 0.25, 0.01))):
        C._sock_set(b.inputs[k], val)
    tr = C.N(nt, "BsdfTranslucent", {"Color": C.mix(nt, 0.5, shade, "#d0603a", blend="SCREEN")})
    mx = C.N(nt, "MixShader", {"Fac": transl})
    nt.links.new(b.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return m


def fish_mat(name, color="#6f9fb4"):
    m, nt, out = C.new_mat(name)
    v = C.coords(nt, "object")
    sc = C.N(nt, "TexVoronoi", {"Vector": v, "Scale": 400.0}, feature="DISTANCE_TO_EDGE").outputs["Distance"]
    sep = C.N(nt, "SeparateXYZ", {"Vector": v})
    belly = C.maprange(nt, C.noise(nt, v, 30.0, 3, 0.5), 0.3, 0.7, 0.0, 0.4)
    shade = C.mix(nt, belly, C.col(color), "#d9e2df")
    C.principled(nt, out, color=shade, metal=0.25, rough=0.22, coat=0.6, coat_rough=0.05,
                 normal=C.bump(nt, sc, 0.2, 0.0005))
    return m


def cloud_mat(name, z_lo=-60.0, z_hi=60.0, top="#fbf6ee", bottom="#93a0b5", transl=0.4, bump_scale=0.08, ao=0.0,
              glow=0.35):
    """Opaque soft cloud surface: white sunlit tops, blue-grey flat bases, sheen rim + translucency glow."""
    m, nt, out = C.new_mat(name)
    v = C.coords(nt, "world")
    z = C.N(nt, "SeparateXYZ", {"Vector": v}).outputs[2]
    k = C.maprange(nt, z, z_lo, z_hi, 0.0, 1.0, "SMOOTHSTEP")
    shade = C.mix(nt, k, C.col(bottom), C.col(top))
    if ao:
        ao_n = C.N(nt, "AmbientOcclusion", {"Distance": ao}, samples=2, only_local=True)
        shade = C.mix(nt, C.mathn(nt, "MULTIPLY", C.mathn(nt, "SUBTRACT", 1.0, ao_n.outputs["AO"], clamp=True), 0.45),
                      shade, "#8a98b2")
    n1 = C.noise(nt, v, bump_scale, 6, 0.65, distortion=0.3)
    n2 = C.noise(nt, v, bump_scale * 6, 4, 0.6)
    b = C.N(nt, "BsdfPrincipled")
    for kk, val in (("Base Color", shade), ("Roughness", 1.0), ("Sheen Weight", 1.0), ("Sheen Roughness", 0.6),
                    ("Sheen Tint", (1, 1, 1, 1)), ("Specular IOR Level", 0.0),
                    ("Normal", C.bump(nt, C.mathn(nt, "ADD", n1, C.mathn(nt, "MULTIPLY", n2, 0.35)), 0.55, 4.0))):
        C._sock_set(b.inputs[kk], val)
    tr = C.N(nt, "BsdfTranslucent", {"Color": C.col("#fff1dc")})
    mx = C.N(nt, "MixShader", {"Fac": transl})
    nt.links.new(b.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2])
    # fake multiple scattering: a faint cool self-glow lifts the shadow sides (opaque clouds otherwise go rock-grey)
    em = C.N(nt, "Emission", {"Color": C.col("#c9d8ec"), "Strength": glow})
    add = C.N(nt, "AddShader")
    nt.links.new(mx.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    return m


def sky_world(strength=1.0):
    """Gradient sky: warm hazy horizon -> blue zenith, warm glow around the sun, pale cloud-floor below horizon."""
    w = bpy.data.worlds.new("sky"); bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    d = C.N(nt, "TexCoord").outputs["Generated"]
    z = C.N(nt, "SeparateXYZ", {"Vector": d}).outputs[2]
    c = C.mix(nt, C.maprange(nt, z, 0.0, 0.2, 0, 1, "SMOOTHSTEP"), C.col("#f3d3a6"), C.col("#8db6dc"))
    c = C.mix(nt, C.maprange(nt, z, 0.15, 0.7, 0, 1, "SMOOTHSTEP"), c, C.col("#2f64a6"))
    c = C.mix(nt, C.maprange(nt, z, 0.0, -0.12, 0, 1), c, C.col("#d2d4d4"))
    sd = tuple(-x for x in SUN_DIR)
    dot = C.vmath(nt, "DOT_PRODUCT", d, sd, out=1)
    glow = C.mathn(nt, "POWER", C.maprange(nt, dot, 0.6, 1.0), 4.0)
    c = C.mix(nt, C.mathn(nt, "MULTIPLY", glow, 0.85, clamp=True), c, C.col("#ffd9a6"))
    bg = C.N(nt, "Background", {"Color": c, "Strength": C.mathn(nt, "ADD", strength, C.mathn(nt, "MULTIPLY", glow, 2.5))})
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    return w


# ====================================================================== model
model = C.load("airship", size=40.0)
mn, mx = model.bounds
C.log("airship bounds", [round(v, 2) for v in mn], [round(v, 2) for v in mx])

M_CANVAS = canvas_mat("as_canvas")
M_PATCH = canvas_mat("as_canvas_patch", color="#8c9893", stain="#4f5650", patchy=0.05, seams=40, ring=0.9)
M_PATCH2 = canvas_mat("as_canvas_patch2", color="#a8845a", stain="#5d4228", patchy=0.05, seams=40, ring=0.9)
M_ROPE = rope_mat("as_rope_m")
M_FIN = membrane_mat("as_fin_m")
M_FISH = fish_mat("as_fish_m")
M_WA = wwood("as_wood_a_m", "#7f5a3e", "#4e3322", "Y", "object", grey=0.3, rough=0.7, rnd=False, grain=14.0, contrast=0.55)
M_WB = wwood("as_wood_b_m", "#94704f", "#5e4430", "Y", "object", grey=0.35, rough=0.68, rnd=False, grain=14.0,
             contrast=0.55)
M_WC = wwood("as_wood_c_m", "#634331", "#3b281c", "Y", "object", grey=0.25, rough=0.72, rnd=False, grain=14.0,
             contrast=0.55)
LOOKS = {
    "as_balloon": M_CANVAS, "as_patch": M_PATCH, "as_rope": M_ROPE, "as_fin": M_FIN, "as_fish": M_FISH,
    "as_wood_a": M_WA, "as_wood_b": M_WB, "as_wood_c": M_WC,
    "as_meat": ("plastic", dict(color="#a8443a", rough=0.35, coat=0.4)),
    "as_iron": ("metal", dict(color="#3b3836", rough=0.55, grime=0.6)),
    "as_barrel": ("painted", dict(color="#3d6a66", rough=0.45, grime=0.6, wear=0.7, panels=None, under="#7a6a55")),
    "brass": ("metal", dict(color="#c49a4a", rough=0.28, grime=0.55)),
}
C.apply_looks(model.objs, LOOKS)
# hull: painted planking (the source file gives the hull shells an 'acmat' iron material)
M_HULL = C.material("painted", "as_hull_paint", color="#5c3527", rough=0.6, grime=0.8, wear=0.6,
                    panels=(1000.0, 7.3, 0.42), seam_width=0.016, under="#8a6a4a", grime_color="#1e130c", streaks=1.0,
                    tint_var=0.12)
M_HULL_TRIM = C.material("painted", "as_hull_trim", color="#3b2a20", rough=0.55, grime=0.6, wear=0.6,
                         panels=(1000.0, 1.8, 1000.0), under="#8a6a48", grime_color="#140d08")
for o in model.objs:
    b = ML.base(o.name)
    if b == "ellipse":
        a, bb = ML.bounds([o])
        C.assign(o, M_HULL if (bb.z - a.z) > 4.0 else M_HULL_TRIM)
    elif o.name == "平面.008":                       # big tail fins
        C.assign(o, M_FIN)
patches = [o for o in model.objs if C.palette_of(o.material_slots[0].material) == "as_canvas_patch"
           or (o.material_slots and o.material_slots[0].material is M_PATCH)]
for i, o in enumerate(patches):
    if i % 2:
        C.assign(o, M_PATCH2)

# ====================================================================== set helpers
DECK = 9.4            # pier deck top
R = random.Random(11)


class MeshBuilder:
    """Accumulates many boxes / cylinders into one bmesh (one object per material), each piece tagged with a
    random face attribute 'rnd' used by the wood shader for per-plank tint."""

    def __init__(self):
        self.bm = bmesh.new()
        self.lay = self.bm.faces.layers.float.new("rnd")

    def _tag(self, faces):
        r = R.random()
        for f in faces:
            f[self.lay] = r

    def box(self, size, loc, rot=(0, 0, 0), bevel=0.0):
        before = set(self.bm.faces)
        M = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(rot[2]), 4, "Z") @ \
            Matrix.Rotation(math.radians(rot[1]), 4, "Y") @ Matrix.Rotation(math.radians(rot[0]), 4, "X") @ \
            Matrix.Diagonal((size[0], size[1], size[2], 1.0))
        res = bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)
        if bevel:
            vs = set(res["verts"])
            edges = [e for e in self.bm.edges if e.verts[0] in vs]
            bmesh.ops.bevel(self.bm, geom=edges, offset=bevel, segments=1, affect="EDGES", profile=0.5)
        self._tag([f for f in self.bm.faces if f not in before])

    def cyl(self, r, p0, p1, seg=10):
        before = set(self.bm.faces)
        p0 = Vector(p0); p1 = Vector(p1); d = p1 - p0
        M = Matrix.Translation((p0 + p1) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(self.bm, cap_ends=True, segments=seg, radius1=r, radius2=r * 0.92, depth=d.length,
                              matrix=M)
        self._tag([f for f in self.bm.faces if f not in before])

    def done(self, name, mat, role="set", hide_turn=True, smooth=True):
        o = C._obj_from_bm(name, self.bm, mat, role=role)
        if smooth:
            C._autosmooth(o, 30)
        if hide_turn:
            o["hide_turn"] = True
        return o


def pier_obj(o):
    o["hide_turn"] = True
    return o


M_PLANK_X = wwood("pier_plank_x", "#7d6045", "#4a3626", "X", grey=0.55)
M_PLANK_Y = wwood("pier_plank_y", "#7d6045", "#4a3626", "Y", grey=0.55)
M_POST = wwood("pier_post", "#6b4e37", "#3a281b", "Z", grey=0.5, rough=0.78)
M_BEAM = wwood("pier_beam", "#5f4532", "#33241a", "X", grey=0.45, rough=0.78)
M_BEAM_Y = wwood("pier_beam_y", "#5f4532", "#33241a", "Y", grey=0.45, rough=0.78)
M_ROPE_W = rope_mat("pier_rope", "#9a7c55", "world")
M_ROPE_D = rope_mat("pier_rope_dark", "#6e5638", "world")
M_IRON = C.material("metal", "pier_iron", color="#2e2b29", rough=0.6, grime=0.7, space="world")
M_COPPER = C.material("metal", "pier_copper", color="#b8703f", rough=0.38, grime=0.6, space="world")
M_TIN = C.material("painted", "pier_tin", color="#6f6a60", metal=0.6, rough=0.5, grime=0.8, wear=0.4,
                   panels=(0.15, 1000, 1000), seam_width=0.02, space="world", grime_color="#3a2414", streaks=1.0)
M_CRATE = wwood("pier_crate", "#9c7a52", "#5c4128", "X", grey=0.3, rough=0.7)
M_BARREL = wwood("pier_barrel", "#7a5233", "#45291a", "Z", grey=0.25, rough=0.6)
M_BARREL_P = C.material("painted", "pier_barrel_teal", color="#3f6b67", rough=0.45, grime=0.6, wear=0.7, panels=None,
                        space="world", under="#6b5a44")
M_CANVAS_SET = C.material("fabric", "pier_tarp", color="#9c8c6a", rough=0.9, weave=90.0, space="world")
M_LAMP = C.material("emissive", "lantern_glow", color=C.kelvin(2300), strength=18.0, base="#ffd29a")
M_FISH_SET = fish_mat("pier_fish", "#7aa6b8")

# ---------------------------------------------------------------- decks
FP = dict(x0=-17.0, x1=-8.4, y0=-1.0, y1=3.6)        # finger pier (planks run along Y)
BW = dict(x0=-22.0, x1=-17.0, y0=-60.0, y1=60.0)      # boardwalk (planks run along X)

planks_y = MeshBuilder()           # planks whose long axis is Y (finger pier)
planks_x = MeshBuilder()           # planks whose long axis is X (boardwalk)
x = FP["x0"]
while x < FP["x1"]:
    w = R.uniform(0.22, 0.32)
    if R.random() > 0.04:
        planks_y.box((w - 0.025, FP["y1"] - FP["y0"] + R.uniform(-0.15, 0.25), 0.07),
                     (x + w / 2, (FP["y0"] + FP["y1"]) / 2 + R.uniform(-0.1, 0.1), DECK - 0.035 + R.uniform(-0.012, 0.012)),
                     (R.uniform(-0.8, 0.8), 0, R.uniform(-0.6, 0.6)), 0.008)
    x += w
y = BW["y0"]
while y < BW["y1"]:
    w = R.uniform(0.22, 0.32)
    if R.random() > 0.03 and not (FP["y0"] < y < FP["y1"] and False):
        planks_x.box((BW["x1"] - BW["x0"] + R.uniform(-0.2, 0.3), w - 0.025, 0.07),
                     ((BW["x0"] + BW["x1"]) / 2 + R.uniform(-0.12, 0.12), y + w / 2, DECK - 0.035 + R.uniform(-0.012, 0.012)),
                     (0, R.uniform(-0.8, 0.8), R.uniform(-0.5, 0.5)), 0.008)
    y += w
planks_y.done("fp_planks", M_PLANK_Y)
planks_x.done("bw_planks", M_PLANK_X)

# stringers / beams under the decks + long stilts dropping into the cloud sea
beams_x = MeshBuilder(); beams_y = MeshBuilder(); posts = MeshBuilder()
for yy in (FP["y0"] + 0.2, (FP["y0"] + FP["y1"]) / 2, FP["y1"] - 0.2):
    beams_x.box((FP["x1"] - FP["x0"] + 0.4, 0.22, 0.3), ((FP["x0"] + FP["x1"]) / 2, yy, DECK - 0.22), bevel=0.02)
for xx in (BW["x0"] + 0.25, (BW["x0"] + BW["x1"]) / 2, BW["x1"] - 0.25):
    beams_y.box((0.22, BW["y1"] - BW["y0"], 0.3), (xx, (BW["y0"] + BW["y1"]) / 2, DECK - 0.22), bevel=0.02)
STILTS = []
for xx in (-15.0, -11.6, -8.7):
    for yy in (FP["y0"] + 0.15, FP["y1"] - 0.15):
        STILTS.append((xx, yy))
    beams_y.box((0.24, FP["y1"] - FP["y0"] + 0.6, 0.26), (xx, (FP["y0"] + FP["y1"]) / 2, DECK - 0.5), bevel=0.02)
yy = BW["y0"] + 1.5
while yy < BW["y1"]:
    for xx in (BW["x0"] + 0.2, BW["x1"] - 0.2):
        STILTS.append((xx, yy))
    beams_x.box((BW["x1"] - BW["x0"] + 0.6, 0.24, 0.26), ((BW["x0"] + BW["x1"]) / 2, yy, DECK - 0.5), bevel=0.02)
    yy += 9.0
for k, (sx, sy) in enumerate(STILTS):
    lean = (R.uniform(-0.25, 0.25), R.uniform(-0.25, 0.25))
    bottom = -48.0 + R.uniform(-6, 4)
    posts.cyl(R.uniform(0.17, 0.22), (sx + lean[0], sy + lean[1], bottom), (sx, sy, DECK - 0.1), 10)
    # diagonal bracing between neighbouring stilts (upper part only)
    if k % 2 == 0 and k + 2 < len(STILTS):
        nx, ny = STILTS[k + 2]
        if abs(nx - sx) + abs(ny - sy) < 6:
            posts.cyl(0.08, (sx, sy, DECK - 0.6), (nx, ny, DECK - 4.5), 8)
            posts.cyl(0.08, (nx, ny, DECK - 0.6), (sx, sy, DECK - 4.5), 8)
    for hz in (DECK - 3.0, DECK - 7.5):
        if k % 2 == 0 and k + 1 < len(STILTS):
            ox, oy = STILTS[k + 1]
            beams_x.box((abs(ox - sx) + 0.4 if abs(ox - sx) > 0.5 else 0.18, abs(oy - sy) + 0.4 if abs(oy - sy) > 0.5 else 0.18,
                         0.18), ((sx + ox) / 2, (sy + oy) / 2, hz), bevel=0.015)
beams_x.done("beams_x", M_BEAM); beams_y.done("beams_y", M_BEAM_Y); posts.done("stilts", M_POST)

# ---------------------------------------------------------------- rail posts with rope coils + sagging rope rails
rail = MeshBuilder()
RAILS = []          # list of post-top points per rail line


def rope_coil(name, cx, cy, z0, r_post, turns=3, rr=0.035):
    pts = []
    for i in range(int(turns * 10) + 1):
        a = 2 * math.pi * i / 10
        pts.append((cx + math.cos(a) * (r_post + rr), cy + math.sin(a) * (r_post + rr), z0 + i * rr * 2.0 / 10 * 1.05))
    pier_obj(C.cable(name, pts, rr, M_ROPE_W, resolution=4))


def rail_line(name, p0, p1, n, height=1.15):
    p0 = Vector(p0); p1 = Vector(p1)
    tops = []
    for i in range(n + 1):
        p = p0.lerp(p1, i / n)
        h = height + R.uniform(-0.12, 0.15)
        rail.box((0.16, 0.16, h + 0.1), (p.x, p.y, DECK + h / 2 - 0.05), (R.uniform(-3, 3), R.uniform(-3, 3), R.uniform(0, 40)),
                 0.015)
        tops.append(Vector((p.x, p.y, DECK + h - 0.08)))
        rope_coil(f"{name}_coil{i}", p.x, p.y, DECK + h - 0.32, 0.1, turns=2.5)
    for i in range(n):
        a, b = tops[i], tops[i + 1]
        mid = (a + b) / 2 - Vector((0, 0, 0.28 + R.uniform(0, 0.12)))
        pier_obj(C.cable(f"{name}_rope{i}", [tuple(a), tuple(a.lerp(mid, 0.6)), tuple(mid), tuple(b.lerp(mid, 0.6)), tuple(b)],
                         0.025, M_ROPE_W, resolution=6))
        lo_a = a - Vector((0, 0, 0.5)); lo_b = b - Vector((0, 0, 0.5))
        mid2 = (lo_a + lo_b) / 2 - Vector((0, 0, 0.18))
        pier_obj(C.cable(f"{name}_rope_lo{i}", [tuple(lo_a), tuple(mid2), tuple(lo_b)], 0.02, M_ROPE_D, resolution=6))
    return tops


rail_line("rail_fp_s", (FP["x0"] + 0.4, FP["y0"] + 0.05, 0), (FP["x1"] - 0.3, FP["y0"] + 0.05, 0), 3)
rail_line("rail_fp_n", (FP["x0"] + 0.4, FP["y1"] - 0.05, 0), (FP["x1"] - 0.3, FP["y1"] - 0.05, 0), 3)
rail_line("rail_bw_w", (BW["x0"] + 0.05, -40, 0), (BW["x0"] + 0.05, 40, 0), 26)
rail_line("rail_bw_e1", (BW["x1"] - 0.05, -40, 0), (BW["x1"] - 0.05, FP["y0"] - 0.3, 0), 12)
rail_line("rail_bw_e2", (BW["x1"] - 0.05, FP["y1"] + 0.3, 0), (BW["x1"] - 0.05, 40, 0), 12)
rail.done("rail_posts", M_POST)

# ---------------------------------------------------------------- mooring: bollards, lines to the ship, gangplank
bol = MeshBuilder()
for (bx, by) in ((-8.9, -0.6), (-8.9, 3.2)):
    bol.cyl(0.2, (bx, by, DECK - 0.05), (bx, by, DECK + 0.55), 14)
    bol.cyl(0.26, (bx, by, DECK + 0.5), (bx, by, DECK + 0.62), 14)
    rope_coil(f"bollard_coil_{by:.0f}", bx, by, DECK + 0.12, 0.2, turns=3.5, rr=0.045)
bol.done("bollards", M_IRON)
# mooring lines: bollard -> ship bulwark (bow & stern quarters), slight sag
for k, (a, b) in enumerate((((-8.9, 3.2, DECK + 0.4), (-2.2, 9.0, 11.6)), ((-8.9, -0.6, DECK + 0.4), (-2.1, -6.5, 11.4)))):
    a = Vector(a); b = Vector(b); mid = (a + b) / 2 - Vector((0, 0, 0.7))
    pier_obj(C.cable(f"mooring_{k}", [tuple(a), tuple(mid), tuple(b)], 0.045, M_ROPE_W, resolution=10))
# gangplank: pier end -> deck bulwark gap
gp = MeshBuilder()
g0 = Vector((-8.6, 1.3, DECK)); g1 = Vector((-2.4, 1.3, 10.95))
dgp = g1 - g0; L = dgp.length; pitch = math.degrees(math.atan2(dgp.z, dgp.x))
for i in range(int(L / 0.3)):
    p = g0.lerp(g1, (i + 0.5) / (L / 0.3))
    gp.box((0.26, 1.2, 0.06), (p.x, p.y, p.z + 0.03), (0, -pitch, R.uniform(-1, 1)), 0.008)
for sy in (0.55, -0.55):
    gp.box((L, 0.1, 0.12), ((g0.x + g1.x) / 2, g0.y + sy, (g0.z + g1.z) / 2 - 0.04), (0, -pitch, 0), 0.01)
gp.done("gangplank", M_PLANK_Y)
for sy in (0.6, -0.6):
    a = g0 + Vector((0, sy, 1.0)); b = g1 + Vector((0, sy, 1.0)); m_ = (a + b) / 2 - Vector((0, 0, 0.35))
    pier_obj(C.cable(f"gang_rope_{sy}", [tuple(a), tuple(m_), tuple(b)], 0.022, M_ROPE_W))

# ---------------------------------------------------------------- lanterns (warm practicals)
lan = MeshBuilder()


def lantern(name, x, y, z_top, hang=0.45, light=40.0):
    """Lantern hanging from a bracket at z_top: iron cap + frame, glowing glass, point light."""
    zc = z_top - hang
    lan.box((0.05, 0.05, hang - 0.15), (x, y, z_top - (hang - 0.15) / 2))
    lan.cyl(0.16, (x, y, zc + 0.2), (x, y, zc + 0.26), 12)
    lan.cyl(0.13, (x, y, zc - 0.26), (x, y, zc - 0.21), 12)
    for a in range(4):
        aa = math.radians(45 + a * 90)
        lan.box((0.02, 0.02, 0.44), (x + math.cos(aa) * 0.12, y + math.sin(aa) * 0.12, zc - 0.02))
    g = C.cylinder(name + "_glass", 0.1, 0.38, (x, y, zc - 0.02), mat=M_LAMP, segments=12, role="keep")
    g["hide_turn"] = True
    lt = C.point(name + "_light", (x, y, zc - 0.02), light, C.kelvin(2300), 0.08)
    lt["hide_turn"] = True


LANTERN_POSTS = [(-16.7, -0.7), (-16.7, 3.3), (-12.5, 3.3), (-8.75, -0.7), (-21.7, 6.0), (-21.7, 14.0), (-21.7, -24.0),
                 (-17.3, 26.0)]
for k, (lx, ly) in enumerate(LANTERN_POSTS):
    top = DECK + 2.7
    rail.box((0.18, 0.18, 2.75), (lx, ly, DECK + 1.3), bevel=0.015) if False else None
    p = MeshBuilder(); p.box((0.18, 0.18, 2.8), (lx, ly, DECK + 1.35), bevel=0.015)
    dirv = Vector((0.5 if lx < -17.0 else 0.0, 0.5 if ly < 0 and lx > -17.0 else (-0.5 if lx > -17.0 else 0.0), 0))
    if dirv.length == 0:
        dirv = Vector((0.5, 0, 0))
    p.box((abs(dirv.x) + 0.12, abs(dirv.y) + 0.12, 0.1), (lx + dirv.x / 2, ly + dirv.y / 2, top))
    p.done(f"lantern_post_{k}", M_POST)
    lantern(f"lantern_{k}", lx + dirv.x, ly + dirv.y, top - 0.05)
lan.done("lantern_iron", M_IRON)

# ---------------------------------------------------------------- props: crates, barrels, baskets, nets, shack, derrick
props_crate = MeshBuilder(); props_barrel = MeshBuilder(); props_teal = MeshBuilder(); props_iron = MeshBuilder()


def crate(x, y, s, rz=0.0, z=DECK):
    props_crate.box((s, s * R.uniform(0.85, 1.0), s * R.uniform(0.75, 0.95)), (x, y, z + s * 0.42), (0, 0, rz), 0.02)
    for dz in (0.08, s * 0.72):
        props_crate.box((s + 0.03, s * 0.9 + 0.03, 0.07), (x, y, z + dz), (0, 0, rz), 0.01)


def barrel(x, y, h=0.95, r=0.34, teal=False, z=DECK, lie=False):
    mb = props_teal if teal else props_barrel
    if lie:
        mb.cyl(r, (x - h / 2, y, z + r), (x + h / 2, y, z + r), 18)
        for dx in (-h * 0.3, h * 0.3):
            props_iron.cyl(r + 0.012, (x + dx - 0.02, y, z + r), (x + dx + 0.02, y, z + r), 18)
        return
    mb.cyl(r, (x, y, z), (x, y, z + h), 18)
    for dz in (0.15, h - 0.15):
        props_iron.cyl(r + 0.012, (x, y, z + dz - 0.02), (x, y, z + dz + 0.02), 18)


# cluster at the junction of finger pier and boardwalk
crate(-19.0, -2.6, 1.0, 12); crate(-19.1, -2.5, 0.75, -8, DECK + 0.86); crate(-20.6, -3.4, 0.9, 40)
crate(-18.6, 5.6, 0.8, -15); barrel(-20.7, 4.6); barrel(-21.3, 5.4, teal=True); barrel(-20.4, 6.2, 0.9, 0.32)
barrel(-15.5, 2.6, 0.9, 0.3, lie=True)
crate(-10.6, -0.3, 0.7, 25); barrel(-11.6, -0.4, 0.8, 0.28, teal=True)
crate(-20.8, -22.0, 1.1, 5); crate(-20.7, -20.7, 0.9, -10); barrel(-18.0, -21.4, teal=True); barrel(-18.6, -20.5)
crate(-21.0, 21.0, 1.0, 30); barrel(-18.2, 20.0)
props_crate.done("crates", M_CRATE); props_barrel.done("barrels", M_BARREL); props_teal.done("barrels_teal", M_BARREL_P)
props_iron.done("hoops", M_IRON)

# fish baskets with fish
bask = MeshBuilder()
for k, (bx, by) in enumerate(((-13.2, 3.0), (-12.6, 2.6), (-18.2, -1.6))):
    bask.cyl(0.32, (bx, by, DECK), (bx, by, DECK + 0.42), 16)
bask.done("baskets", wwood("basket", "#a07c4c", "#6a4a2a", "Z", grey=0.2, rough=0.85))
fish = MeshBuilder()
for k in range(14):
    bx, by = ((-13.2, 3.0), (-12.6, 2.6), (-18.2, -1.6))[k % 3]
    a = R.uniform(0, math.pi)
    fish.box((0.38, 0.09, 0.12), (bx + R.uniform(-0.15, 0.15), by + R.uniform(-0.15, 0.15), DECK + 0.42 + R.uniform(0, 0.1)),
             (R.uniform(-20, 20), R.uniform(-15, 15), math.degrees(a)), 0.035)
fo = fish.done("fish_pile", M_FISH_SET)
for mdn in ("sub",):
    md = fo.modifiers.new(mdn, "SUBSURF"); md.levels = 1; md.render_levels = 2

# rope coils lying on the deck
for k, (cx, cy) in enumerate(((-14.2, -0.3), (-19.5, 1.4))):
    pts = []
    for i in range(60):
        a = 2 * math.pi * i / 12
        rr = 0.18 + 0.06 * (i / 60) * 4
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr, DECK + 0.04 + (i % 12 == 0) * 0.0 + 0.012 * (i / 12)))
    pier_obj(C.cable(f"deck_coil_{k}", pts, 0.04, M_ROPE_W, resolution=3))

# shack on the boardwalk
SX, SY = -20.4, -12.5
sh = MeshBuilder()
for dx in range(-8, 9):
    sh.box((0.03 + 0.08, 0.26, 2.6), (SX + 1.2, SY + dx * 0.26, DECK + 1.3), (0, R.uniform(-0.6, 0.6), 0), 0.01)
for dx in range(-6, 7):
    sh.box((0.26, 0.1, 2.6), (SX + dx * 0.26 * 0.5 - 0.0, SY - 2.2, DECK + 1.3), (0, 0, 0), 0.01) if False else None
sh.box((2.6, 4.6, 2.6), (SX - 0.15, SY, DECK + 1.3), bevel=0.02)
sh.box((0.22, 1.2, 1.9), (SX + 1.27, SY - 0.6, DECK + 0.95), bevel=0.01)      # door frame
sh.done("shack", M_PLANK_X)
roof = MeshBuilder()
roof.box((3.4, 5.4, 0.06), (SX - 0.1, SY, DECK + 2.85), (0, -8, 0))
roof.done("shack_roof", M_TIN)
win = C.box("shack_window", (0.04, 0.8, 0.6), (SX + 1.23, SY + 1.1, DECK + 1.6), mat=C.material("emissive", "window_glow",
            color=C.kelvin(2400), strength=3.0, base="#3a2a1a"), bevel=0, role="keep")
win["hide_turn"] = True
C.text("shack_sign", "漁港", 0.42, (SX + 1.28, SY - 0.2, DECK + 2.35), (90, 0, 90),
       C.material("flat", "sign_paint", color="#e8dcc0", rough=0.8), C.FONT_TC, extrude=0.01)["hide_turn"] = True

# cargo derrick at the pier end: mast + boom + hanging net with a crate
dm = MeshBuilder()
DX, DY = -9.6, 3.4
dm.cyl(0.16, (DX, DY, DECK), (DX, DY, DECK + 6.0), 12)
dm.cyl(0.11, (DX, DY, DECK + 1.2), (DX + 3.0, DY - 1.5, DECK + 5.0), 10)
dm.done("derrick", M_POST)
pier_obj(C.cable("derrick_stay", [(DX, DY, DECK + 6.0), (DX + 1.5, DY - 0.75, DECK + 5.75), (DX + 3.0, DY - 1.5, DECK + 5.0)],
                 0.02, M_ROPE_W))
pier_obj(C.cable("derrick_line", [(DX + 3.0, DY - 1.5, DECK + 5.0), (DX + 3.0, DY - 1.5, DECK + 3.2)], 0.02, M_ROPE_W))
hc = MeshBuilder()
hc.box((0.8, 0.8, 0.65), (DX + 3.0, DY - 1.5, DECK + 2.8), (0, 0, 20), 0.02)
hc.done("derrick_crate", M_CRATE)
for k in range(4):
    a = math.radians(20 + 45 + k * 90)
    pier_obj(C.cable(f"sling_{k}", [(DX + 3.0, DY - 1.5, DECK + 3.25), (DX + 3.0 + math.cos(a) * 0.5, DY - 1.5 + math.sin(a) * 0.5,
                                                                       DECK + 2.8)], 0.012, M_ROPE_W))

# suspension bridge from the boardwalk's north end to a distant platform (silhouette in the haze)
B0 = Vector((-19.5, 60.0, DECK)); B1 = Vector((-75.0, 150.0, DECK - 6.0))
br = MeshBuilder()
Lb = (B1 - B0).length; nb = int(Lb / 0.45); ang = math.degrees(math.atan2(B1.y - B0.y, B1.x - B0.x))
for i in range(nb):
    t = (i + 0.5) / nb
    p = B0.lerp(B1, t) - Vector((0, 0, 7.0 * math.sin(math.pi * t)))
    br.box((0.25, 1.8, 0.06), (p.x, p.y, p.z), (0, 0, ang + 90 + R.uniform(-4, 4)), 0)
br.done("bridge_planks", M_PLANK_Y)
for side in (-1, 1):
    off = Vector((math.cos(math.radians(ang + 90)), math.sin(math.radians(ang + 90)), 0)) * 0.95 * side
    pts = [tuple(B0.lerp(B1, t) - Vector((0, 0, 7.0 * math.sin(math.pi * t) - 1.0)) + off) for t in [i / 8 for i in range(9)]]
    pier_obj(C.cable(f"bridge_rope_{side}", pts, 0.05, M_ROPE_D))
# distant platforms on stilts with shacks
far = MeshBuilder()
for (px, py, pz, s) in ((-75.0, 150.0, DECK - 6.0, 1.0), (-280.0, -130.0, 6.0, 1.6),
                        (140.0, -120.0, 2.0, 1.2)):
    far.box((10 * s, 8 * s, 0.4), (px, py, pz), (0, 0, R.uniform(0, 40)))
    far.box((4 * s, 3.5 * s, 3.0 * s), (px + 1.0, py, pz + 1.7 * s), (0, 0, R.uniform(0, 40)))
    for k in range(6):
        far.cyl(0.35 * s, (px + R.uniform(-4, 4) * s, py + R.uniform(-3, 3) * s, -70), (px + R.uniform(-4, 4) * s,
                                                                                     py + R.uniform(-3, 3) * s, pz), 8)
far.done("far_platforms", M_POST, hide_turn=True)

# distant airships (simple silhouettes, like the other ships of the port)
def far_ship(name, loc, length, rz):
    m = C.material("fabric", "far_canvas", color="#cdbf9f", rough=0.9, weave=20.0, space="world")
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1.0)
    bmesh.ops.scale(bm, vec=(length * 0.22, length * 0.5, length * 0.2), verts=bm.verts)
    b = C._obj_from_bm(name, bm, m, loc, (0, 0, rz), smooth=True)
    h = C.box(name + "_hull", (length * 0.12, length * 0.45, length * 0.08),
              (loc[0], loc[1], loc[2] - length * 0.32), (0, 0, rz), mat=M_BEAM, bevel=0.1)
    for o in (b, h):
        o["role"] = "keep"


far_ship("far_ship_a", (230.0, 210.0, 60.0), 34.0, 25)
far_ship("far_ship_b", (-260.0, 300.0, 40.0), 28.0, -40)
far_ship("far_ship_c", (190.0, -260.0, 30.0), 30.0, 70)

# ====================================================================== clouds
# Opaque surfaces only (no volumetrics): metaball cumulus (blobs merge with soft necks instead of the hard
# intersection lines of stacked spheres) + noise displacement; a billow heightfield for the cloud sea.
CLOUD_Z = -55.0
M_CLOUD = cloud_mat("cloud_sea", CLOUD_Z - 20, CLOUD_Z + 40, bump_scale=0.03, ao=25.0)
M_CU = cloud_mat("cumulus_m", CLOUD_Z, CLOUD_Z + 180, transl=0.45, bump_scale=0.05, ao=30.0)


def cloud_sea(name, size=8000.0, n=400, fine=(1600.0, 200)):
    """Billow heightfield (|noise| = rounded lumps with soft creases between them): a fine inner grid and a
    coarse outer grid that reaches the horizon (no gap between sea edge and sky)."""
    def h_at(x, y):
        a = abs(mnoise.noise(Vector((x / 130.0, y / 130.0, 0.3))))
        b = abs(mnoise.noise(Vector((x / 45.0, y / 45.0, 1.7))))
        c = abs(mnoise.noise(Vector((x / 17.0, y / 17.0, 4.1))))
        big = mnoise.fractal(Vector((x / 700.0, y / 700.0, 2.2)), 0.5, 2.0, 2)
        return CLOUD_Z - 20.0 + a * 50.0 + b * 22.0 + c * 6.0 + big * 25.0
    objs = []
    for nm, sz, segs, hole in ((name, fine[0], int(fine[1] * 1.6), 0.0), (name + "_outer", size, n // 4, fine[0] / 2 - 10)):
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=segs, y_segments=segs, size=sz / 2)
        if hole:
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(abs(v.co.x) < hole and abs(v.co.y) < hole
                                                                  for v in f.verts)], context="FACES")
        for v in bm.verts:
            v.co.z = h_at(v.co.x, v.co.y) - (0.0 if not hole else 3.0)
        objs.append(C._obj_from_bm(nm, bm, M_CLOUD, role="keep", smooth=True))
    return objs


cloud_sea("cloud_sea")


def meta_cloud(name, base, width, height, seed, n=60, shoulders=2, res=None, mat=None):
    """Cumulus from metaballs: core column + many envelope blobs + domed top (+ lower shoulders), converted to a
    mesh, displaced with noise for cauliflower detail, flat base."""
    rr = random.Random(seed); base = Vector(base)
    mb = bpy.data.metaballs.new(name + "MB")
    res = res or max(1.0, width / 70.0)
    mb.resolution = res; mb.render_resolution = res; mb.threshold = 0.6
    ob = bpy.data.objects.new(name + "MB", mb); C.link(ob)

    def ball(c, r):
        e = mb.elements.new(); e.co = c - base; e.radius = r; e.stiffness = 2.0

    def column(off, w, h, k):
        for i in range(max(3, k // 5)):
            t = i / max(3, k // 5)
            ball(base + off + Vector((0, 0, h * t * 0.8 + w * 0.1)), w * (0.42 - 0.18 * t))
        for i in range(k):
            t = rr.random() ** 0.85
            env = w * (0.42 - 0.18 * t)
            a = rr.uniform(0, 2 * math.pi)
            r = w * rr.uniform(0.09, 0.17) * (1.0 - 0.35 * t)
            ball(base + off + Vector((math.cos(a) * env * rr.uniform(0.55, 0.95), math.sin(a) * env * rr.uniform(0.55, 0.95),
                                      h * t + r * 0.3)), r)
        for i in range(max(3, k // 6)):
            a = rr.uniform(0, 2 * math.pi); r_ = w * rr.uniform(0.0, 0.16)
            ball(base + off + Vector((math.cos(a) * r_, math.sin(a) * r_, h * rr.uniform(0.9, 1.0))), w * rr.uniform(0.1, 0.16))

    column(Vector((0, 0, 0)), width, height, n)
    for k in range(shoulders):
        a = rr.uniform(0, 2 * math.pi)
        off = Vector((math.cos(a), math.sin(a), 0)) * width * rr.uniform(0.4, 0.55)
        column(off, width * rr.uniform(0.55, 0.75), height * rr.uniform(0.35, 0.6), n // 2)
    ob.location = base
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob, do_unlink=True); bpy.data.metaballs.remove(mb)
    me.transform(Matrix.Translation(base))
    bm = bmesh.new(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    bm.normal_update()
    sc = width * 0.07
    for v in bm.verts:
        q = v.co / sc
        v.co += v.normal * sc * 0.35 * mnoise.fractal(q + Vector((seed * 3.1, 0, 0)), 0.55, 2.0, 3)
        if v.co.z < base.z:
            v.co.z = base.z + (v.co.z - base.z) * 0.05
    o = C._obj_from_bm(name, bm, mat or M_CU, role="keep", smooth=True)
    C.log(f"cloud {name}: {len(o.data.polygons)} faces")
    return o


meta_cloud("cuHero", (520.0, 300.0, CLOUD_Z), 300.0, 300.0, 1, 90)
meta_cloud("cuSone", (420.0, -440.0, CLOUD_Z), 280.0, 250.0, 2, 80)
meta_cloud("cuStwo", (-430.0, 420.0, CLOUD_Z), 300.0, 270.0, 3, 80)
meta_cloud("cuFarA", (-650.0, -360.0, CLOUD_Z), 340.0, 170.0, 7, 60)
meta_cloud("cuFarB", (850.0, -60.0, CLOUD_Z), 340.0, 200.0, 8, 60)
RC = random.Random(21)
for k in range(16):                         # smaller cumulus humilis scattered on the sea
    a = RC.uniform(0, 2 * math.pi); d = RC.uniform(160, 900)
    w_ = RC.uniform(50, 110)
    meta_cloud(f"cuSmall{k:02d}", (math.cos(a) * d, math.sin(a) * d, CLOUD_Z + 5), w_, w_ * RC.uniform(0.3, 0.6),
               40 + k, 18, shoulders=1)

# ====================================================================== light + atmosphere
sky_world(1.0)
C.sun("sun", tuple(SUN_DIR), 5.0, "#ffbf80", angle=1.2)
# sunlit cloud sea bouncing light up into the shadow side of the ship (motivated fill, invisible to camera)
C.area("cloud_bounce", (0.0, 0.0, -25.0), (0.0, 0.0, 10.0), 60000.0, "#e6ecf2", 70.0)


def haze_dome(name, center, radii, density, color, anisotropy=0.5):
    """Homogeneous haze in a flattened ellipsoid: the path length changes smoothly with view direction
    (a box shows a hard line where rays leave through its top instead of its side)."""
    m, nt, out = C.new_mat(name + "_vol")
    v = C.N(nt, "VolumePrincipled", {"Density": density, "Color": C.col(color), "Anisotropy": anisotropy})
    nt.links.new(v.outputs[0], out.inputs["Volume"])
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0)
    bmesh.ops.scale(bm, vec=radii, verts=bm.verts)
    o = C._obj_from_bm(name, bm, m, center, role="fx")
    o.visible_shadow = False
    return o


haze_dome("haze", (0, 0, -60), (1700, 1700, 520), 0.00055, "#dde4ec", 0.5)


def _haze_density(d):
    """Set the haze dome's density, return the previous value (s2 looks toward the sun: the full haze washes it out)."""
    m = bpy.data.materials.get("haze_vol")
    for n in (m.node_tree.nodes if m else []):
        if n.type == "PRINCIPLED_VOLUME":
            old = n.inputs["Density"].default_value
            n.inputs["Density"].default_value = d
            return old
    return None


_s2 = {}


def _s2_setup():
    _s2["d"] = _haze_density(0.00010)


def _s2_teardown():
    if _s2.get("d") is not None:
        _haze_density(_s2["d"])


# ====================================================================== shots
SHOTS = [
    C.Shot("hero", dict(loc=(-18.2, -31.0, 10.9), target=(-3.0, 0.0, 17.0), lens=21, fstop=5.6, focus=(-3.0, -2.0, 12.0)),
           "天空漁港的碼頭邊：熱氣球飛船繫在木棧橋旁，午後斜陽照亮補丁氣囊，腳下是一整片雲海。", kind="hero"),
    C.Shot("card", dict(loc=(-55.0, -46.0, 24.0), target=(0.0, 0.0, 16.0), lens=35),
           "三分之四視角：飛船停靠在碼頭，背後是高聳的積雲。", kind="card"),
    C.Shot("s1", dict(loc=(-44.0, 48.0, 18.0), target=(-0.5, 0.5, 16.5), lens=42),
           "三分之四前視：補丁氣囊、纜繩網與木造船身。"),
    C.Shot("s2", dict(loc=(36.0, -46.0, 23.0), target=(0.0, -4.0, 15.0), lens=35),
           "後側俯視：船尾的魚鰭尾翼與甲板，後方是碼頭棧橋與雲海。",
           exposure=-1.0, setup=_s2_setup, teardown=_s2_teardown),
    C.Shot("s3", dict(loc=(-5.5, -10.0, 16.0), target=(0.5, -3.4, 11.8), lens=42, fstop=2.8, focus=(0.5, -3.65, 12.2)),
           "甲板特寫：船尾的舵輪、地籠與木桶。"),
    C.Shot("s4", dict(loc=(-13.0, -27.0, 21.0), target=(-6.5, -14.0, 25.0), lens=45, fstop=2.8, focus=(-6.2, -15.0, 24.5)),
           "氣囊特寫：帆布的縫線、污漬與一圈圈綁緊的纜繩。"),
]
CAPTIONS = {"clay": "白模：與三分之四前視同一鏡頭，只看造型與比例。",
            "wire": "線框：同一鏡頭顯示 255 個部件的實際佈線。"}
TURN = dict(loc=(0.0, -70.0, 20.0), target=(0.0, 0.0, 15.8), lens=38)


def render_wire():
    """Same as C.wire_pass but with use_even_offset off: on this model's thin/degenerate faces the even-offset
    corners shoot out as long spikes across the frame."""
    ref = next(s for s in SHOTS if s.name == "s1")
    # dark body: against this bright sky, pale lines on a pale clay body were hard to read
    saved = C.clay_pass("#1c2229", "#4a4b4d", "WIREBODY")
    wm = C.material("emissive", "WIRE_mat", color="#d8f3ff", strength=2.0, base="#d8f3ff")
    th = max(model.bounds[1] - model.bounds[0]) * 0.0005
    copies = []
    for o in model.objs:
        if o.type != "MESH":
            continue
        c = o.copy(); C.link(c); c.parent = o.parent; c.matrix_world = o.matrix_world.copy()
        md = c.modifiers.new("wire", "WIREFRAME")
        md.thickness = th; md.use_replace = True; md.use_even_offset = False; md.offset = 0.0; md.use_boundary = True
        c.data = o.data.copy(); c.data.materials.clear(); c.data.materials.append(wm)
        C.tag(c, "wire"); copies.append(c)
    C.render_shot(C.Shot("wire", ref.cam, kind="still", exposure=ref.exposure), args,
                  os.path.join(C.out_dir(args, "airship"), "wire.jpg"))
    C.end_wire((saved, copies))


want_wire = C.wanted(args, "wire")
args.only = [n for n in (args.only or [s.name for s in SHOTS] + ["clay"]) if n != "wire"] or ["-"]
C.run(args, "airship", model, SHOTS, clay_wire_of="s1", turn=TURN, turn_mode="model", captions_extra=CAPTIONS)
if want_wire:
    render_wire()
