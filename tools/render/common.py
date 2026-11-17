"""Shared offline-render kit for the portfolio (Blender 5.3, run headless).

A scene script (tools/render/scene_<key>.py) does:

    import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import common as C
    args = C.parse_args()                      # --quality draft|final  --only hero,s1  --turn  --out DIR
    C.reset()
    model = C.load("ship", size=12.0)          # palette materials, centred, base on z=0, parented to model.pivot
    C.apply_looks(model.objs, {"ship_hull": ("painted", dict(color="#d8d3c3"))})
    ... build the set with C.box / C.floor / C.pipe / C.cable / C.text / C.area / C.spot / C.haze ...
    shots = [C.Shot("hero", cam=dict(loc=..., target=..., lens=35, fstop=2.8), kind="hero", caption="...")]
    C.run(args, "ship", model, shots, clay_wire_of="s1", turn=dict(loc=..., target=..., lens=40))

See README.md in this folder for the output contract and measured times.
"""
import bpy, bmesh, sys, os, math, json, time, argparse
import numpy as np
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
ROOT = os.path.dirname(TOOLS)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
import modellib as ML  # noqa: E402

RENDERS = os.path.join(ROOT, "site", "renders")
FONT_TC = r"C:\Windows\Fonts\msjhbd.ttc"     # Microsoft JhengHei Bold (Traditional Chinese)
FONT_LATIN = r"C:\Windows\Fonts\arialbd.ttf"
FONT_STENCIL = r"C:\Windows\Fonts\impact.ttf"

# resolution / samples per shot kind
QUALITY = {
    "final": {"hero": (1920, 1080, 128), "card": (1200, 900, 96), "still": (1600, 900, 96), "turn": (1280, 720, 48)},
    "draft": {"hero": (640, 360, 24), "card": (640, 480, 24), "still": (640, 360, 24), "turn": (640, 360, 12)},
}


def log(*a):
    print("[render]", *a, flush=True)


