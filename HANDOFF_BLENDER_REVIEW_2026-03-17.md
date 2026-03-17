# HANDOFF — Blender Viewport Review + Pre-CNC Clarifications
# Date: 2026-03-17
# From: Claude Code
# To: Claude Chat (Blender MCP)

---

## Your Mission

Two tasks:

1. **Load the preprocessing test meshes into Blender and organize them for visual review.**
   Bland needs to compare the surface shapes before choosing which mesh to send to the CNC.

2. **Ask Bland the questions in the "Clarifications Needed" section at the bottom.**
   There are several untracked files from parallel sessions that need decisions before
   Claude Code can clean up and prepare final G-code.

---

## Context: What the Meshes Are

This project cuts an acrylic lens on a CNC router. Sunlight through the lens projects
a caustic (concentrated light pattern) onto the floor. The target image was an inkbrush
painting.

A 16-quadrant preprocessing sweep was just completed. The question was: does preprocessing
the input image before feeding it to the Julia solver improve the caustic quality?

**Result:** Bandpass filtering (preserving mid-spatial frequencies, removing flat and noise)
produced the best results at NORMAL (512px) resolution.

---

## Meshes to Load

Load these four OBJ files into the same Blender scene for side-by-side comparison.
All are in metres. All need to be scaled to 8"×8" (0.2032m) to compare fairly.

### Mesh A — Original inkbrush (no preprocessing, baseline)
```
/Users/admin/causticsEngineering/Final cows/inkbrush/normal/mesh.obj
```
- Relief (dome height, caustic surface only): **1.959mm = 0.077"**
- Surface height std: **1.354mm** (rich curvature, full photographic gradient encoding)
- Edge correlation (r): 0.014 (solver encoded brightness gradients, not edges)
- G-code already generated from this mesh — see clarification questions below
- Scale: native XY span = 0.10000m → scale 2.032× to get 8"×8"

### Mesh B — Bandpass σ_lo=2, σ_hi=32 (mid-frequency, broad band)
```
/Users/admin/causticsEngineering/examples/block4_normal/block4_q3_normal_hyper.obj
```
- Surface height std: **1.336mm** (nearly matches original — rich curvature)
- Edge correlation (r): **0.101** (7× better than original at correlating with caustic edges)
- Scale: native XY span ≈ 0.1001m → scale 2.030× to get 8"×8"
- Note: filename has `_hyper` suffix but this is a NORMAL (512px, ~526k face) mesh

### Mesh C — Bandpass σ_lo=1, σ_hi=8 (mid-frequency, narrow band)
```
/Users/admin/causticsEngineering/examples/block4_normal/block4_q4_normal_hyper.obj
```
- Surface height std: **1.332mm** (nearly matches original)
- Edge correlation (r): **0.104** (marginally better than Mesh B)
- Scale: native XY span ≈ 0.1001m → scale 2.030× to get 8"×8"
- Note: same filename artifact — this is a NORMAL mesh

### Mesh D — Differentiable renderer optimization result (experimental)
```
/Users/admin/causticsEngineering/examples/diffrender/optimized_lens.obj
```
- Status: UNKNOWN — this came from an optimization experiment that ran 5 iterations
- May be partially optimized or non-physical — show it but flag it as experimental
- Scale: unknown, check native XY span and scale to 0.2032m if reasonable

---

## How to Organize in Blender

1. Import each mesh with `forward_axis='Y', up_axis='Z'`

2. Scale each to 8"×8" (see scale factors above):
   ```python
   # Example for Mesh A
   obj = bpy.data.objects['mesh']
   scale = 0.2032 / 0.10000   # 2.032
   obj.scale = (scale, scale, scale)
   bpy.ops.object.transform_apply(scale=True)
   ```

