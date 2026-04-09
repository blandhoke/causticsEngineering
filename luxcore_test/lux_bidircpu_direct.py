"""Test BIDIRCPU directly via pyluxcore — same properties as working exporter test."""
import bpy, addon_utils, sys, time
import numpy as np

addon_utils.extensions_refresh(ensure_wheels=True)
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.BlendLuxCore")
import pyluxcore
pyluxcore.Init()

W, H = 32, 32
print("=== BIDIRCPU direct pyluxcore test ===", flush=True)

scene_props = pyluxcore.Properties()
scene_props.Set(pyluxcore.Property("scene.camera.type",          ["perspective"]))
scene_props.Set(pyluxcore.Property("scene.camera.lookat.orig",   [0.0, 0.0, 3.0]))
scene_props.Set(pyluxcore.Property("scene.camera.lookat.target", [0.0, 0.0, 0.0]))
scene_props.Set(pyluxcore.Property("scene.camera.up",            [0.0, 1.0, 0.0]))
scene_props.Set(pyluxcore.Property("scene.materials.white.type", ["matte"]))
scene_props.Set(pyluxcore.Property("scene.materials.white.kd",   [0.8, 0.8, 0.8]))
verts = [-1.0,-1.0,0.0,  1.0,-1.0,0.0,  1.0,1.0,0.0,  -1.0,1.0,0.0]
tris  = [0,1,2,  0,2,3]
scene_props.Set(pyluxcore.Property("scene.objects.floor.material", ["white"]))
scene_props.Set(pyluxcore.Property("scene.objects.floor.vertices", verts))
scene_props.Set(pyluxcore.Property("scene.objects.floor.faces",    tris))
scene_props.Set(pyluxcore.Property("scene.lights.pt.type",      ["point"]))
scene_props.Set(pyluxcore.Property("scene.lights.pt.position",  [0.0, 0.0, 2.0]))
scene_props.Set(pyluxcore.Property("scene.lights.pt.color",     [1.0, 1.0, 1.0]))
scene_props.Set(pyluxcore.Property("scene.lights.pt.power",     [100.0]))
scene_props.Set(pyluxcore.Property("scene.lights.pt.efficency", [17.0]))
scene_props.Set(pyluxcore.Property("scene.epsilon.min", [1e-5]))
scene_props.Set(pyluxcore.Property("scene.epsilon.max", [0.1]))

scene = pyluxcore.Scene()
scene.Parse(scene_props)
print("Scene created.", flush=True)

cfg_props = pyluxcore.Properties()
cfg_props.Set(pyluxcore.Property("renderengine.type",  ["BIDIRCPU"]))
cfg_props.Set(pyluxcore.Property("sampler.type",       ["METROPOLIS"]))
cfg_props.Set(pyluxcore.Property("film.width",         [W]))
cfg_props.Set(pyluxcore.Property("film.height",        [H]))
cfg_props.Set(pyluxcore.Property("film.filter.type",   ["NONE"]))
cfg_props.Set(pyluxcore.Property("film.opencl.enable", [0]))
cfg_props.Set(pyluxcore.Property("light.maxdepth",     [10]))
cfg_props.Set(pyluxcore.Property("path.maxdepth",      [10]))
cfg_props.Set(pyluxcore.Property("lightstrategy.type", ["LOG_POWER"]))
cfg_props.Set(pyluxcore.Property("renderengine.seed",  [1]))
cfg_props.Set(pyluxcore.Property("batch.haltspp",      [5]))
cfg_props.Set(pyluxcore.Property("batch.halttime",     [0]))
cfg_props.Set(pyluxcore.Property("sampler.metropolis.largesteprate",      [0.4]))
cfg_props.Set(pyluxcore.Property("sampler.metropolis.maxconsecutivereject",[512]))
cfg_props.Set(pyluxcore.Property("sampler.metropolis.imagemutationrate",  [0.1]))
cfg_props.Set(pyluxcore.Property("film.imagepipelines.000.0.type",  ["NOP"]))
cfg_props.Set(pyluxcore.Property("film.imagepipelines.000.1.type",  ["TONEMAP_LINEAR"]))
cfg_props.Set(pyluxcore.Property("film.imagepipelines.000.1.scale", [1.0]))

print("Building RenderConfig...", flush=True)
t0 = time.time()
rcfg = pyluxcore.RenderConfig(cfg_props, scene)
print(f"RenderConfig built in {time.time()-t0:.3f}s", flush=True)

print("Creating RenderSession... (timeout=20s)", flush=True)
t1 = time.time()
# The following line will either complete quickly or hang on OpenCL enumeration
session = pyluxcore.RenderSession(rcfg)
print(f"RenderSession created in {time.time()-t1:.2f}s ← BIDIR DIRECT WORKS!", flush=True)

session.Start()
deadline = time.time() + 15
while not session.HasDone():
    if time.time() > deadline:
        print("TIMEOUT", flush=True); break
    print(f"  spp={session.GetStats().Get('stats.renderengine.pass').GetInt()}", flush=True)
    time.sleep(1)
session.Stop()
print(f"Done in {time.time()-t0:.1f}s", flush=True)
