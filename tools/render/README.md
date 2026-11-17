# tools/render — offline Blender stills for the portfolio

Blender 5.3 headless, Cycles on CPU for stills, EEVEE for turntables. One script per work:
`scene_<key>.py` (keys from `tools/modellib.py` `FILES`: ship, char, console, pod, arcade, jukebox, airship, venom).
`scene_ship.py` is the reference: copy its structure.

## Run

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"
& $blender -b --factory-startup --python tools\render\scene_ship.py -- --quality draft --only hero,s1 --out <scratch dir>
& $blender -b --factory-startup --python tools\render\scene_ship.py -- --quality final            # all stills -> site/renders/ship
& $blender -b --factory-startup --python tools\render\scene_ship.py -- --quality final --only turn   # turntable only
```

Args after `--`:
- `--quality draft|final` (default draft). draft = 640x360 (card 640x480), 24 spp; final = hero 1920x1080 128 spp,
  card 1200x900 96 spp, s*/clay/wire 1600x900 96 spp, turntable EEVEE 1280x720 48 samples.
- `--only hero,card,s1,s2,s3,s4,clay,wire,turn` — subset (default: all stills, no turntable).
- `--turn` — also render the turntable; `--frames N` (default 24).
- `--out DIR` — write somewhere else (use your scratch dir for look-dev so you do not overwrite finals).
- `--samples N` — override spp for every still (quick quality probes); `--no-json` — do not rewrite shots.json.

Keep test renders at draft: other agents share this 4-core / 8 GB machine.

## Output contract (site/renders/<key>/)

| file | size | content |
|---|---|---|
| hero.jpg | 1920x1080 | most dramatic beauty shot |
| card.jpg | 1200x900 | clean three-quarter for the index card |
| s1.jpg … s4.jpg | 1600x900 | s1 three-quarter front, s2 rear/side, s3+s4 detail close-ups with DOF |
| clay.jpg, wire.jpg | 1600x900 | exactly the s1 camera; clay = neutral matte model, set kept but subdued; wire = real quad topology |
| turn/00.jpg … turn/23.jpg | 1280x720 | 24 frames, full 360° |
| shots.json | | `[{"file":"hero.jpg","caption":"…"}, …]` short Traditional Chinese captions, every still incl. clay/wire; describe the shot only, no invented facts about the artist |

JPEG quality 90. `C.run()` writes all of it; captions come from `Shot(caption=…)` plus `captions_extra={"clay":…, "wire":…}`.

## Writing scene_<key>.py

```python
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
args = C.parse_args(); C.reset()
model = C.load("arcade", size=1.9)                      # or scale=…, ground=[names], prep=fn(objs), rot_z=deg
C.apply_looks(model.objs, {"arc_side": ("painted", dict(color="#2d4f8f", panels=None)),
                           "arc_screen": ("screen", dict(color="#35c9ff", strength=4))})
M_FLOOR = C.material("concrete", "floor", color="#3a3c3e", wet=0.6)
C.floor(60, M_FLOOR); C.box("crate", (1, 1, 1), (3, 2, 0), mat=M_FLOOR, origin="bottom")
C.area("key", (4, -5, 5), (0, 0, 1), 800, C.kelvin(5600), 3); C.haze(density=0.004)
shots = [C.Shot("hero", dict(loc=(…), target=(…), lens=35, fstop=4, focus=(…)), "說明…", kind="hero"), …]
C.run(args, "arcade", model, shots, clay_wire_of="s1", turn=dict(loc=(…), target=(…), lens=40),
      captions_extra={"clay": "…", "wire": "…"})
