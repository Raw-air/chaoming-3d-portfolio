"""把 素材/ 內的 FBX / OBJ 轉成網站用的 GLB（上材質、歸一化、減面、Draco 壓縮、匯出拓撲線框）。

用法（PowerShell）：
  & "C:\\Program Files\\Blender Foundation\\Blender 5.3\\blender.exe" -b --factory-startup `
      --python tools\\build_models.py -- 素材 site\\models [只處理的 key ...]
"""
import bpy, bmesh, sys, os, json, math, re, zlib
import numpy as np
from mathutils import Vector, Matrix

args = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = os.path.abspath(args[0]), os.path.abspath(args[1])
ONLY = args[2:]
PREV = os.environ.get("PREVIEW_DIR")
os.makedirs(OUT, exist_ok=True)

FILES = {
    "ship": "飛船 重拆.obj", "char": "大專  男主 服裝.fbx", "console": "操控台.fbx", "pod": "生物倉.fbx",
    "arcade": "遊戲機.fbx", "jukebox": "點唱機.fbx", "airship": "飛船.fbx", "venom": "猛毒雕刻.fbx",
}

# ---------------------------------------------------------------- materials
def lin(c):
    return ((c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)

def hexrgb(h):
    h = h.lstrip("#")
    return tuple(lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))

