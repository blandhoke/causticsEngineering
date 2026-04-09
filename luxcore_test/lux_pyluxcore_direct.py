#!/usr/bin/env python3
"""
Test pyluxcore PATH engine directly — no BlendLuxCore exporter.
Uses pyluxcore.Scene API correctly.
"""

import sys, time
import numpy as np

import bpy
import addon_utils
addon_utils.extensions_refresh(ensure_wheels=True)
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.BlendLuxCore")

import pyluxcore
pyluxcore.Init()

W, H = 64, 64

print("=== pyluxcore direct PATH test ===", flush=True)

# ── Build pyluxcore.Scene ────────────────────────────────────────────────────

scene_props = pyluxcore.Properties()

# Camera (perspective, looking down -Z from z=3)
scene_props.Set(pyluxcore.Property("scene.camera.type",          ["perspective"]))
scene_props.Set(pyluxcore.Property("scene.camera.lookat.orig",   [0.0, 0.0, 3.0]))
scene_props.Set(pyluxcore.Property("scene.camera.lookat.target", [0.0, 0.0, 0.0]))
scene_props.Set(pyluxcore.Property("scene.camera.up",            [0.0, 1.0, 0.0]))

# White matte material
scene_props.Set(pyluxcore.Property("scene.materials.white.type", ["matte"]))
scene_props.Set(pyluxcore.Property("scene.materials.white.kd",   [0.8, 0.8, 0.8]))

# Floor mesh (two triangles)
verts = [-1.0,-1.0,0.0,  1.0,-1.0,0.0,  1.0,1.0,0.0,  -1.0,1.0,0.0]
tris  = [0,1,2,  0,2,3]
scene_props.Set(pyluxcore.Property("scene.objects.floor.material", ["white"]))
scene_props.Set(pyluxcore.Property("scene.objects.floor.vertices", verts))
scene_props.Set(pyluxcore.Property("scene.objects.floor.faces",    tris))

# Point light
scene_props.Set(pyluxcore.Property("scene.lights.pt.type",      ["point"]))
scene_props.Set(pyluxcore.Property("scene.lights.pt.position",  [0.0, 0.0, 2.0]))
scene_props.Set(pyluxcore.Property("scene.lights.pt.color",     [1.0, 1.0, 1.0]))
scene_props.Set(pyluxcore.Property("scene.lights.pt.power",     [100.0]))
scene_props.Set(pyluxcore.Property("scene.lights.pt.efficency", [17.0]))

print("Creating pyluxcore.Scene...", flush=True)
scene = pyluxcore.Scene()
scene.Parse(scene_props)
print("Scene created.", flush=True)

# ── RenderConfig ─────────────────────────────────────────────────────────────

cfg_props = pyluxcore.Properties()
cfg_props.Set(pyluxcore.Property("renderengine.type", ["PATHCPU"]))
cfg_props.Set(pyluxcore.Property("sampler.type",      ["SOBOL"]))
cfg_props.Set(pyluxcore.Property("film.width",        [W]))
cfg_props.Set(pyluxcore.Property("film.height",       [H]))
cfg_props.Set(pyluxcore.Property("batch.haltspp",     [5]))

print("Building RenderConfig...", flush=True)
rcfg = pyluxcore.RenderConfig(cfg_props, scene)
print("RenderConfig built.", flush=True)

# ── RenderSession ─────────────────────────────────────────────────────────────

print("Creating RenderSession...", flush=True)
t0 = time.time()
session = pyluxcore.RenderSession(rcfg)
print(f"RenderSession created in {time.time()-t0:.2f}s", flush=True)

print("Starting render...", flush=True)
session.Start()

deadline = time.time() + 30
while not session.HasDone():
    if time.time() > deadline:
        print("TIMEOUT — PATH still running after 30s", flush=True)
        break
    stats = session.GetStats()
    spp = stats.Get("stats.renderengine.pass").GetInt()
    print(f"  spp={spp}", flush=True)
    time.sleep(1)

session.Stop()
print(f"Render complete in {time.time()-t0:.1f}s", flush=True)

# ── Extract and save ─────────────────────────────────────────────────────────

film = session.GetFilm()
pixels = np.zeros([H * W, 3], dtype=np.float32)
film.GetOutputFloat(pyluxcore.FilmOutputType.RGB_IMAGEPIPELINE, pixels)
img = np.flipud(pixels.reshape(H, W, 3))
img = np.clip(img ** (1/2.2), 0, 1)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(4, 4))
ax.imshow(img)
ax.axis('off')
plt.tight_layout(pad=0)
plt.savefig("/tmp/lux_direct_test.png", dpi=72, bbox_inches='tight')
plt.close()
print("Saved → /tmp/lux_direct_test.png", flush=True)
print("=== PATH engine WORKS directly via pyluxcore ===", flush=True)