# ====================================================================== CLI
def parse_args(argv=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--quality", choices=["draft", "final"], default="draft")
    p.add_argument("--only", default="", help="comma list of shot names (hero,card,s1..,clay,wire,turn)")
    p.add_argument("--turn", action="store_true", help="also render the turntable")
    p.add_argument("--frames", type=int, default=24)
    p.add_argument("--out", default="", help="output dir (default site/renders/<key>)")
    p.add_argument("--samples", type=int, default=0, help="override samples for every still")
    p.add_argument("--no-json", action="store_true")
    a = p.parse_args(argv)
    a.only = [s.strip() for s in a.only.split(",") if s.strip()]
    return a


def wanted(args, name):
    if name == "turn":
        return args.turn or "turn" in args.only
    return not args.only or name in args.only


# ====================================================================== scene basics
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ML.reset_materials()
    _cache.clear()
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    return sc


def col(c, alpha=None):
    """'#rrggbb' (sRGB) or (r,g,b) linear -> linear RGBA tuple."""
    if isinstance(c, str):
        rgb = ML.hexrgb(c)
    else:
        rgb = tuple(c[:3])
    return (*rgb, 1.0 if alpha is None else alpha)


def kelvin(k):
    """Approximate black-body colour (linear RGB) for a colour temperature in K."""
    t = k / 100.0
    if t <= 66:
        r = 255; g = 99.4708025861 * math.log(t) - 161.1195681661
        b = 0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307
    else:
        r = 329.698727446 * ((t - 60) ** -0.1332047592); g = 288.1221695283 * ((t - 60) ** -0.0755148492); b = 255
    s = [min(max(v, 0), 255) / 255 for v in (r, g, b)]
    return tuple(ML.lin(v) for v in s)


def tag(o, role):
    """role: 'model' | 'set' | 'light' | 'keep' (emitters that clay/wire passes must not touch) | 'fx'."""
    o["role"] = role
    return o


def link(o, coll=None):
    (coll or bpy.context.scene.collection).objects.link(o)
    return o


# ====================================================================== render setup
def setup_cycles(samples, quality="final"):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02 if quality == "final" else 0.06
    cy.use_denoising = True
    try:
        cy.denoiser = "OPENIMAGEDENOISE"
        cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
        cy.denoising_prefilter = "ACCURATE"
    except Exception as e:
        log("denoise opt", e)
    cy.max_bounces = 8; cy.diffuse_bounces = 3; cy.glossy_bounces = 4
    cy.transmission_bounces = 8; cy.transparent_max_bounces = 8; cy.volume_bounces = 0
    cy.caustics_reflective = False; cy.caustics_refractive = False
    cy.sample_clamp_direct = 0; cy.sample_clamp_indirect = 8
    cy.volume_step_rate = 2.0; cy.volume_max_steps = 256
    try:
        cy.blur_glossy = 1.0
    except Exception:
        pass
    sc.render.use_persistent_data = True


def setup_eevee(samples):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    ee = sc.eevee
    ee.taa_render_samples = samples
    for k, v in (("use_raytracing", True), ("use_shadows", True), ("use_volumetric_shadows", True),
                 ("volumetric_end", 120.0), ("volumetric_tile_size", "4"), ("volumetric_samples", 64),
                 ("use_fast_gi", True), ("shadow_ray_count", 2), ("shadow_step_count", 8),
                 ("clamp_surface_indirect", 10.0)):
        try:
            setattr(ee, k, v)
        except Exception as e:
            log("eevee opt", k, e)
    try:
        ee.ray_tracing_options.resolution_scale = "2"
        ee.ray_tracing_options.use_denoise = True
    except Exception:
        pass


def color_look(look="AgX - Punchy", exposure=0.0, gamma=1.0):
    vs = bpy.context.scene.view_settings
    vs.view_transform = "AgX"
    for name in (look, "AgX - Medium High Contrast", "AgX - High Contrast", "None"):
        try:
            vs.look = name; break
        except Exception:
            continue
    vs.exposure = exposure; vs.gamma = gamma


def set_output(path, w, h, fmt="JPEG", quality=90):
    r = bpy.context.scene.render
    r.resolution_x = w; r.resolution_y = h; r.resolution_percentage = 100
    ims = r.image_settings
    try:
        ims.media_type = "IMAGE"
    except Exception:
        pass
    ims.file_format = fmt
    if fmt == "JPEG":
        ims.quality = quality
        ims.color_mode = "RGB"
    r.filepath = path
    os.makedirs(os.path.dirname(path), exist_ok=True)


# ====================================================================== node helpers
def _sock_set(sock, v):
    if isinstance(v, bpy.types.NodeSocket):
        sock.node.id_data.links.new(v, sock)
        return
    if sock.type == "RGBA" and isinstance(v, (str, tuple, list)):
        v = col(v) if isinstance(v, str) or len(v) == 3 else tuple(v)
    sock.default_value = v


def N(nt, kind, inputs=None, **props):
    """Create node `Shader<kind>` (e.g. 'NodeTexNoise' or full 'ShaderNodeTexNoise'); set props and inputs.
    inputs: {name_or_index: value | socket}."""
    nd = nt.nodes.new(kind if kind.startswith(("ShaderNode", "NodeReroute")) else "ShaderNode" + kind)
    for k, v in props.items():
        setattr(nd, k, v)
    for k, v in (inputs or {}).items():
        _sock_set(nd.inputs[k], v)
    return nd


def mathn(nt, op, a, b=None, clamp=False):
    nd = N(nt, "Math", operation=op, use_clamp=clamp)
    _sock_set(nd.inputs[0], a)
    if b is not None:
        _sock_set(nd.inputs[1], b)
    return nd.outputs[0]


def vmath(nt, op, a, b=None, out=0):
    nd = N(nt, "VectorMath", operation=op)
    _sock_set(nd.inputs[0], a)
    if b is not None:
        _sock_set(nd.inputs[1], b)
    return nd.outputs[out]


def mix(nt, fac, a, b, blend="MIX", clamp=True):
    """Colour mix (ShaderNodeMix RGBA): inputs 0=Factor, 6=A, 7=B; output 2."""
    nd = N(nt, "Mix", data_type="RGBA", blend_type=blend, clamp_result=clamp)
    _sock_set(nd.inputs[0], fac); _sock_set(nd.inputs[6], a); _sock_set(nd.inputs[7], b)
    return nd.outputs[2]


def mixf(nt, fac, a, b):
    nd = N(nt, "Mix", data_type="FLOAT")
    _sock_set(nd.inputs[0], fac); _sock_set(nd.inputs[2], a); _sock_set(nd.inputs[3], b)
    return nd.outputs[0]


def maprange(nt, v, a, b, c=0.0, d=1.0, interp="LINEAR"):
    nd = N(nt, "MapRange", interpolation_type=interp, clamp=True)
    _sock_set(nd.inputs[0], v)
    nd.inputs[1].default_value = a; nd.inputs[2].default_value = b
    nd.inputs[3].default_value = c; nd.inputs[4].default_value = d
    return nd.outputs[0]


def coords(nt, space="object", scale=1.0):
    """Texture coordinates in metres: 'object' (sticks to model; model data is baked in metres)
    or 'world' (Geometry.Position, for set pieces)."""
    if space == "world":
        v = N(nt, "NewGeometry").outputs["Position"]
    else:
        v = N(nt, "TexCoord").outputs["Object"]
    if scale != 1.0:
        v = vmath(nt, "SCALE", v)
        v.node.inputs[3].default_value = scale
    return v


def noise(nt, vec, scale, detail=4.0, rough=0.55, distortion=0.0, out="Factor"):
    nd = N(nt, "TexNoise", {"Vector": vec, "Scale": scale, "Detail": detail, "Roughness": rough, "Distortion": distortion})
    return nd.outputs[out]


def new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out


def principled(nt, out, **inputs):
    b = N(nt, "BsdfPrincipled")
    names = {"color": "Base Color", "metal": "Metallic", "rough": "Roughness", "normal": "Normal", "ior": "IOR",
             "alpha": "Alpha", "coat": "Coat Weight", "coat_rough": "Coat Roughness", "sheen": "Sheen Weight",
             "sheen_tint": "Sheen Tint", "sss": "Subsurface Weight", "sss_radius": "Subsurface Radius",
             "sss_scale": "Subsurface Scale", "aniso": "Anisotropic", "aniso_rot": "Anisotropic Rotation",
             "spec": "Specular IOR Level", "transmission": "Transmission Weight", "emit": "Emission Color",
             "emit_strength": "Emission Strength", "coat_normal": "Coat Normal", "tangent": "Tangent",
             "coat_tint": "Coat Tint", "sheen_rough": "Sheen Roughness"}
    for k, v in inputs.items():
        if v is None:
            continue
        _sock_set(b.inputs[names.get(k, k)], v)
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return b


def bump(nt, height, strength=0.3, distance=0.01, normal=None):
    nd = N(nt, "Bump", {"Height": height, "Strength": strength, "Distance": distance})
    if normal is not None:
        _sock_set(nd.inputs["Normal"], normal)
    return nd.outputs[0]


def edge_mask(nt, radius=0.012, lo=0.995, hi=0.93):
    """Convex/concave edge mask from the Bevel node (Cycles; EEVEE returns ~0 = no wear)."""
    bev = N(nt, "Bevel", {"Radius": radius}, samples=4)
    geo = N(nt, "NewGeometry")
    d = vmath(nt, "DOT_PRODUCT", bev.outputs[0], geo.outputs["Normal"], out=1)
    return maprange(nt, d, lo, hi, 0.0, 1.0)


def cavity_mask(nt, distance=0.25, contrast=1.5):
    ao = N(nt, "AmbientOcclusion", {"Distance": distance}, samples=8, only_local=True)
    inv = mathn(nt, "SUBTRACT", 1.0, ao.outputs["AO"], clamp=True)
    return mathn(nt, "POWER", inv, 1.0 / contrast)


def panel_grid(nt, vec, size=(1.2, 1.6, 0.9), width=0.012):
    """Procedural panel seams on any surface, no UVs. Returns (seam 0..1, per-panel random 0..1).
    Grid planes of each axis are only drawn on faces whose normal is NOT along that axis (tri-planar)."""
    inv = vmath(nt, "MULTIPLY", vec, (1.0 / size[0], 1.0 / size[1], 1.0 / size[2]))
    fr = vmath(nt, "FRACTION", inv)
    dd = vmath(nt, "ABSOLUTE", vmath(nt, "SUBTRACT", fr, (0.5, 0.5, 0.5)))
    sep = N(nt, "SeparateXYZ", {"Vector": dd})
    nrm = N(nt, "SeparateXYZ", {"Vector": vmath(nt, "ABSOLUTE", N(nt, "NewGeometry").outputs["Normal"])})
    seam = None
    for i in range(3):
        w = width / size[i]
        line = maprange(nt, sep.outputs[i], 0.5 - w, 0.5 - w * 0.4, 0.0, 1.0)        # 1 on the seam
        wt = maprange(nt, nrm.outputs[i], 0.92, 0.6, 0.0, 1.0)                          # 0 when facing this axis
        li = mathn(nt, "MULTIPLY", line, wt)
        seam = li if seam is None else mathn(nt, "MAXIMUM", seam, li)
    cell = vmath(nt, "FLOOR", inv)
    rnd = N(nt, "TexWhiteNoise", {"Vector": cell}, noise_dimensions="3D").outputs["Value"]
    return seam, rnd


# ====================================================================== material recipes
_cache = {}


def painted(name, color="#cfcbbb", rough=0.42, metal=0.0, grime=0.5, wear=0.35, panels=(1.2, 1.6, 0.9),
            seam_width=0.01, grime_color="#2a241c", under="#8c8f93", tint_var=0.06, space="object",
            streaks=0.5, scale=1.0, coat=0.0, **_):
    """Painted metal: per-panel tint variation, dark seams, cavity grime (AO), vertical streaks,
    roughness breakup, bare-metal edge wear (Bevel)."""
    m, nt, out = new_mat(name)
    v = coords(nt, space, 1.0 / scale)
    base = col(color)
    color_sock = N(nt, "RGB").outputs[0]; color_sock.default_value = base
    shade = color_sock
    rnd = None
    if panels:
        seam, rnd = panel_grid(nt, v, panels, seam_width)
        # per-panel tint (+-tint_var)
        tv = maprange(nt, rnd, 0, 1, 1 - tint_var, 1 + tint_var)
        shade = mix(nt, 1.0, shade, N(nt, "CombineXYZ", {"X": tv, "Y": tv, "Z": tv}).outputs[0], blend="MULTIPLY")
    n_big = noise(nt, v, 0.9, 6, 0.6)
    n_fine = noise(nt, v, 9.0, 8, 0.65)
    # streaks: noise stretched along Z
    st = vmath(nt, "MULTIPLY", v, (6.0, 6.0, 0.35))
    n_str = noise(nt, st, 1.0, 4, 0.5)
    g = mathn(nt, "MULTIPLY", cavity_mask(nt, 0.35 * scale), 1.4, clamp=True)
    g = mathn(nt, "MAXIMUM", g, mathn(nt, "MULTIPLY", maprange(nt, n_big, 0.48, 0.75), 0.6))
    g = mathn(nt, "MAXIMUM", g, mathn(nt, "MULTIPLY", maprange(nt, n_str, 0.5, 0.8), streaks))
    if panels:
        g = mathn(nt, "MAXIMUM", g, mathn(nt, "MULTIPLY", seam, 0.85))
    g = mathn(nt, "MULTIPLY", g, grime, clamp=True)
    shade = mix(nt, g, shade, grime_color)
    # edge wear -> bare metal
    e = edge_mask(nt, 0.01 * scale)
    wmask = mathn(nt, "MULTIPLY", e, maprange(nt, n_fine, 0.35, 0.6), clamp=True)
    wmask = mathn(nt, "MULTIPLY", wmask, wear * 2.0, clamp=True)
    shade = mix(nt, wmask, shade, under)
    r = maprange(nt, n_fine, 0.3, 0.7, rough - 0.08, rough + 0.1)
    r = mixf(nt, g, r, min(rough + 0.25, 0.9))
    r = mixf(nt, wmask, r, 0.28)
    mt = mixf(nt, wmask, metal, 1.0)
    h = mathn(nt, "MULTIPLY", n_fine, 0.15)
    if panels:
        h = mathn(nt, "SUBTRACT", h, seam)
    nrm = bump(nt, h, 0.35, 0.004 * scale)
    principled(nt, out, color=shade, metal=mt, rough=r, normal=nrm, coat=coat, coat_rough=0.2)
    return m


def metal(name, color="#8a9097", rough=0.3, brushed=0.0, grime=0.25, space="object", scale=1.0, axis="Z", **_):
    """Bare metal with roughness breakup; brushed>0 adds anisotropy + streaked roughness."""
    m, nt, out = new_mat(name)
    v = coords(nt, space, 1.0 / scale)
    stretch = {"X": (0.02, 1, 1), "Y": (1, 0.02, 1), "Z": (1, 1, 0.02)}[axis]
    n_fine = noise(nt, v, 14.0, 6, 0.6)
    n_br = noise(nt, vmath(nt, "MULTIPLY", v, tuple(s * 40 for s in stretch)), 1.0, 2, 0.5)
    n_big = noise(nt, v, 1.2, 5, 0.6)
    r = maprange(nt, n_fine, 0.3, 0.7, rough * 0.75, rough * 1.3)
    if brushed:
        r = mixf(nt, brushed, r, maprange(nt, n_br, 0.3, 0.7, rough * 0.6, rough * 1.5))
    shade = mix(nt, mathn(nt, "MULTIPLY", maprange(nt, n_big, 0.45, 0.75), grime), col(color), "#2a2722")
    shade = mix(nt, mathn(nt, "MULTIPLY", cavity_mask(nt, 0.2 * scale), grime * 1.5, clamp=True), shade, "#1d1b18")
    nrm = bump(nt, n_fine, 0.08, 0.002)
    principled(nt, out, color=shade, metal=1.0, rough=r, aniso=brushed * 0.7, normal=nrm)
    return m


def rubber(name, color="#18181a", rough=0.82, space="object", **_):
    m, nt, out = new_mat(name)
    v = coords(nt, space)
    n = noise(nt, v, 30.0, 4, 0.6)
    principled(nt, out, color=mix(nt, maprange(nt, n, 0.3, 0.7, 0, 0.35), col(color), "#2b2a28"),
               rough=maprange(nt, n, 0.3, 0.7, rough - 0.1, rough + 0.1), spec=0.35,
               normal=bump(nt, n, 0.25, 0.002))
    return m


def plastic(name, color="#3a3f46", rough=0.38, coat=0.0, space="object", **_):
    m, nt, out = new_mat(name)
    v = coords(nt, space)
    n = noise(nt, v, 20.0, 5, 0.6)
    principled(nt, out, color=col(color), rough=maprange(nt, n, 0.3, 0.7, rough - 0.07, rough + 0.08),
               coat=coat, coat_rough=0.08, normal=bump(nt, n, 0.05, 0.002))
    return m


def glass(name, color="#bfe9e4", rough=0.02, ior=1.45, tint=1.0, **_):
    """Real transmission (Cycles refraction; EEVEE raytraced refraction)."""
    m, nt, out = new_mat(name)
    principled(nt, out, color=col(color), rough=rough, ior=ior, transmission=1.0, metal=0.0)
    for k, v in (("use_raytrace_refraction", True), ("use_screen_refraction", True), ("surface_render_method", "DITHERED")):
        try:
            setattr(m, k, v)
        except Exception:
            pass
    return m


def tinted_glass(name, color="#0d2a2c", rough=0.04, glow="#2ad0c0", glow_strength=0.0, **_):
    """Opaque dark visor/canopy glass: deep tinted base + clear coat reflections (no see-through)."""
    m, nt, out = new_mat(name)
    v = coords(nt)
    n = noise(nt, v, 3.0, 3, 0.5)
    fres = N(nt, "LayerWeight", {"Blend": 0.35}).outputs["Facing"]
    base = mix(nt, mathn(nt, "MULTIPLY", fres, 0.6), col(color), "#000000")
    principled(nt, out, color=base, metal=0.0, rough=maprange(nt, n, 0.3, 0.7, rough * 0.6, rough * 2.0),
               coat=1.0, coat_rough=0.02, spec=1.0, emit=glow, emit_strength=glow_strength)
    return m


def emissive(name, color="#ffb35a", strength=8.0, base="#1a1a1a", **_):
    m, nt, out = new_mat(name)
    principled(nt, out, color=col(base), rough=0.35, emit=col(color), emit_strength=strength)
    return m


def screen(name, color="#35c9ff", strength=3.0, lines=180.0, **_):
    """Emissive screen with scanlines and slight flicker noise, glossy glass on top."""
    m, nt, out = new_mat(name)
    v = coords(nt)
    w = N(nt, "TexWave", {"Vector": v, "Scale": lines, "Distortion": 0.0}, wave_type="BANDS", bands_direction="Z")
    n = noise(nt, v, 4.0, 2, 0.5)
    k = mathn(nt, "MULTIPLY", maprange(nt, w.outputs["Factor"], 0, 1, 0.55, 1.0), maprange(nt, n, 0.3, 0.7, 0.8, 1.1))
    s = mathn(nt, "MULTIPLY", k, strength)
    principled(nt, out, color="#020304", rough=0.06, coat=1.0, coat_rough=0.03, emit=col(color), emit_strength=s)
    return m


def wood(name, color="#7a4a32", color2=None, rough=0.5, grain=6.0, axis="X", coat=0.3, space="object", **_):
    m, nt, out = new_mat(name)
    v = coords(nt, space)
    c2 = color2 or tuple(x * 0.55 for x in col(color)[:3])
    st = {"X": (0.15, 1, 1), "Y": (1, 0.15, 1), "Z": (1, 1, 0.15)}[axis]
    vv = vmath(nt, "MULTIPLY", v, st)
    w = N(nt, "TexWave", {"Vector": vv, "Scale": grain, "Distortion": 6.0, "Detail": 3.0, "Detail Scale": 1.5},
          wave_type="RINGS", rings_direction="SPHERICAL")
    n = noise(nt, vv, 25.0, 6, 0.6)
    g = mathn(nt, "MULTIPLY", w.outputs["Factor"], maprange(nt, n, 0.2, 0.8, 0.7, 1.2), clamp=True)
    shade = mix(nt, g, col(color), c2)
    principled(nt, out, color=shade, rough=maprange(nt, g, 0, 1, rough - 0.1, rough + 0.12), coat=coat, coat_rough=0.25,
               normal=bump(nt, g, 0.15, 0.002))
    return m


def fabric(name, color="#5d5a36", rough=0.85, weave=220.0, sheen=0.6, space="object", **_):
    m, nt, out = new_mat(name)
    v = coords(nt, space)
    a = N(nt, "TexWave", {"Vector": v, "Scale": weave}, wave_type="BANDS", bands_direction="X", wave_profile="SIN").outputs["Factor"]
    b = N(nt, "TexWave", {"Vector": v, "Scale": weave}, wave_type="BANDS", bands_direction="Z", wave_profile="SIN").outputs["Factor"]
    c = N(nt, "TexWave", {"Vector": v, "Scale": weave}, wave_type="BANDS", bands_direction="Y", wave_profile="SIN").outputs["Factor"]
    h = mathn(nt, "MAXIMUM", mathn(nt, "MULTIPLY", a, b), mathn(nt, "MULTIPLY", c, b))
    n = noise(nt, v, 3.0, 5, 0.6)
    shade = mix(nt, maprange(nt, n, 0.35, 0.7, 0.0, 0.25), col(color), "#151311")
    principled(nt, out, color=shade, rough=rough, sheen=sheen, sheen_rough=0.4, spec=0.3,
               normal=bump(nt, h, 0.25, 0.001))
    return m


def leather(name, color="#3a2419", rough=0.48, space="object", **_):
    m, nt, out = new_mat(name)
    v = coords(nt, space)
    vor = N(nt, "TexVoronoi", {"Vector": v, "Scale": 180.0}, feature="F1").outputs["Distance"]
    n = noise(nt, v, 4.0, 6, 0.6)
    shade = mix(nt, maprange(nt, n, 0.35, 0.7, 0, 0.4), col(color), tuple(x * 0.5 for x in col(color)[:3]))
    principled(nt, out, color=shade, rough=maprange(nt, n, 0.3, 0.7, rough - 0.12, rough + 0.12), coat=0.25, coat_rough=0.3,
               normal=bump(nt, vor, 0.25, 0.0008))
    return m


def skin(name, color="#b67a58", rough=0.45, sss=0.25, **_):
    m, nt, out = new_mat(name)
    v = coords(nt)
    n = noise(nt, v, 60.0, 6, 0.6)
    blot = noise(nt, v, 6.0, 3, 0.5)
    shade = mix(nt, maprange(nt, blot, 0.4, 0.7, 0, 0.18), col(color), "#9b4a3a")
    principled(nt, out, color=shade, rough=maprange(nt, n, 0.3, 0.7, rough - 0.08, rough + 0.08), sss=sss,
               sss_radius=(1.0, 0.35, 0.18), sss_scale=0.015, spec=0.5, normal=bump(nt, n, 0.08, 0.0005))
    return m


def hair(name, color="#1c1411", rough=0.32, **_):
    m, nt, out = new_mat(name)
    v = coords(nt)
    st = noise(nt, vmath(nt, "MULTIPLY", v, (60.0, 60.0, 4.0)), 1.0, 3, 0.5)
    shade = mix(nt, maprange(nt, st, 0.35, 0.7, 0, 0.5), col(color), tuple(min(1, x * 2.2) for x in col(color)[:3]))
    principled(nt, out, color=shade, rough=rough, aniso=0.8, sheen=0.3, normal=bump(nt, st, 0.3, 0.001))
    return m


def concrete(name, color="#3a3c3e", wet=0.6, rough=0.62, joints=4.0, scale=1.0, **_):
    """Polished/wet concrete floor (world space): puddles (low roughness, darker), slab joints, stains."""
    m, nt, out = new_mat(name)
    v = coords(nt, "world", 1.0 / scale)
    n_big = noise(nt, v, 0.08, 5, 0.6)
    n_mid = noise(nt, v, 0.7, 6, 0.6)
    n_fine = noise(nt, v, 30.0, 4, 0.6)
    puddle = mathn(nt, "MULTIPLY", maprange(nt, n_big, 0.46, 0.56), wet, clamp=True)
    shade = mix(nt, maprange(nt, n_mid, 0.3, 0.75, 0, 0.5), col(color), "#151617")
    shade = mix(nt, mathn(nt, "MULTIPLY", puddle, 0.45), shade, "#0d0e0f")
    if joints:
        seam, rnd = panel_grid(nt, v, (joints, joints, 1000.0), 0.015)
        shade = mix(nt, mathn(nt, "MULTIPLY", rnd, 0.12), shade, "#202224")
        shade = mix(nt, mathn(nt, "MULTIPLY", seam, 0.8), shade, "#080808")
    r = maprange(nt, n_fine, 0.3, 0.7, rough - 0.1, rough + 0.1)
    r = mixf(nt, puddle, r, 0.03)
    h = mathn(nt, "MULTIPLY", n_fine, mathn(nt, "SUBTRACT", 1.0, puddle))
    principled(nt, out, color=shade, rough=r, spec=0.5, normal=bump(nt, h, 0.12, 0.002))
    m["wet_mask"] = True
    return m


def floor_paint(name, color="#d9a21b", wet=0.6, wear=0.5, **_):
    """Painted floor markings that share the floor's puddle mask (world space) and get scuffed."""
    m, nt, out = new_mat(name)
    v = coords(nt, "world")
    n_big = noise(nt, v, 0.08, 5, 0.6)
    n_scuff = noise(nt, v, 3.5, 8, 0.7)
    puddle = mathn(nt, "MULTIPLY", maprange(nt, n_big, 0.46, 0.56), wet, clamp=True)
    sc = mathn(nt, "MULTIPLY", maprange(nt, n_scuff, 0.42, 0.62), wear, clamp=True)
    shade = mix(nt, sc, col(color), "#2c2d2e")
    shade = mix(nt, mathn(nt, "MULTIPLY", puddle, 0.3), shade, "#0f0f10")
    r = mixf(nt, puddle, maprange(nt, n_scuff, 0.3, 0.7, 0.45, 0.65), 0.04)
    principled(nt, out, color=shade, rough=r, normal=bump(nt, n_scuff, 0.1, 0.001))
    return m


def clay(name, color="#b9b4ab", rough=0.6, **_):
    m, nt, out = new_mat(name)
    principled(nt, out, color=col(color), rough=rough, spec=0.35)
    return m


def flat(name, color="#808080", metal=0.0, rough=0.5, **_):
    m, nt, out = new_mat(name)
    principled(nt, out, color=col(color), rough=rough, metal=metal)
    return m


RECIPES = {"painted": painted, "metal": metal, "rubber": rubber, "plastic": plastic, "glass": glass,
           "tinted_glass": tinted_glass, "emissive": emissive, "screen": screen, "wood": wood, "fabric": fabric,
           "leather": leather, "skin": skin, "hair": hair, "concrete": concrete, "floor_paint": floor_paint,
           "clay": clay, "flat": flat}


def material(recipe, name=None, **kw):
    """Build (cached by name) a material from a recipe. Returns bpy Material."""
    nm = name or (recipe + "_" + str(abs(hash(json.dumps(kw, sort_keys=True, default=str))) % 10 ** 6))
    m = _cache.get(nm)
    if m is not None:
        return m
    m = RECIPES[recipe](nm, **kw)
    m["recipe"] = recipe
    _cache[nm] = m
    return m


def auto_recipe(pal_name):
    """Reasonable default look derived from a modellib.PAL entry (used for unmapped palette names)."""
    hx, metal_, rough, em, es, alpha = ML.PAL[pal_name]
    if alpha < 1:
        return ("glass", dict(color=hx))
    if em and es >= 1.0:
        return ("emissive", dict(color=em, strength=es * 4, base=hx))
    if metal_ >= 0.85:
        return ("metal", dict(color=hx, rough=rough))
    if metal_ >= 0.2:
        return ("painted", dict(color=hx, rough=rough, metal=0.0))
    return ("plastic", dict(color=hx, rough=rough))


def palette_of(m):
    if m is None:
        return None
    return m.get("palette") or ML.base(m.name)


def apply_looks(objs, mapping=None, auto=True):
    """Replace palette materials by rich recipe materials.
    mapping: {palette_name: (recipe, {kwargs})  |  bpy Material}. Unlisted palette names use auto_recipe()
    (if auto) or stay as they are."""
    mapping = mapping or {}
    for o in objs:
        if o.type not in ("MESH", "CURVE", "FONT"):
            continue
        for s in o.material_slots:
            pn = palette_of(s.material)
            if pn is None:
                continue
            spec = mapping.get(pn)
            if spec is None:
                if not auto or pn not in ML.PAL:
                    continue
                spec = auto_recipe(pn)
            m = spec if isinstance(spec, bpy.types.Material) else material(spec[0], "look_" + pn, **spec[1])
            m["palette"] = pn
            s.link = "DATA"
            s.material = m


def assign(o, m):
    """Single material on an object (Material or (recipe, kwargs))."""
    if isinstance(m, tuple):
        m = material(m[0], **m[1])
    me = o.data
    me.materials.clear(); me.materials.append(m)
    return o


# ====================================================================== model
class Model:
    def __init__(self, key, objs, pivot):
        self.key = key; self.objs = objs; self.pivot = pivot

    @property
    def bounds(self):
        return ML.bounds(self.objs)

    def by_name(self, name):
        return next((o for o in self.objs if o.name == name), None)


def load(key, size=None, scale=None, rot_z=0.0, location=(0, 0, 0), ground=None):
    """Import model `key`, palette materials, bake: rotate about Z (deg), centre XY, base on z=0,
    then scale (longest side = size, or uniform scale). ground: optional list of object names whose
    lowest vertex defines the floor contact (e.g. landing gear) instead of the overall minimum.
    All objects are parented to an Empty `pivot` at `location` (rotate it for turntables)."""
    objs = ML.load_model(key)
    if rot_z:
        ML.transform(objs, Matrix.Rotation(math.radians(rot_z), 4, "Z"))
    mn, mx = ML.bounds(objs)
    gz = mn.z
    if ground:
        gmn, _ = ML.bounds([o for o in objs if o.name in ground])
        gz = gmn.z
    s = scale or (size / max(mx - mn) if size else 1.0)
    T = Matrix.Scale(s, 4) @ Matrix.Translation(Vector((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -gz)))
    ML.transform(objs, T)
    pivot = bpy.data.objects.new(key + "_pivot", None)
    link(pivot); pivot.location = location
    for o in objs:
        o.parent = pivot
        tag(o, "model")
        o.data.shade_smooth() if False else None
    bpy.context.view_layer.update()
    log(f"model {key}: {len(objs)} objs, scale {s:.3f}, dims {[round(x, 2) for x in (mx - mn) * s]}")
    return Model(key, objs, pivot)


# ====================================================================== set building
def _obj_from_bm(name, bm, mat=None, loc=(0, 0, 0), rot=(0, 0, 0), role="set", smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    if smooth:
        me.shade_smooth()
    o = bpy.data.objects.new(name, me)
    link(o)
    o.location = loc; o.rotation_euler = Euler([math.radians(a) for a in rot])
    if mat is not None:
        assign(o, mat)
    return tag(o, role)


def box(name, size, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, bevel=0.02, role="set", origin="center"):
    """Box with real dimensions baked into the mesh (so object-space textures are in metres).
    origin: 'center' or 'bottom' (loc is the centre of the bottom face)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if origin == "bottom":
        bmesh.ops.translate(bm, vec=Vector((0, 0, size[2] / 2)), verts=bm.verts)
    if bevel:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(bevel, min(size) * 0.45), segments=2, affect="EDGES",
                        profile=0.5)
    o = _obj_from_bm(name, bm, mat, loc, rot, role)
    _autosmooth(o)
    return o


def _autosmooth(o, angle=35):
    try:
        o.data.shade_smooth()
        md = o.modifiers.new("smooth", "NODES")  # placeholder replaced below if the asset exists
        o.modifiers.remove(md)
    except Exception:
        pass
    try:
        with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], selected_editable_objects=[o]):
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))
    except Exception as e:
        log("autosmooth", e)


def cylinder(name, radius, depth, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, segments=32, role="set", origin="center"):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=radius, radius2=radius, depth=depth)
    if origin == "bottom":
        bmesh.ops.translate(bm, vec=Vector((0, 0, depth / 2)), verts=bm.verts)
    o = _obj_from_bm(name, bm, mat, loc, rot, role)
    _autosmooth(o)
    return o


def plane(name, size, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, role="set"):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bmesh.ops.scale(bm, vec=Vector((size[0], size[1], 1)), verts=bm.verts)
    return _obj_from_bm(name, bm, mat, loc, rot, role)


def floor(size=80.0, mat=None, name="floor"):
    return plane(name, (size, size), (0, 0, 0), mat=mat)


def pipe(name, p0, p1, radius=0.05, mat=None, segments=16, role="set"):
    """Straight cylinder between two points."""
    p0 = Vector(p0); p1 = Vector(p1); d = p1 - p0
    o = cylinder(name, radius, d.length, mat=mat, segments=segments, role=role)
    o.location = (p0 + p1) / 2
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return o


def cable(name, points, radius=0.04, mat=None, resolution=12, role="set"):
    """Smooth tube (bezier curve with bevel) through points [(x,y,z), ...]."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"; cu.bevel_depth = radius; cu.bevel_resolution = 4; cu.use_fill_caps = True
    cu.resolution_u = resolution
    sp = cu.splines.new("BEZIER"); sp.bezier_points.add(len(points) - 1)
    for bp, p in zip(sp.bezier_points, points):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = "AUTO"
    o = bpy.data.objects.new(name, cu); link(o)
    if mat is not None:
        m = mat if isinstance(mat, bpy.types.Material) else material(mat[0], **mat[1])
        cu.materials.append(m)
    return tag(o, role)


_fonts = {}


def font(path):
    if path not in _fonts:
        _fonts[path] = bpy.data.fonts.load(path, check_existing=True)
    return _fonts[path]


def text(name, body, size=1.0, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, fontpath=FONT_LATIN, extrude=0.0,
         align="CENTER", spacing=1.0, role="set"):
    """Text object (signage/decals). rot in degrees; (90,0,0) stands it up facing -Y; (0,0,0) lies flat."""
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body; cu.size = size; cu.extrude = extrude
    cu.font = font(fontpath); cu.align_x = align; cu.align_y = "CENTER"; cu.space_character = spacing
    o = bpy.data.objects.new(name, cu); link(o)
    o.location = loc; o.rotation_euler = Euler([math.radians(a) for a in rot])
    if mat is not None:
        m = mat if isinstance(mat, bpy.types.Material) else material(mat[0], **mat[1])
        cu.materials.append(m)
    return tag(o, role)


def look_at(o, target, roll=0.0):
    d = Vector(target) - o.location
    q = d.to_track_quat("-Z", "Y")
    o.rotation_euler = q.to_euler()
    if roll:
        o.rotation_euler.rotate_axis("Z", math.radians(roll))
    return o


def _light(name, kind, loc, power, color, target=None):
    L = bpy.data.lights.new(name, kind)
    L.energy = power
    L.color = col(color)[:3] if isinstance(color, str) else tuple(color[:3])
    o = bpy.data.objects.new(name, L); link(o); o.location = loc
    if target is not None:
        look_at(o, target)
    return tag(o, "light")


def area(name, loc, target, power=500.0, color=(1, 1, 1), size=2.0, size_y=None, spread=180.0, visible=False):
    o = _light(name, "AREA", loc, power, color, target)
    L = o.data
    L.shape = "RECTANGLE" if size_y else "SQUARE"
    L.size = size
    if size_y:
        L.size_y = size_y
    L.spread = math.radians(spread)
    o.visible_camera = visible
    return o


def spot(name, loc, target, power=1000.0, color=(1, 1, 1), angle=45.0, blend=0.3, radius=0.1, volume=1.0):
    o = _light(name, "SPOT", loc, power, color, target)
    L = o.data
    L.spot_size = math.radians(angle); L.spot_blend = blend; L.shadow_soft_size = radius
    L.volume_factor = volume
    return o


def point(name, loc, power=100.0, color=(1, 1, 1), radius=0.1, volume=1.0):
    o = _light(name, "POINT", loc, power, color)
    o.data.shadow_soft_size = radius; o.data.volume_factor = volume
    return o


def sun(name, direction, strength=3.0, color=(1, 1, 1), angle=1.0, volume=1.0):
    """direction: vector the light travels along (e.g. (0,-1,-0.3))."""
    o = _light(name, "SUN", (0, 0, 20), strength, color)
    o.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    o.data.angle = math.radians(angle); o.data.volume_factor = volume
    return o


def strip(name, p0, p1, width=0.08, color="#cfe6ff", strength=12.0, normal=(0, 0, -1), role="keep"):
    """Emissive light strip (thin box) between p0 and p1, emitting mostly along `normal`."""
    p0 = Vector(p0); p1 = Vector(p1); d = p1 - p0
    o = box(name, (width, d.length, width * 0.5), bevel=0.0, mat=material("emissive", color=color, strength=strength),
            role=role)
    o.location = (p0 + p1) / 2
    o.rotation_euler = d.to_track_quat("Y", "Z").to_euler()
    return o


def haze(name="haze", center=(0, 0, 6), size=(60, 60, 14), density=0.01, color="#c8d6dc", anisotropy=0.35):
    """Homogeneous volume box (cheap in Cycles: no ray marching for constant density)."""
    m, nt, out = new_mat(name + "_vol")
    v = N(nt, "VolumePrincipled", {"Density": density, "Color": col(color), "Anisotropy": anisotropy})
    nt.links.new(v.outputs[0], out.inputs["Volume"])
    o = box(name, size, center, bevel=0.0, mat=m, role="fx")
    o.visible_shadow = False
    return o


def world(color="#05080a", strength=1.0, horizon=None, zenith=None):
    """Simple world: flat colour, or a vertical gradient horizon->zenith."""
    w = bpy.data.worlds.new("world"); bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = N(nt, "Background", {"Strength": strength})
    if horizon and zenith:
        z = N(nt, "SeparateXYZ", {"Vector": N(nt, "TexCoord").outputs["Generated"]})
        _sock_set(bg.inputs["Color"], mix(nt, maprange(nt, z.outputs[2], 0.0, 0.6), col(horizon), col(zenith)))
    else:
        bg.inputs["Color"].default_value = col(color)
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    return w


def sky_card(name, loc, size, rot=(90, 0, 0), top="#1c4a4a", bottom="#8fe3d0", strength=3.0, clouds=0.7, scale=0.08):
    """Emissive backdrop card (storm sky seen through a door): vertical gradient + cloud noise."""
    m, nt, out = new_mat(name + "_mat")
    v = coords(nt, "world")
    z = N(nt, "SeparateXYZ", {"Vector": N(nt, "TexCoord").outputs["Generated"]}).outputs[1]
    n = noise(nt, vmath(nt, "MULTIPLY", v, (1.0, 1.0, 1.8)), scale, 8, 0.62, distortion=0.4)
    c = mix(nt, z, col(bottom), col(top))
    c = mix(nt, mathn(nt, "MULTIPLY", maprange(nt, n, 0.4, 0.7), clouds), c, "#03100f")
    em = N(nt, "Emission", {"Color": c, "Strength": strength})
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    o = plane(name, size, loc, rot, m, role="keep")
    o.visible_shadow = False
    return o


# ====================================================================== camera & shots
def camera(name, loc, target, lens=35.0, fstop=None, focus=None, shift=(0.0, 0.0), sensor=36.0, roll=0.0):
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    o = bpy.data.objects.get(name)
    if o is None:
        o = bpy.data.objects.new(name, cd); link(o)
    o.location = loc; look_at(o, target, roll)
    cd.lens = lens; cd.sensor_width = sensor; cd.shift_x, cd.shift_y = shift
    cd.clip_start = 0.05; cd.clip_end = 500
    cd.dof.use_dof = fstop is not None
    if fstop is not None:
        cd.dof.aperture_fstop = fstop
        fp = Vector(focus if focus is not None else target)
        cd.dof.focus_distance = (fp - Vector(loc)).length
    return tag(o, "camera")


class Shot:
    """name: 'hero' | 'card' | 's1'...; file defaults to name + '.jpg'; kind: hero|card|still.
    cam: kwargs for camera(); exposure: view exposure; setup/teardown: optional callables."""

    def __init__(self, name, cam, caption="", kind="still", file=None, exposure=0.0, setup=None, teardown=None,
                 samples=None):
        self.name = name; self.cam = cam; self.caption = caption; self.kind = kind
        self.file = file or (name + ".jpg"); self.exposure = exposure; self.setup = setup; self.teardown = teardown
        self.samples = samples


def out_dir(args, key):
    return os.path.abspath(args.out) if args.out else os.path.join(RENDERS, key)


def render_shot(shot, args, path, kind=None):
    sc = bpy.context.scene
    w, h, spp = QUALITY[args.quality][kind or shot.kind]
    if shot.samples and args.quality == "final":
        spp = shot.samples
    if args.samples:
        spp = args.samples
    setup_cycles(spp, args.quality)
    cam = camera("CAM_" + shot.name, **shot.cam)
    sc.camera = cam
    color_look(exposure=shot.exposure)
    set_output(path, w, h)
    if shot.setup:
        shot.setup()
    t = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t
    if shot.teardown:
        shot.teardown()
    log(f"TIME {shot.name} {args.quality} {w}x{h} {spp}spp: {dt:.1f}s -> {path}")
    return dt


# ---------------------------------------------------------------- clay / wire passes
def _swap_materials(objs, fn):
    saved = []
    for o in objs:
        if o.type not in ("MESH", "CURVE", "FONT") or not hasattr(o.data, "materials"):
            continue
        mats = list(o.data.materials)
        saved.append((o, mats))
        slots = [s.material for s in o.material_slots]
        for i, m in enumerate(slots):
            nm = fn(o, m)
            if nm is not None:
                o.material_slots[i].link = "DATA"
                o.data.materials[i] = nm
    return saved


def _restore(saved):
    for o, mats in saved:
        for i, m in enumerate(mats):
            o.data.materials[i] = m


def _is_emitter(m):
    return m is not None and m.get("recipe") in ("emissive", "screen")


def clay_pass(model_color="#bdb8ae", set_color="#4a4b4d"):
    """Swap: model -> light clay, set -> dark clay; emitters, lights, sky and haze untouched."""
    cm = material("clay", "CLAY_model", color=model_color, rough=0.55)
    cs = material("clay", "CLAY_set", color=set_color, rough=0.7)
    objs = [o for o in bpy.context.scene.objects if o.get("role") in ("model", "set")]
    return _swap_materials(objs, lambda o, m: None if _is_emitter(m) else (cm if o.get("role") == "model" else cs))


def wire_pass(model, thickness=0.006, wire_color="#d8f3ff", wire_strength=3.0, body_color="#14171b",
              set_color="#2b2c2e"):
    """True-topology wireframe: a Wireframe-modifier copy of every model mesh (uses the mesh's real edges, so
    quads stay quads — the Cycles Wireframe *node* would show the triangulation). Body = dark matte."""
    saved = clay_pass(body_color, set_color)
    wm = material("emissive", "WIRE_mat", color=wire_color, strength=wire_strength, base=wire_color)
    copies = []
    for o in model.objs:
        if o.type != "MESH":
            continue
        c = o.copy(); c.data = o.data  # share mesh; modifier output replaces it
        link(c); c.parent = o.parent; c.matrix_world = o.matrix_world.copy()
        md = c.modifiers.new("wire", "WIREFRAME")
        md.thickness = thickness; md.use_replace = True; md.use_even_offset = True; md.offset = 0.0
        md.use_boundary = True; md.material_offset = 0
        c.data = o.data.copy(); c.data.materials.clear(); c.data.materials.append(wm)
        tag(c, "wire"); copies.append(c)
    return saved, copies


def end_wire(state):
    saved, copies = state
    for c in copies:
        me = c.data
        bpy.data.objects.remove(c, do_unlink=True)
        bpy.data.meshes.remove(me)
    _restore(saved)


# ---------------------------------------------------------------- turntable
def render_turntable(args, model, cam, out, frames=24, mode="model", center=(0, 0, 0), start_deg=0.0):
    """frames JPGs out/turn/00.jpg..; EEVEE. mode 'model' rotates model.pivot, 'camera' orbits the camera
    around `center` (keeps height/distance)."""
    sc = bpy.context.scene
    w, h, spp = QUALITY[args.quality]["turn"]
    setup_eevee(spp if args.quality == "final" else 16)
    c = camera("CAM_turn", **cam); sc.camera = c
    color_look(exposure=cam.get("exposure", 0.0) if isinstance(cam, dict) and "exposure" in cam else 0.0)
    rot0 = model.pivot.rotation_euler.z
    base_loc = Vector(c.location); ctr = Vector(center)
    tgt = cam.get("target")
    t0 = time.time()
    for i in range(frames):
        a = math.radians(start_deg) + 2 * math.pi * i / frames
        if mode == "model":
            model.pivot.rotation_euler.z = rot0 + a
        else:
            rel = base_loc - ctr
            c.location = ctr + Matrix.Rotation(a, 3, "Z") @ rel
            look_at(c, tgt)
        set_output(os.path.join(out, "turn", f"{i:02d}.jpg"), w, h)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        log(f"TIME turn {i:02d} {args.quality} {w}x{h} eevee {spp}spp: {time.time() - t:.1f}s")
    model.pivot.rotation_euler.z = rot0
    log(f"TIME turn total {time.time() - t0:.1f}s")


# ---------------------------------------------------------------- driver
def run(args, key, model, shots, clay_wire_of="s1", turn=None, turn_mode="model", wire_thickness=None,
        captions_extra=None):
    """Render the shot list (respecting --only), then clay/wire (camera of `clay_wire_of`), then turntable
    (if --turn). Writes shots.json with captions for all stills (including clay/wire)."""
    out = out_dir(args, key)
    os.makedirs(out, exist_ok=True)
    times = {}
    for s in shots:
        if wanted(args, s.name):
            times[s.name] = render_shot(s, args, os.path.join(out, s.file))
    ref = next((s for s in shots if s.name == clay_wire_of), None)
    extra = captions_extra or {}
    if ref is not None:
        if wanted(args, "clay"):
            saved = clay_pass()
            sh = Shot("clay", ref.cam, kind="still", exposure=ref.exposure)
            times["clay"] = render_shot(sh, args, os.path.join(out, "clay.jpg"))
            _restore(saved)
        if wanted(args, "wire"):
            size = max(model.bounds[1] - model.bounds[0])
            st = wire_pass(model, thickness=wire_thickness or size * 0.0006)
            sh = Shot("wire", ref.cam, kind="still", exposure=ref.exposure)
            times["wire"] = render_shot(sh, args, os.path.join(out, "wire.jpg"))
            end_wire(st)
    if turn and wanted(args, "turn"):
        render_turntable(args, model, turn, out, frames=args.frames, mode=turn_mode,
                         center=turn.get("center", (0, 0, 0)) if isinstance(turn, dict) else (0, 0, 0))
    if not args.no_json:
        items = [{"file": s.file, "caption": s.caption} for s in shots]
        for k in ("clay", "wire"):
            if k in extra:
                items.append({"file": k + ".jpg", "caption": extra[k]})
        with open(os.path.join(out, "shots.json"), "w", encoding="utf-8") as fh:
            json.dump(items, fh, ensure_ascii=False, indent=1)
    log("TIMES", json.dumps({k: round(v, 1) for k, v in times.items()}))
    return times