# name: (hex, metallic, roughness, emissive hex or None, emissive strength, alpha)
PAL = {
    # generic
    "metal_dark": ("#23272d", 0.9, 0.42, None, 0, 1), "metal_mid": ("#6c737c", 0.9, 0.38, None, 0, 1),
    "metal_light": ("#b9c0c8", 1.0, 0.22, None, 0, 1), "chrome": ("#e6e9ee", 1.0, 0.1, None, 0, 1),
    "copper": ("#b4683a", 1.0, 0.3, None, 0, 1), "brass": ("#c79a45", 1.0, 0.3, None, 0, 1),
    "black_gloss": ("#0b0c10", 0.2, 0.12, None, 0, 1), "black_matte": ("#121316", 0.0, 0.8, None, 0, 1),
    "rubber": ("#1b1b1e", 0.0, 0.9, None, 0, 1),
    # ship
    "ship_hull": ("#c9c6a8", 0.25, 0.48, None, 0, 1), "ship_panel": ("#7d8468", 0.4, 0.5, None, 0, 1),
    "ship_engine": ("#3d4a52", 0.7, 0.4, None, 0, 1), "ship_engine2": ("#56605d", 0.7, 0.42, None, 0, 1),
    "ship_door": ("#a8392f", 0.3, 0.5, None, 0, 1), "ship_glass": ("#0e1a22", 0.6, 0.06, "#2ad0ff", 0.25, 1),
    "ship_vent": ("#15181b", 0.8, 0.5, "#ff5a1e", 0.6, 1),
    # character
    "ch_coat": ("#5d5a36", 0, 0.78, None, 0, 1), "ch_pants": ("#6b3e2a", 0, 0.82, None, 0, 1),
    "ch_boots": ("#3a2419", 0, 0.6, None, 0, 1), "ch_belt": ("#2a1d15", 0, 0.5, None, 0, 1),
    "ch_scarf": ("#a3271f", 0, 0.85, None, 0, 1), "ch_shirt": ("#26282b", 0, 0.85, None, 0, 1),
    "ch_skin": ("#b67a58", 0, 0.55, None, 0, 1), "ch_hair": ("#1c1411", 0, 0.5, None, 0, 1),
    "ch_eye_white": ("#efe9e2", 0, 0.25, None, 0, 1), "ch_eye_iris": ("#2b1a12", 0, 0.2, None, 0, 1),
    "ch_teeth": ("#e8e0d0", 0, 0.35, None, 0, 1), "ch_lens": ("#3a2606", 0.3, 0.05, "#ffab2e", 1.6, 1),
    # console / pod
    "con_body": ("#2b3038", 0.8, 0.45, None, 0, 1), "con_panel": ("#3a424d", 0.8, 0.4, None, 0, 1),
    "con_accent": ("#7a2a25", 0.5, 0.45, None, 0, 1), "emit_red": ("#2a0605", 0.2, 0.3, "#ff2b23", 3.0, 1),
    "emit_amber": ("#2a1503", 0.2, 0.3, "#ff9a1f", 2.2, 1), "emit_teal": ("#04201f", 0.2, 0.3, "#1fffd2", 2.2, 1),
    "pod_glass": ("#7ff5e0", 0.0, 0.05, "#1fffd2", 0.35, 0.28), "pod_metal": ("#4a5158", 0.9, 0.38, None, 0, 1),
    "pod_base": ("#2c3238", 0.9, 0.45, None, 0, 1),
    # arcade
    "arc_side": ("#2d4f8f", 0.1, 0.5, None, 0, 1), "arc_front": ("#22242a", 0.2, 0.55, None, 0, 1),
    "arc_trim": ("#a9c4e6", 0.9, 0.25, None, 0, 1), "arc_screen": ("#05080d", 0.3, 0.05, "#35c9ff", 1.4, 1),
    "arc_marquee": ("#f3ead8", 0.0, 0.4, "#ff3b3b", 1.8, 1),
    "btn_red": ("#d8262b", 0, 0.3, "#ff2b2b", 0.5, 1), "btn_yellow": ("#f1c22d", 0, 0.3, "#ffc82b", 0.5, 1),
    "btn_blue": ("#2c7be0", 0, 0.3, "#2b8cff", 0.5, 1), "btn_green": ("#2fb86a", 0, 0.3, "#2bff8a", 0.5, 1),
    # jukebox
    "jb_wood": ("#7a4a32", 0.0, 0.5, None, 0, 1), "jb_glass": ("#0c0d12", 0.4, 0.05, "#ffb347", 0.5, 1),
    "jb_cloth": ("#3b1512", 0.0, 0.9, None, 0, 1), "jb_tube": ("#ffd9a0", 0.0, 0.2, "#ff9a3d", 2.6, 1),
    # airship
    "as_balloon": ("#d9cfb4", 0, 0.85, None, 0, 1), "as_patch": ("#7fa39a", 0, 0.85, None, 0, 1),
    "as_rope": ("#8a6a45", 0, 0.9, None, 0, 1), "as_hull": ("#9a5f4c", 0, 0.7, None, 0, 1),
    "as_wood_a": ("#8b5a3c", 0, 0.75, None, 0, 1), "as_wood_b": ("#a9774f", 0, 0.75, None, 0, 1),
    "as_wood_c": ("#6b432e", 0, 0.75, None, 0, 1), "as_fin": ("#c56a62", 0, 0.8, None, 0, 1),
    "as_iron": ("#2c2f33", 0.9, 0.5, None, 0, 1), "as_barrel": ("#3f6a6a", 0.6, 0.5, None, 0, 1),
    "as_fish": ("#7fb4c9", 0.3, 0.35, None, 0, 1), "as_meat": ("#b5433a", 0, 0.6, None, 0, 1),
    # sculpt
    "vn_body": ("#0d0e12", 0.35, 0.24, None, 0, 1), "vn_teeth": ("#e9dfc6", 0, 0.3, None, 0, 1),
    "vn_base": ("#5a4630", 1.0, 0.35, None, 0, 1),
}
_mats = {}

def mat(name):
    if name in _mats:
        return _mats[name]
    hx, metal, rough, em, es, alpha = PAL[name]
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    rgb = hexrgb(hx)
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    if em:
        b.inputs["Emission Color"].default_value = (*hexrgb(em), 1)
        b.inputs["Emission Strength"].default_value = es
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            pass
    disp = hexrgb(em) if em and es > 1 else rgb
    m.diffuse_color = (*disp, alpha)
    m.metallic = metal; m.roughness = rough
    _mats[name] = m
    return m


def set_slots(o, names):
    """Replace material slots of object o with palette materials (same slot order)."""
    me = o.data
    me.materials.clear()
    for n in names:
        me.materials.append(mat(n))


def set_all(o, name):
    me = o.data
    me.materials.clear(); me.materials.append(mat(name))
    for p in me.polygons:
        p.material_index = 0


