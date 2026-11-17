"""把 素材/ 內的 FBX / OBJ 轉成網站用的 GLB（上材質、歸一化、減面、Draco 壓縮、匯出拓撲線框）。

用法（PowerShell）：
  & "C:\\Program Files\\Blender Foundation\\Blender 5.3\\blender.exe" -b --factory-startup `
      --python tools\\build_models.py -- 素材 site\\models [只處理的 key ...]

匯入、烘焙變換、調色盤材質等共用部分在 tools/modellib.py。
"""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modellib import (FILES, PAL, COLOR, DECIMATE, SPIN, NO_WIRE, mat, obb, join, tri_count,  # noqa: F401
                      import_file, bake_world, apply_decimate, reset_materials)

args = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = os.path.abspath(args[0]), os.path.abspath(args[1])
ONLY = args[2:]
PREV = os.environ.get("PREVIEW_DIR")
os.makedirs(OUT, exist_ok=True)


def process(key):
    f = FILES[key]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    reset_materials()
    import_file(key, SRC)
    sc = bpy.context.scene
    meshes = [o for o in sc.objects if o.type == "MESH"]
    stats = {"file": f, "objects": len(meshes), "tris": tri_count(meshes), "verts": sum(len(o.data.vertices) for o in meshes),
             "materials": len({s.material.name for o in meshes for s in o.material_slots if s.material})}

    # bake world transforms into mesh data
    bake_world(meshes, list(sc.objects))

    COLOR[key](meshes)

    # decimate heavy pieces
    apply_decimate(key, list(sc.objects))

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
