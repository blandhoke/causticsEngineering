"""Dump all RenderConfig properties that BlendLuxCore generates for BIDIR."""
import bpy, addon_utils, sys, time

addon_utils.extensions_refresh(ensure_wheels=True)
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.BlendLuxCore")
import pyluxcore

# Minimal scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.mesh.primitive_plane_add(size=2, location=(0,0,-1))
ld = bpy.data.lights.new("L", 'POINT'); ld.energy = 1000
lo = bpy.data.objects.new("L", ld); lo.location = (0,0,3)
bpy.context.collection.objects.link(lo)
cd = bpy.data.cameras.new("C")
co = bpy.data.objects.new("C", cd); co.location = (0,0,5)
bpy.context.collection.objects.link(co)
bpy.context.scene.camera = co

scene = bpy.context.scene
scene.render.engine = 'LUXCORE'
scene.luxcore.config.engine  = 'BIDIR'
scene.luxcore.config.sampler = 'METROPOLIS'
scene.luxcore.halt.enable      = True
scene.luxcore.halt.use_samples = True
scene.luxcore.halt.samples     = 5
scene.render.resolution_x = 32
scene.render.resolution_y = 32

depsgraph  = bpy.context.evaluated_depsgraph_get()
statistics = scene.luxcore.statistics.get_active()
from bl_ext.user_default.BlendLuxCore import export

class FE:
    is_preview = False; session = None; exporter = None
    aov_imagepipelines = {}; DENOISED_OUTPUT_NAME = "DENOISED"
    def update_stats(self, *a): pass
    def update_progress(self, *a): pass
    def test_break(self): return False
    def report(self, *a): pass
    def error_set(self, *a): pass
    def begin_result(self, *a, **k): return None
    def end_result(self, *a, **k): pass

print("\n=== BIDIR export properties ===", flush=True)
exp = export.Exporter(statistics)

# Monkey-patch to capture the RenderConfig before session starts
original_render_session = pyluxcore.RenderSession.__init__

captured_rcfg = [None]
def patched_init(self, rcfg, *args, **kwargs):
    captured_rcfg[0] = rcfg
    raise RuntimeError("CAPTURE_DONE")

pyluxcore.RenderSession.__init__ = patched_init

try:
    session = exp.create_session(depsgraph, engine=FE(), view_layer=depsgraph.view_layer_eval)
except RuntimeError as e:
    if "CAPTURE_DONE" in str(e):
        rcfg = captured_rcfg[0]
        if rcfg:
            props = rcfg.GetProperties()
            keys = props.GetAllNames()
            print(f"Config property count: {len(keys)}", flush=True)
            for k in sorted(keys):
                v = props.Get(k)
                print(f"  {k} = {v.GetValuesString()}", flush=True)
        else:
            print("No RenderConfig captured", flush=True)
    else:
        raise

pyluxcore.RenderSession.__init__ = original_render_session
print("=== Done ===", flush=True)