def by_face(o, names, fn):
    """names: palette list; fn(center, normal) -> index into names."""
    me = o.data
    me.materials.clear()
    for n in names:
        me.materials.append(mat(n))
    for p in me.polygons:
        p.material_index = fn(p.center, p.normal)


def by_island(o, names):
    """Cycle palette materials over loose mesh islands."""
    me = o.data
    me.materials.clear()
    for n in names:
        me.materials.append(mat(n))
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    seen = set(); k = 0
    for f in bm.faces:
        if f.index in seen:
            continue
        stack = [f]; seen.add(f.index); grp = []
        while stack:
            fc = stack.pop(); grp.append(fc)
            for e in fc.edges:
                for nf in e.link_faces:
                    if nf.index not in seen:
                        seen.add(nf.index); stack.append(nf)
        for fc in grp:
            fc.material_index = k % len(names)
        k += 1
    bm.to_mesh(me); bm.free()


def base(n):
    return re.sub(r"\.\d+$", "", n)


def obb(o):
    # 由頂點直接計算（o.bound_box 在 mesh.transform() 之後不一定即時更新）
    co = np.empty(len(o.data.vertices) * 3, dtype=np.float32)
    o.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    return Vector(co.min(axis=0).tolist()), Vector(co.max(axis=0).tolist())


# ---------------------------------------------------------------- per-model colouring (geometry already in world space)
def color_ship(objs):
    table = {"機身": "ship_hull", "機身鐵板細節": "ship_panel", "前左右渦輪引擎": "ship_engine", "後左右渦輪引擎": "ship_engine2",
             "後排渦輪": "ship_engine", "渦輪引擎軸心": "metal_dark", "渦輪引擎軸心管子": "copper", "排氣孔": "ship_vent",
             "機身下出風口": "metal_dark", "機身下出風口.001": "ship_glass", "門倉": "ship_door", "底座": "metal_dark",
             "底座支架": "metal_mid", "Material": "metal_mid"}
    for o in objs:
        names = []
        for s in o.material_slots:
            n = s.material.name if s.material else ""
            names.append("metal_light" if n.startswith("風扇葉片") else table.get(n, "metal_mid"))
        set_slots(o, names or ["metal_mid"])


def color_char(objs):
    table = {"coat": "ch_coat", "Pants": "ch_pants", "boots.001": "ch_boots", "belt": "ch_belt", "scarf": "ch_scarf",
             "underwear": "ch_shirt", "Male protagonist skin": "ch_skin", "男主皮膚": "ch_skin", "Hair": "ch_hair",
             "Hair.001": "ch_hair", "材质.009": "ch_hair", "材质.004": "ch_eye_white", "材质.005": "ch_eye_iris",
             "Male protagonist's eyebrows": "ch_hair", "睫毛": "black_matte", "The male protagonist's teeth and tongue": "ch_teeth",
             "護目鏡.001": "brass", "護目鏡 鏡片.001": "ch_lens", "goggles2": "metal_dark", "goggles3": "ch_belt",
             "螺絲": "metal_light", "螺絲2": "metal_light", "拉鍊": "metal_light"}
    for o in objs:
        set_slots(o, [table.get(s.material.name if s.material else "", "ch_coat") for s in o.material_slots] or ["ch_coat"])


def color_console(objs):
    table = {"平面.030": "metal_dark", "立方体.035": "con_panel", "立方体.031": "con_body", "立方体.029": "con_body",
             "立方体.032": "con_accent", "平面.028": "con_panel", "平面.029": "metal_dark", "立方体.034": "con_panel",
             "平面.032": "emit_amber", "立方体.033": "con_panel", "立方体.036": "metal_dark", "平面.031": "emit_red"}
    for o in objs:
        set_all(o, table.get(o.name, "con_body"))


def color_pod(objs):
    table = {"柱体.018": "pod_glass", "柱体.019": "pod_base", "柱体.015": "pod_metal", "柱体.016": "copper",
             "柱体.017": "copper", "柱体.020": "pod_base", "柱体.021": "emit_red"}
    for o in objs:
        set_all(o, table.get(o.name, "pod_metal"))


