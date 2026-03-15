"""
Blender caustic render script for CausticsEngineering OBJ output.

Run headlessly:
    blender --background --python render_caustics.py

Or paste into Blender's Scripting workspace and click Run Script.
Requires Blender 3.3+. Tested with 3.6 and 4.x.
"""

import bpy
import math
import mathutils

# ── Configuration ──────────────────────────────────────────────────────────────

OBJ_PATH    = "/Users/admin/causticsEngineering/examples/original_image.obj"
OUTPUT_PATH = "/Users/admin/causticsEngineering/examples/caustic_render.png"

IOR          = 1.49   # must match n1 in the Julia code
FOCAL_DIST   = 0.2    # metres — light-to-lens distance (focalLength in Julia)
LIGHT_ENERGY = 8000   # watts; raise if the caustic is too dim
SAMPLES      = 512    # Cycles samples; 512 = fast preview, 2048+ = final quality
RESOLUTION   = 1024   # pixels, square

# ── 1. Clear scene ─────────────────────────────────────────────────────────────

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for block in list(bpy.data.meshes) + list(bpy.data.lights) + list(bpy.data.cameras):
    try:
        bpy.data.batch_remove([block])
    except Exception:
        pass

# ── 2. Import OBJ ──────────────────────────────────────────────────────────────
# Blender 3.3+ uses wm.obj_import; older versions use import_scene.obj

if bpy.app.version >= (3, 3, 0):
    bpy.ops.wm.obj_import(filepath=OBJ_PATH)
else:
    bpy.ops.import_scene.obj(filepath=OBJ_PATH, axis_forward='-Z', axis_up='Y')

lens_obj = bpy.context.selected_objects[0]
lens_obj.name = "CausticLens"

# Compute bounding box in world space
dg = bpy.context.evaluated_depsgraph_get()
ev = lens_obj.evaluated_get(dg)
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

# ── 3. Glass material (IOR matches the Julia refraction model) ─────────────────

mat = bpy.data.materials.new("CausticGlass")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()

out   = nt.nodes.new('ShaderNodeOutputMaterial'); out.location   = (300, 0)
glass = nt.nodes.new('ShaderNodeBsdfGlass');      glass.location = (  0, 0)
glass.inputs['IOR'].default_value       = IOR
glass.inputs['Roughness'].default_value = 0.0          # perfectly smooth
glass.inputs['Color'].default_value     = (1, 1, 1, 1) # clear glass
nt.links.new(glass.outputs['BSDF'], out.inputs['Surface'])

lens_obj.data.materials.clear()
lens_obj.data.materials.append(mat)

# ── 4. Point light — directly above lens centre at focal distance ──────────────
# A near-point source matches the algorithm's assumption in findSurface().
# For a collimated beam instead, change type='SUN' and remove shadow_soft_size.

light_z    = lens_top_z + FOCAL_DIST
light_data = bpy.data.lights.new("CausticLight", type='POINT')
light_data.energy           = LIGHT_ENERGY
light_data.shadow_soft_size = 0.001          # near-point; increase for softer result
light_data.cycles.use_multiple_importance_sampling = True

# Blender 4.0+ shadow caustics (silently ignored on older versions)
try:
    light_data.cycles.use_shadow_caustic = True
except AttributeError:
    pass

light_obj          = bpy.data.objects.new("CausticLight", light_data)
light_obj.location = (cx, cy, light_z)
bpy.context.collection.objects.link(light_obj)

# ── 5. Projection plane — white diffuse, below lens at focal distance ──────────
# The caustic pattern forms here. Make it larger than the lens so edge spill shows.

plane_z = lens_bottom_z - FOCAL_DIST
bpy.ops.mesh.primitive_plane_add(size=lens_span * 3, location=(cx, cy, plane_z))
plane      = bpy.context.active_object
plane.name = "ProjectionPlane"

pmat = bpy.data.materials.new("WhiteDiffuse")
pmat.use_nodes = True
pnt = pmat.node_tree
pnt.nodes.clear()
pout    = pnt.nodes.new('ShaderNodeOutputMaterial'); pout.location    = (300, 0)
diffuse = pnt.nodes.new('ShaderNodeBsdfDiffuse');    diffuse.location = (  0, 0)
diffuse.inputs['Color'].default_value     = (1, 1, 1, 1)
diffuse.inputs['Roughness'].default_value = 0.0
pnt.links.new(diffuse.outputs['BSDF'], pout.inputs['Surface'])
plane.data.materials.append(pmat)

# Blender 4.0+ shadow catcher for caustic light paths
try:
    plane.cycles.is_caustic_catcher = True
except AttributeError:
    pass

# ── 6. Camera — orthographic, above scene looking straight down ────────────────
# Positioned above the light so it looks through the glass lens onto the
# projection plane. The camera has no physical presence in Cycles so it
# does not block any light rays.

cam_data             = bpy.data.cameras.new("Camera")
cam_data.type        = 'ORTHO'
cam_data.ortho_scale = lens_span * 1.5      # tighter crop on the caustic region

cam_obj                = bpy.data.objects.new("Camera", cam_data)
cam_obj.location       = (cx, cy, light_z + 0.05)
cam_obj.rotation_euler = (0, 0, 0)          # default Blender camera looks down -Z
bpy.context.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj

# ── 7. World — pure black background (no ambient light polluting caustics) ─────

world = bpy.context.scene.world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node is None:
    bg_node = world.node_tree.nodes.new('ShaderNodeBackground')
bg_node.inputs['Color'].default_value    = (0, 0, 0, 1)
bg_node.inputs['Strength'].default_value = 0.0

# ── 8. Render settings ─────────────────────────────────────────────────────────

scene  = bpy.context.scene
cycles = scene.cycles

scene.render.engine = 'CYCLES'
cycles.samples      = SAMPLES

# Do NOT denoise — denoising smears caustic detail
cycles.use_denoising = False

# Caustics — this is the key setting
cycles.caustics_refractive = True
cycles.caustics_reflective = False

# Allow enough bounces for light to pass through the glass and reach the plane
cycles.max_bounces             = 16
cycles.transmission_bounces    = 8
cycles.transparent_max_bounces = 8

# GPU rendering — AMD Radeon Pro 560X via Metal
cycles.device = 'GPU'
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'METAL'
prefs.get_devices()
for device in prefs.devices:
    device.use = True  # enable all available devices

scene.render.resolution_x               = RESOLUTION
scene.render.resolution_y               = RESOLUTION
scene.render.filepath                   = OUTPUT_PATH
scene.render.image_settings.file_format = 'PNG'

# ── 9. Render ──────────────────────────────────────────────────────────────────

print(f"\nLight at z = {light_z:.4f} m")
print(f"Plane at z = {plane_z:.4f} m")
print(f"Rendering {RESOLUTION}×{RESOLUTION} @ {SAMPLES} samples...")
bpy.ops.render.render(write_still=True)
print(f"\nDone → {OUTPUT_PATH}")
