"""
Blender + BlendLuxCore BDPT caustic render script.

Bidirectional Path Tracing with Metropolis sampling — the gold standard
for refractive caustics. Cycles backward-traces poorly for this light
path (source → lens top → refract → lens bottom → refract → plane);
BIDIR traces from both ends simultaneously.

Run headlessly:
    /Applications/Blender.app/Contents/MacOS/Blender \
        --background --python render_caustics_bdpt.py

Or paste into Blender's Scripting workspace and click Run Script.
Requires BlendLuxCore 2.10.2 installed as a Blender 4.3 extension.
"""

import bpy
import addon_utils
import mathutils

# ── Configuration ──────────────────────────────────────────────────────────────

OBJ_PATH    = "/Users/admin/causticsEngineering/examples/original_image.obj"
OUTPUT_PATH = "/Users/admin/causticsEngineering/examples/caustic_bdpt.png"

IOR          = 1.49
FOCAL_DIST   = 0.2       # metres — point light distance above lens top
LIGHT_ENERGY = 10000     # watts
HALT_SAMPLES = 2000      # samples per pixel (BDPT converges fast for caustics)
RESOLUTION   = 1024

# ── 1. Enable BlendLuxCore ─────────────────────────────────────────────────────

print("Enabling BlendLuxCore...")
addon_utils.extensions_refresh(ensure_wheels=True)
result = bpy.ops.preferences.addon_enable(module="bl_ext.user_default.BlendLuxCore")
print(f"  addon_enable result: {result}")


# ── 2. Clear scene ─────────────────────────────────────────────────────────────

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for block in list(bpy.data.meshes) + list(bpy.data.lights) + list(bpy.data.cameras):
    try:
        bpy.data.batch_remove([block])
    except Exception:
        pass

# ── 3. Import OBJ (axis-corrected — confirmed by Blender MCP session) ─────────

bpy.ops.wm.obj_import(
    filepath=OBJ_PATH,
    forward_axis='Y',
    up_axis='Z',
)
lens_obj = bpy.context.selected_objects[0]
lens_obj.name = "CausticLens"

# Compute bounding box in world space
dg      = bpy.context.evaluated_depsgraph_get()
ev      = lens_obj.evaluated_get(dg)
corners = [lens_obj.matrix_world @ mathutils.Vector(c) for c in ev.bound_box]
xs = [v.x for v in corners]
ys = [v.y for v in corners]
zs = [v.z for v in corners]

cx, cy        = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
lens_top_z    = max(zs)
lens_bottom_z = min(zs)
lens_span     = max(max(xs) - min(xs), max(ys) - min(ys))

print(f"Lens centre XY : ({cx:.4f}, {cy:.4f})")
print(f"Lens Z range   : {lens_bottom_z:.4f} → {lens_top_z:.4f}")
print(f"Lens span      : {lens_span:.4f} m")

# ── 4. Glass material ──────────────────────────────────────────────────────────
# Use Cycles-compatible nodes — BlendLuxCore auto-converts Glass BSDF to LuxCore glass.
# mat.luxcore.use_cycles_nodes defaults to False; set True to use the Cycles node tree.

mat = bpy.data.materials.new("CausticGlass")
mat.use_nodes = True
mat.luxcore.use_cycles_nodes = True   # tell BlendLuxCore to read mat.node_tree

nt = mat.node_tree
nt.nodes.clear()

out   = nt.nodes.new('ShaderNodeOutputMaterial'); out.location   = (300, 0)
glass = nt.nodes.new('ShaderNodeBsdfGlass');      glass.location = (  0, 0)
glass.inputs['IOR'].default_value       = IOR
glass.inputs['Roughness'].default_value = 0.0
glass.inputs['Color'].default_value     = (1, 1, 1, 1)
nt.links.new(glass.outputs['BSDF'], out.inputs['Surface'])

lens_obj.data.materials.clear()
lens_obj.data.materials.append(mat)

# ── 5. Point light ─────────────────────────────────────────────────────────────

light_z    = lens_top_z + FOCAL_DIST
light_data = bpy.data.lights.new("CausticLight", type='POINT')
light_data.energy           = LIGHT_ENERGY
light_data.shadow_soft_size = 0.001   # near-point source

light_obj          = bpy.data.objects.new("CausticLight", light_data)
light_obj.location = (cx, cy, light_z)
bpy.context.collection.objects.link(light_obj)

print(f"Light at z = {light_z:.4f} m")

# ── 6. Projection plane (white matte, LuxCore node tree) ──────────────────────

plane_z = lens_bottom_z - FOCAL_DIST
bpy.ops.mesh.primitive_plane_add(size=lens_span * 3, location=(cx, cy, plane_z))
plane      = bpy.context.active_object
plane.name = "ProjectionPlane"

pmat = bpy.data.materials.new("WhiteMatte")
pmat.use_nodes = True
pmat.luxcore.use_cycles_nodes = True   # use Cycles nodes (auto-converted by BlendLuxCore)

pnt = pmat.node_tree
pnt.nodes.clear()