def color_arcade(objs):
    for o in objs:
        n = o.name
        if n == "立方体":
            mn, mx = obb(o)
            H = mx.z - mn.z; W = mx.x

            def fn(c, nr):
                z = (c.z - mn.z) / H
                if abs(nr.x) > 0.85 and abs(c.x) > W * 0.55:
                    return 0  # side art panels
                if nr.y < -0.2 and abs(c.x) < W * 0.86:
                    if z > 0.885:
                        return 3  # marquee
                    if 0.6 < z < 0.87:
                        return 2  # CRT
                return 1
            by_face(o, ["arc_side", "arc_front", "arc_screen", "arc_marquee"], fn)
        elif n == "立方体.001":
            set_all(o, "arc_trim")
        elif n == "立方体.002":
            set_all(o, "metal_mid")
        elif n == "圆环.006":
            set_all(o, "metal_dark")
        elif n.startswith("球体"):
            set_all(o, "btn_red")
        elif n in ("圆环.004", "圆环.005"):
            by_island(o, ["btn_red", "btn_yellow", "btn_blue", "btn_green"])
        else:
            set_all(o, "metal_dark")


def color_jukebox(objs):
    for o in objs:
        n = o.name
        slot = o.material_slots[0].material.name if o.material_slots and o.material_slots[0].material else ""
        if n == "立方体":
            mn, mx = obb(o); H = mx.z - mn.z

            def fn(c, nr):
                z = (c.z - mn.z) / H
                if nr.y < -0.35 and abs(c.x) < (mx.x * 0.8):
                    if z > 0.72:
                        return 1
                    if z < 0.6 and abs(c.x) < mx.x * 0.62:
                        return 2
                return 0
            by_face(o, ["jb_wood", "jb_glass", "jb_cloth"], fn)
        elif n == "圆环.003":
            set_all(o, "jb_tube")
        elif n == "平面":
            set_all(o, "chrome")
        elif n == "立方体.003":
            set_all(o, "metal_mid")
        elif n == "立方体.001":
            set_all(o, "metal_light")
        elif slot == "材质.002":
            set_all(o, "chrome")
        else:
            set_all(o, "metal_light")


def color_airship(objs):
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    for o in objs:
        a, b = obb(o)
        for i in range(3):
            mn[i] = min(mn[i], a[i]); mx[i] = max(mx[i], b[i])
    size = max(mx - mn)
    woods = ["as_wood_a", "as_wood_b", "as_wood_c"]
    for o in objs:
        b = base(o.name); a, bb = obb(o); d = bb - a; big = max(d); thin = min(d) / max(big, 1e-6)
        m0 = o.material_slots[0].material.name if o.material_slots and o.material_slots[0].material else ""
        if b == "球体":
            pick = "as_balloon" if big > size * 0.3 else "as_patch"
        elif m0.startswith("熱氣球 繩") or b in ("繩", "Torus1", "环体", "贝塞尔曲线"):
            pick = "as_rope"
        elif m0.startswith("acmat") or b == "地籠":
            pick = "as_iron"
        elif b == "ellipse":
            pick = "as_hull"
        elif m0.startswith("油桶"):
            pick = "as_barrel"
        elif b == "魚":
            pick = None
        elif "舵" in b or b == "Wheel":
            pick = "brass" if "底座" not in b else "as_wood_c"
        elif b == "平面" and thin < 0.12 and big > size * 0.12 and not m0.startswith(("吊橋", "飛船木板")):
            pick = "as_fin"
        else:
            pick = woods[zlib.crc32(o.name.encode()) % 3]
        if pick is None:
            set_slots(o, [("as_meat" if (s.material and s.material.name.startswith("肉")) else "as_fish") for s in o.material_slots] or ["as_fish"])
        else:
            set_all(o, pick)


def color_venom(objs):
    table = {"角色": "vn_body", "牙": "vn_teeth"}
    for o in objs:
        set_all(o, table.get(o.name, "vn_base"))


COLOR = {"ship": color_ship, "char": color_char, "console": color_console, "pod": color_pod, "arcade": color_arcade,
         "jukebox": color_jukebox, "airship": color_airship, "venom": color_venom}
