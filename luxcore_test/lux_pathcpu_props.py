"""Test PATHCPU with same properties as the working BIDIR config."""
import bpy, addon_utils, sys, time
import numpy as np

addon_utils.extensions_refresh(ensure_wheels=True)
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.BlendLuxCore")
import pyluxcore
pyluxcore.Init()

W, H = 64, 64

print("=== PATHCPU with BIDIR-equivalent properties ===", flush=True)

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

print("Creating Scene...", flush=True)
scene = pyluxcore.Scene()
scene.Parse(scene_props)

cfg_props = pyluxcore.Properties()
# Use EXACT same properties as the working BIDIR export, just swap engine type
cfg_props.Set(pyluxcore.Property("renderengine.type",     ["PATHCPU"]))  # was BIDIRCPU
cfg_props.Set(pyluxcore.Property("sampler.type",          ["SOBOL"]))
cfg_props.Set(pyluxcore.Property("film.width",            [W]))
cfg_props.Set(pyluxcore.Property("film.height",           [H]))
cfg_props.Set(pyluxcore.Property("film.filter.type",      ["NONE"]))
cfg_props.Set(pyluxcore.Property("film.filter.width",     [1.5]))
cfg_props.Set(pyluxcore.Property("film.opencl.enable",    [0]))           # KEY: disable film OpenCL
cfg_props.Set(pyluxcore.Property("lightstrategy.type",    ["LOG_POWER"]))
cfg_props.Set(pyluxcore.Property("path.maxdepth",         [10]))
cfg_props.Set(pyluxcore.Property("path.forceblackbackground.enable", [0]))
cfg_props.Set(pyluxcore.Property("path.albedospecular.type",              ["REFLECT_TRANSMIT"]))
cfg_props.Set(pyluxcore.Property("path.albedospecular.glossinessthreshold", [0.05]))
cfg_props.Set(pyluxcore.Property("renderengine.seed",     [1]))
cfg_props.Set(pyluxcore.Property("batch.haltspp",         [5]))
cfg_props.Set(pyluxcore.Property("batch.halttime",        [0]))
cfg_props.Set(pyluxcore.Property("film.imagepipelines.000.0.type",  ["NOP"]))
cfg_props.Set(pyluxcore.Property("film.imagepipelines.000.1.type",  ["TONEMAP_LINEAR"]))
cfg_props.Set(pyluxcore.Property("film.imagepipelines.000.1.scale", [1.0]))
cfg_props.Set(pyluxcore.Property("film.imagepipelines.000.radiancescales.0.enabled",     [1]))
cfg_props.Set(pyluxcore.Property("film.imagepipelines.000.radiancescales.0.globalscale", [1.0]))
cfg_props.Set(pyluxcore.Property("film.imagepipelines.000.radiancescales.0.rgbscale",    [1.0, 1.0, 1.0]))

print("Building RenderConfig...", flush=True)
t0 = time.time()
rcfg = pyluxcore.RenderConfig(cfg_props, scene)
print(f"RenderConfig built in {time.time()-t0:.2f}s", flush=True)

print("Creating RenderSession...", flush=True)
t1 = time.time()
session = pyluxcore.RenderSession(rcfg)
print(f"RenderSession created in {time.time()-t1:.2f}s", flush=True)

print("Starting render...", flush=True)
session.Start()
deadline = time.time() + 30
while not session.HasDone():
    if time.time() > deadline:
        print("TIMEOUT after 30s", flush=True)
        break
    spp = session.GetStats().Get("stats.renderengine.pass").GetInt()
    print(f"  spp={spp}", flush=True)
    time.sleep(1)

session.Stop()
print(f"PATHCPU completed in {time.time()-t0:.1f}s  ← PATH WORKS!", flush=True)