3. Arrange in a 2×2 grid (or horizontal row):
   - X offset 0.250m between meshes (leaves ~24mm gap between 8" pieces)
   - Label each with a text object: "A: Original", "B: Bandpass 2-32", "C: Bandpass 1-8", "D: DiffRender"

4. Set viewport shading to **Material Preview** or **Solid with Matcap** to show surface curvature clearly.

5. Key things for Bland to look at:
   - Is the surface relief visibly similar between A, B, and C? (It should be — all ~1.33-1.35mm std)
   - Does D (diffrender) look physically reasonable or distorted?
   - Are there any visible artifacts, holes, or discontinuities in B and C?

---

## Render Thumbnails (Already Available)

If Blender MCP has trouble with any mesh, these pre-rendered Mitsuba thumbnails are available
for comparison in Claude Chat:

- `claude_chat_handoff4/block4_q3_normal_thumb.png` — Mesh B caustic render
- `claude_chat_handoff4/block4_q4_normal_thumb.png` — Mesh C caustic render
- `claude_chat_handoff4/block4_results_contact.png` — All block4 results (4-panel)
- `luxcore_test/inkbrush_caustic_normal.png` — Mesh A caustic reference render

---

## ⚠ Clarifications Needed from Bland

Ask these questions. Claude Code cannot proceed to G-code export without answers.

---

### Question 1: G-code files — which one is going to the machine?

Two G-code files exist. Ask Bland:

> "There are two G-code files in the project folder. Can you tell me what each one is?
>
> - **test_caustic_finish.nc** (22MB) — 1,601 rows at 0.005" stepover, 1/16" ball nose bit, ~187 min runtime
> - **test_caustic_v12.nc** (29MB) — 1,311 columns at 0.01250" stepover, 1/8" ball nose bit, includes roughing pass
>
> Are these test files from a previous session, or is one of them ready to send to the Blue Elephant?
> Which bit are you planning to use — 1/16" or 1/8"?
> And which mesh was used to generate them — is it the original inkbrush mesh, or one of the new bandpass meshes?"

---

### Question 2: trim_caustic_obj.py — has the base slab been removed?

A script called `trim_caustic_obj.py` was written in a previous session. It strips the
flat base slab from the bottom half of the mesh before G-code export.

> "The CNC pipeline has a script called `trim_caustic_obj.py` that removes the flat underside
> from the mesh before sending it to the CNC. The original mesh has two vertex layers — a
> flat base slab (not needed for cutting) and the caustic surface on top.
>
> Was `trim_caustic_obj.py` applied when generating `test_caustic_v12.nc`?
> If not, the G-code may include unnecessary cuts into flat material.
>
> The HANDOFF_GCODE_SETTINGS file says the base slab was 'detected and ignored' —
> so CAUSTICFORGE may handle this automatically. Can you confirm?"

---

### Question 3: Differentiable optimization — pursue or discard?

`optimize_caustic.py` and `examples/diffrender/` are from an experiment that tried to
refine the lens mesh using Mitsuba's differentiable renderer (backpropagation through
the caustic render to optimize vertex positions).

> "There's an experimental folder called `diffrender/` with a script that tries to
> improve the lens mesh using AI-style optimization (gradient descent through the
> light simulation). It ran for 5 steps and produced an `optimized_lens.obj`.
>
> Is this something you want to explore further, or was it a dead end?
> Should Claude Code commit this experiment to git, or delete it?"

---

### Question 4: Mitsuba render script vs Python ray tracer

`render_mitsuba.py` was added. The existing pipeline uses `simulate_normal.py` (Python
forward ray tracer). Mitsuba ptracer is more physically accurate but slower for caustics.

> "There's a new Mitsuba render script (`render_mitsuba.py`) in addition to the existing
> Python ray tracer (`simulate_normal.py`). Are you planning to use Mitsuba for caustic
> verification going forward, or was `render_mitsuba.py` just a test?
>
> The 16-quadrant pipeline already uses Mitsuba for its renders — so this may be redundant.
> Should Claude Code clean it up or keep it?"

---

### Question 5: CAUSTICFORGE addon status

The G-code settings handoff mentions a Blender addon:
```
/Users/admin/Library/Application Support/Blender/4.3/scripts/addons/causticforge_v1.py
```

> "There's a CAUSTICFORGE Blender addon that was used to generate the G-code. Is this
> addon actively installed and working in your Blender? The handoff notes mention a few
> known bugs (unit display bug, BVH timeout for large meshes). Should Claude Code review
> and fix those bugs before the next G-code export?"

---

## Decision Point After Bland Answers

Once Bland confirms which mesh to use for CNC:

1. **If Mesh A (original inkbrush):** G-code may already be done — just verify `test_caustic_v12.nc` was generated from the correct mesh and matches the bit/stepover Bland wants.

2. **If Mesh B or C (bandpass):** Claude Code will need to regenerate G-code using CAUSTICFORGE with the new OBJ. The `trim_caustic_obj.py` step may need to run first.

3. **In either case:** Claude Code should commit all the untracked files (or delete the ones Bland doesn't want) before the CNC session.

---

## Files Claude Code Will NOT Touch Without Answers

- `test_caustic_finish.nc` — G-code for CNC — do not overwrite
- `test_caustic_v12.nc` — G-code for CNC — do not overwrite
- `examples/diffrender/optimized_lens.obj` — may be wanted
- `causticforge_v1.py` (Blender addon) — in user's Library, not in project repo