DECIMATE = {"venom": {"角色": 150000, "牙": 26000}, "airship": {"贝塞尔曲线.059": 26000, "平面.001": 18000, "球体.051": 9000}}
SPIN = {"ship": ["圆环", "圆环.001"]}   # kept as separate nodes with centred origins (propellers)
NO_WIRE = {"venom"}


# ---------------------------------------------------------------- helpers
def override(active, objs):
    return bpy.context.temp_override(active_object=active, object=active, selected_objects=objs, selected_editable_objects=objs)


def join(objs, name):
    objs = [o for o in objs if o]
    if not objs:
        return None
    if len(objs) > 1:
        with override(objs[0], objs):
            bpy.ops.object.join()
    objs[0].name = name; objs[0].data.name = name
    return objs[0]


def tri_count(objs):
    n = 0
    for o in objs:
        o.data.calc_loop_triangles(); n += len(o.data.loop_triangles)
    return n


def process(key):
    f = FILES[key]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()
    p = os.path.join(SRC, f)
    if f.lower().endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=p)
    else:
        bpy.ops.wm.obj_import(filepath=p)
    sc = bpy.context.scene
    meshes = [o for o in sc.objects if o.type == "MESH"]
    stats = {"file": f, "objects": len(meshes), "tris": tri_count(meshes), "verts": sum(len(o.data.vertices) for o in meshes),
             "materials": len({s.material.name for o in meshes for s in o.material_slots if s.material})}

    # bake world transforms into mesh data
    mats_w = {o.name: o.matrix_world.copy() for o in meshes}
    for o in sc.objects:
        o.animation_data_clear()
    for o in meshes:
        if o.data.users > 1:
            o.data = o.data.copy()
    for o in meshes:
        mw = mats_w[o.name]
        o.parent = None
        o.matrix_world = Matrix.Identity(4)
        o.data.transform(mw)
        if mw.determinant() < 0:
            o.data.flip_normals()
        o.data.update()
    for o in list(sc.objects):
        if o.type != "MESH":
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()

    COLOR[key](meshes)

    # decimate heavy pieces
    for name, target in DECIMATE.get(key, {}).items():
        o = sc.objects.get(name)
        if not o:
            print("  !! decimate target missing", name); continue
        o.data.calc_loop_triangles(); n = len(o.data.loop_triangles)
        if n <= target:
            continue
        md = o.modifiers.new("dec", "DECIMATE"); md.ratio = target / n
        dg = bpy.context.evaluated_depsgraph_get()
        me2 = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        o.modifiers.clear(); old = o.data; o.data = me2; bpy.data.meshes.remove(old)
        o.data.shade_smooth()
        print(f"  decimated {name}: {n} -> {len(o.data.polygons)}")

    # strip attributes we do not ship
    for o in meshes:
        me = o.data
        while me.uv_layers:
            me.uv_layers.remove(me.uv_layers[0])
        for a in list(me.color_attributes):
            me.color_attributes.remove(a)
        if me.shape_keys:
            o.shape_key_clear()

    # normalise: centre XY, base on ground, longest side = 1
    mn = Vector((1e18,) * 3); mx = Vector((-1e18,) * 3)
    for o in meshes:
        a, b = obb(o)
        for i in range(3):
            mn[i] = min(mn[i], a[i]); mx[i] = max(mx[i], b[i])
    dims = mx - mn; s = 1.0 / max(dims)
    T = Matrix.Scale(s, 4) @ Matrix.Translation(Vector((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z)))
    for o in meshes:
        o.data.transform(T); o.data.update()
    stats["dims"] = [round(x, 3) for x in dims]
    stats["norm_dims"] = [round(x * s, 4) for x in dims]

    # 爆炸拆解圖：把「所屬部件的中心」寫進頂點色（網站端用來把部件沿中心方向推開）
    for o in meshes:
        co = np.empty(len(o.data.vertices) * 3, dtype=np.float32)
        o.data.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        c = (co.min(axis=0) + co.max(axis=0)) / 2      # 直接由頂點算（bound_box 在 transform 後不會即時更新）
        col = (float(np.clip(c[0] + 0.5, 0, 1)), float(np.clip(c[1] + 0.5, 0, 1)), float(np.clip(c[2], 0, 1)), 1.0)
        attr = o.data.color_attributes.new("part", "FLOAT_COLOR", "POINT")
        attr.data.foreach_set("color", col * len(attr.data))
        o.data.color_attributes.active_color = attr
        try:
            o.data.color_attributes.render_color_index = 0
        except Exception:
            pass

    # split spinning parts, join the rest
    spin_objs = [sc.objects[n] for n in SPIN.get(key, []) if n in sc.objects]
    body = join([o for o in meshes if o not in spin_objs], "BODY")
    out_objs = [body]
    stats["spin"] = []
    for i, o in enumerate(spin_objs):
        a, b = obb(o); c = (a + b) / 2
        o.data.transform(Matrix.Translation(-c)); o.location = c
        o.name = f"SPIN{i}"; out_objs.append(o)
        stats["spin"].append({"name": o.name, "center": [round(x, 4) for x in c], "size": [round(x, 4) for x in (b - a)]})
    bpy.context.view_layer.update()
    stats["web_tris"] = tri_count(out_objs)

    # topology wireframe: same meshes with faces removed (exported as GL_LINES)
    if key not in NO_WIRE:
        for o in list(out_objs):
            w = o.copy(); w.data = o.data.copy(); sc.collection.objects.link(w)
            w.name = o.name + "_WIRE"
            bm = bmesh.new(); bm.from_mesh(w.data)
            bmesh.ops.delete(bm, geom=list(bm.faces), context="FACES_ONLY")
            bm.to_mesh(w.data); bm.free()
            w.data.materials.clear()
            stats.setdefault("wire_edges", 0)
            stats["wire_edges"] += len(w.data.edges)

    if PREV:
        render_preview(key, out_objs)

    path = os.path.join(OUT, key + ".glb")
    kw = dict(filepath=path, export_format="GLB", export_yup=True, export_apply=False, export_animations=False,
              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
              export_draco_position_quantization=14, export_draco_normal_quantization=10,
              use_mesh_edges=True, export_cameras=False, export_lights=False)
    for extra in ({"export_texcoords": False, "export_vertex_color": "ACTIVE", "export_active_vertex_color_when_no_material": True},
                  {"export_texcoords": False, "export_vertex_color": "ACTIVE"}, {"export_texcoords": False}, {}):
        try:
            bpy.ops.export_scene.gltf(**kw, **extra); break
        except TypeError as e:
            print("  export retry:", e)
    stats["bytes"] = os.path.getsize(path)
    print("BUILT", key, stats)
    return stats