```

- **Model**: `C.load` = `modellib.load_model` (import, bake world transforms, palette materials by part name) +
  centre XY, base on z=0, scale, parent everything to `model.pivot` (the turntable rotates it). Units are metres
  after scaling — pick a real-world size (the ship is scaled ×2.2 → 12 m long, 15.6 m wingspan).
- **Materials**: `C.apply_looks(objs, {palette_name: (recipe, kwargs)})` swaps the flat palette material in every
  slot. Unlisted palette names get `C.auto_recipe()` (derived from PAL metal/rough/emission). Recipes
  (`C.RECIPES`): `painted` (panel seams, per-panel tint, AO cavity grime, vertical streaks, Bevel edge wear to bare
  metal, roughness breakup; `panels=None` to disable seams, `metal=` for painted-metal sheen), `metal`
  (`brushed=0..1` anisotropic), `rubber`, `plastic`, `glass` (real transmission), `tinted_glass` (opaque canopy/visor),
  `emissive`, `screen` (scanlines), `wood`, `fabric` (weave bump + sheen), `leather`, `skin` (SSS), `hair`,
  `concrete` (wet floor: puddles, slab joints), `floor_paint` (markings sharing the floor's puddle mask), `clay`, `flat`.
  `C.material(recipe, name, **kw)` builds one for set pieces. Model recipes use Object coords (stick to the model);
  pass `space="world"` for set pieces. All recipes work in Cycles and EEVEE (Bevel/AO degrade gracefully in EEVEE).
- **Set**: `box` (real dimensions baked, beveled, `origin="bottom"`), `cylinder`, `plane`, `floor`, `pipe(p0,p1,r)`,
  `cable(points, r)` (bezier tube), `text(body, size, loc, rot, mat, fontpath)` (`C.FONT_TC` msjhbd.ttc for Chinese,
  `C.FONT_LATIN`, `C.FONT_STENCIL` impact.ttf; rot (90,0,0) stands it up facing −Y, (0,0,0) lies on the floor),
  `strip` (emissive light bar), `sky_card` (emissive gradient+cloud backdrop), `haze` (homogeneous volume box),
  `world`. Lights: `area`, `spot`, `point`, `sun`; colours as '#hex' or `C.kelvin(K)`.
- **Roles**: every object gets `o["role"]` = model / set / light / keep (emitters & backdrops that clay/wire must
  not touch) / fx. Set `o["hide_turn"] = True` on props that would intersect the model while it spins.
- **Shots**: `C.Shot(name, cam=dict(loc, target, lens, fstop, focus, shift, roll), caption, kind="hero|card|still",
  exposure=0, samples=None, setup=fn, teardown=fn)`.
- **Clay / wire**: done by `C.run` with the camera of `clay_wire_of`. Wire uses a Wireframe *modifier* copy of each
  model mesh (true quads, verified visually); the Cycles Wireframe *node* would show the triangulation.
  Thickness defaults to 0.05 % of the model size; body = light clay with emissive white lines
  (`wire_pass(body_color="#14171b")` gives a dark blueprint look instead).
- **Caching**: `C.material()` caches by name — two different looks need two different names.

## Measured times (i5-6500, 4 threads, CPU Cycles)

| what | time |
|---|---|
| draft still 640x360 24 spp (ship scene, haze, ~600 set objects) | 25–40 s each incl. scene sync (first ~10 s is import/build) |
| draft clay / wire | 17 s / 20 s |
| EEVEE turntable draft 640x360 | first frame ~26 s (shader compile), then ~2–3 s/frame |
| final hero 1920x1080 128 spp | **1214 s (20 min)** |
| final s1 1600x900 96 spp | **673 s (11 min)** |
| full-size 16 spp + OIDN (card / s2 / s3 / s4 / clay / wire) | 81 / 107 / 113 / 125 / 82 / 89 s |
| EEVEE turntable 1280x720 24 samples | ~20 s first frame, then ~10 s/frame (24 frames: 4 min) |

A full final set at the default spp would be ~1.5 h on this machine. Budget accordingly: render hero/s1 at
final spp, and use `--quality final --samples 16..32` (full contract size, OIDN) for the rest if time is short.
(AO and Bevel node samples were lowered to 2 after the hero/s1 timings — expect those to be a bit faster now.)

## Pitfalls (Blender 5.3)

- `Material.use_nodes` is deprecated (always on); wrap in try. ShaderNodeMix has duplicate socket names — use
  indices (Factor 0, A/B colour 6/7, colour result output 2); `C.mix()` does this.
- AgX looks are full names: "AgX - Punchy", "AgX - High Contrast", "AgX - Medium High Contrast" … (the enum of
  `view_transform` reports only 'NONE' through bl_rna, but setting 'AgX' works). Punchy made the off-white hull read
  salmon next to teal light; the kit uses "AgX - High Contrast".
- `image_settings.media_type` exists (set 'IMAGE' before `file_format='JPEG'`).
- `object.bound_box` is stale after `mesh.transform()` — use `modellib.bounds()` / `obb()` (vertex based).
- Warm lights: `C.kelvin(3000)` is very orange in linear; next to a teal key it turns white paint pink.
  Use ≥4500 K for lights that hit the hero model, keep 2400–3000 K for visible practical bulbs.
- Volumes: keep haze homogeneous (constant density) — Cycles then needs no ray marching and the cost is small.
  A dense haze box in front of a bright backdrop washes it into flat fog; keep the outside haze thin.
- The ship OBJ's propeller blades reach below the landing gear; `scene_ship.prep` rotates them about their hub
  (`ground=` then puts the gear, not the blades, on the floor).
- Text objects: a 4-character Chinese sign in msjhbd.ttc renders fine as a FONT curve (no need to convert to mesh).