pout    = pnt.nodes.new('ShaderNodeOutputMaterial'); pout.location    = (300, 0)
diffuse = pnt.nodes.new('ShaderNodeBsdfDiffuse');    diffuse.location = (  0, 0)
diffuse.inputs['Color'].default_value     = (1, 1, 1, 1)
diffuse.inputs['Roughness'].default_value = 0.0
pnt.links.new(diffuse.outputs['BSDF'], pout.inputs['Surface'])

plane.data.materials.append(pmat)

print(f"Plane at z = {plane_z:.4f} m")

# ── 7. Camera — orthographic, looking straight down ───────────────────────────

cam_data             = bpy.data.cameras.new("Camera")
cam_data.type        = 'ORTHO'
cam_data.ortho_scale = lens_span * 1.5

cam_obj                = bpy.data.objects.new("Camera", cam_data)
cam_obj.location       = (cx, cy, light_z + 0.05)
cam_obj.rotation_euler = (0, 0, 0)   # default Blender camera looks down -Z
bpy.context.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj

# ── 8. World — pure black ─────────────────────────────────────────────────────

world = bpy.context.scene.world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node is None:
    bg_node = world.node_tree.nodes.new('ShaderNodeBackground')
bg_node.inputs['Color'].default_value    = (0, 0, 0, 1)
bg_node.inputs['Strength'].default_value = 0.0

# ── 9. LuxCore render settings ────────────────────────────────────────────────

scene  = bpy.context.scene

scene.render.engine = 'LUXCORE'
print(f"Render engine set to: {scene.render.engine}")

config = scene.luxcore.config

# BIDIR = Bidirectional Path Tracing (traces from both camera AND light)
config.engine = 'BIDIR'

# METROPOLIS: focuses samples on brighter caustic hotspots
# "Suited for rendering caustics" (per BlendLuxCore docs)
config.sampler = 'METROPOLIS'

# Ray depth: 16 bounces in each direction (plenty for two refractions)
config.bidir_light_maxdepth = 16
config.bidir_path_maxdepth  = 16

# Halt condition
halt = scene.luxcore.halt
halt.enable      = True
halt.use_samples = True
halt.samples     = HALT_SAMPLES

# Output resolution
scene.render.resolution_x               = RESOLUTION
scene.render.resolution_y               = RESOLUTION
scene.render.filepath                   = OUTPUT_PATH
scene.render.image_settings.file_format = 'PNG'

print(f"\nRendering {RESOLUTION}×{RESOLUTION}  |  BIDIR/METROPOLIS  |  {HALT_SAMPLES} spp")
print(f"Output → {OUTPUT_PATH}")
print("Note: BIDIR is CPU-only. GPU is not used for this engine.\n")

# ── 10. Save .blend, then Blender renders it in a second invocation ───────────
# bpy.ops.render.render() with LuxCore in --background mode fails silently
# (the LuxCore engine's render() method is never dispatched in headless context).
# The reliable workaround: save the configured scene to a .blend file, then
# Blender re-opens it with -f 1 which does a proper render + file write.

BLEND_PATH = "/tmp/caustic_bdpt_scene.blend"
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
print(f"Scene saved → {BLEND_PATH}")

import subprocess, os, sys
blender_bin = sys.executable.replace('/bin/python3.11', '')
# sys.executable is the blender Python, not the Blender binary; find it
blender_candidates = [
    "/Applications/Blender.app/Contents/MacOS/Blender",
]
blender_bin = next((p for p in blender_candidates if os.path.exists(p)), "blender")

# Write a helper script: enable BlendLuxCore, then render, then save
render_script = "/tmp/luxcore_render_pass.py"
with open(render_script, "w") as f:
    f.write(f"""\
import bpy, addon_utils, sys
addon_utils.extensions_refresh(ensure_wheels=True)
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.BlendLuxCore")
print("BlendLuxCore enabled, starting render...")
sys.stdout.flush()

bpy.context.scene.render.filepath = {repr(OUTPUT_PATH.replace('.png', ''))}
bpy.context.scene.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)

import os, glob
out = {repr(OUTPUT_PATH)}
if os.path.exists(out):
    print(f"Render saved → {{out}}")
else:
    matches = sorted(glob.glob(out.replace('.png', '') + '*.png'))
    if matches:
        import shutil; shutil.copy(matches[-1], out)
        print(f"Render saved → {{out}} (from {{matches[-1]}})")
    else:
        print("WARNING: no output file found")
""")

print(f"Launching second Blender pass to render…")
proc = subprocess.run(
    [blender_bin, "--background", BLEND_PATH,
     "--python", render_script],
    capture_output=False,
    timeout=600,
)
print(f"Return code: {proc.returncode}")

# Blender appends frame number: caustic_bdpt0001.png
import glob
base    = OUTPUT_PATH.replace('.png', '')
matches = glob.glob(f"{base}*.png")
if os.path.exists(OUTPUT_PATH):
    print(f"\nDone → {OUTPUT_PATH}")
elif matches:
    import shutil
    best = sorted(matches)[-1]
    shutil.copy(best, OUTPUT_PATH)
    print(f"\nDone → {OUTPUT_PATH}  (copied from {best})")
else:
    print(f"\nWARNING: output not found. Checked {base}*.png")