def render_preview(key, objs):
    sc = bpy.context.scene
    cam_d = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam)
    sc.camera = cam; cam_d.lens = 55
    tgt = bpy.data.objects.new("tgt", None); sc.collection.objects.link(tgt)
    mn = Vector((1e18,) * 3); mx = Vector((-1e18,) * 3)
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
    tgt.location = (mn + mx) / 2
    cam.constraints.new("TRACK_TO").target = tgt
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x = 560; sc.render.resolution_y = 560
    sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_cavity = True
    sh.show_specular_highlight = True
    hide = [o for o in sc.objects if o.name.endswith("_WIRE")]
    for o in hide:
        o.hide_render = True
    for tag, az, el in (("f", -62, 16), ("b", 118, 24)):
        a = math.radians(az); e = math.radians(el)
        cam.location = tgt.location + Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))) * 2.5
        sc.render.filepath = os.path.join(PREV, f"{key}_{tag}.png")
        bpy.ops.render.render(write_still=True)
    for o in hide:
        o.hide_render = False
    bpy.data.objects.remove(cam, do_unlink=True); bpy.data.objects.remove(tgt, do_unlink=True)


stats_path = os.path.join(OUT, "stats.json")
allstats = json.load(open(stats_path, encoding="utf-8")) if os.path.exists(stats_path) else {}
for key in FILES:
    if ONLY and key not in ONLY:
        continue
    allstats[key] = process(key)
with open(stats_path, "w", encoding="utf-8") as fh:
    json.dump(allstats, fh, ensure_ascii=False, indent=1)
print("ALL DONE")
