# Deep Research Report on Caustic Image Generation Methods for CNC-Milled Cast Acrylic

## Scope and the physical bottlenecks that decide contrast and resolution

This report treats “generating caustic images” as **computationally designing an optical element** (usually reflective or refractive) so that illumination forms a **prescribed irradiance pattern** (an “image”) on a target plane or along a 3D trajectory. Classic “forward” caustics rendering (simulate a given object) matters here mainly because most inverse methods need a fast, stable forward model somewhere in the loop. citeturn5view1turn43view0turn16view0

For **CNC-milled cast acrylic caustic windows** (your stated goal), the limiting factors for “ultra high resolution” and “high contrast” are usually not the mesh export step—they’re these:

A caustic “image” is effectively a **ray-density redistribution problem**, so any **non-ideal source extent** (LED die size, diffuser, finite distance, divergence) smears high frequencies and kills black levels. This is explicitly called out in recent caustic-design work as a core limitation of point/parallel-source assumptions and as a motivation for surface-light-source modeling. fileciteturn0file1 citeturn16view0

Even if the math is perfect, **surface roughness / incomplete polishing** introduces scattering that behaves like blur + veiling glare, raising the “black floor.” The “Caustic Art” technical report and entity["people","Matt Ferraro","causticsengineering author"]’s machining write-up both treat polishing/specularity as a primary practical constraint. citeturn19view0turn6view1

The “single-surface heightfield” assumption (flat entry face, sculpted exit face) is common because it fabricates well. In Yue et al.’s Poisson method, they assume incident light is nearly parallel/normal so the entry face can be treated as non-refracting, and only the exit face is designed. citeturn9view0

Finally, high-contrast solutions often require strong local ray bending. That increases the risk of internal reflections / pathological geometry; Schwartzburg et al. explicitly motivate L2-optimal transport as a way to reduce overall ray-direction change, helping fabrication and avoiding defects like internal reflections. citeturn10view0

## Research taxonomy of caustic image generation methods

Across optics / graphics / fabrication papers and open implementations, “make a surface that projects an image” collapses into a small set of *method families*.

image_group{"layout":"carousel","aspect_ratio":"16:9","query":["high-contrast computational caustic design acrylic prototype brain","magic window caustic lens acrylic slab projecting image","CNC milled acrylic caustic lens shadow image"],"num_per_query":1}

### Analysis-by-synthesis and stochastic optimization

The earliest “general” approach is: pick a surface parameterization, repeatedly render a caustic image, and optimize surface parameters to reduce image error. Finckh et al. use an **analysis-by-synthesis loop** accelerated on GPU, driven by **Simultaneous Perturbation Stochastic Approximation (SPSA)**. They frame the objective as caustic-image error (MSE) and update a mesh/B-spline surface iteratively. citeturn43view0

This family is flexible (you can swap light model, geometry, constraints), but is compute-expensive because rendering dominates runtime, and it tends to struggle with weak-intensity regions unless you add specialized regularizers. That weakness is also echoed in later surveys/related-work sections that position OT/PDE methods as solutions to those artifacts/costs. citeturn16view0turn43view0

### Patch/microfacet decomposition and combinatorial arrangement

Instead of one smooth freeform surface, Papas et al. (“Goal-Based Caustics”) decompose a target image into a **set of (anisotropic) Gaussian kernels**, then build an **array of continuous micro-patches**, each focusing light onto one kernel via refraction/reflection. They must then **assign/arrange** patches to target kernels (a discrete optimization), and they fabricate by milling. citeturn26view0turn25view0

This tends to produce striking results at relatively low “design complexity,” but it has an intrinsic discretization: the image is approximated by a finite mixture of kernels and a finite patch set, so very fine, continuous-tone behavior and deep blacks can be harder than with continuous-surface OT formulations. citeturn26view0turn9view0turn7view3

### Poisson/PDE-based continuous mapping plus normal/height reconstruction

Yue et al. explicitly classify previous caustic design approaches into (a) random perturbation and (b) compute a light correspondence, then build the surface. Their contribution is to compute a **continuous, energy-preserving mapping** between incident domain and screen domain, and then compute the surface; both steps are formulated via **Poisson’s equation**. citeturn9view0

A practical rendition of this exact pipeline appears in Ferraro’s “Magic Window” write-up: (1) **warp cells** so cell area matches target brightness while maintaining continuity, using a Poisson equation to generate a smooth velocity field, then (2) compute target normals via Snell and integrate to a heightmap again using Poisson with Neumann boundary conditions. citeturn6view1turn5view0

This family is popular because Poisson solves are stable, fast, and map cleanly into “heightfield → mesh → CNC” workflows. It is also directly implemented in open codebases you can mine. citeturn2view1turn4view0turn6view1

### Optimal transport (OT) for correspondence, then surface recovery

OT methods treat caustic design as mass transport: move source irradiance to target irradiance while optimizing some transport cost. In practice, OT provides a correspondence that is (ideally) **curl-free** (gradient of a potential), which is exactly what you want for stable normal/height integration. The fast_caustic_design README explicitly leans on this: “by Brenier’s theorem” an optimal plan is a gradient field, and if you lose that property, normal integration distorts the lens. citeturn41view0

There are two major OT subfamilies in caustics:

**High-contrast OT with power diagrams (Schwartzburg et al.)**  
Schwartzburg et al. introduce an OT formulation that supports **piecewise smooth surfaces** and **non-bijective mappings**, which they argue enables a richer space of images including **completely black regions** and **singularities (infinite density lines/points)**. Their discrete OT computation uses **Voronoi/power diagrams** (Laguerre diagrams) and then a 3D optimization to fit a surface whose normals match the OT-induced normal field. citeturn10view1turn10view3turn10view2 fileciteturn0file2

They also report scaling behavior and timings where OT dominates runtime and they reached **million-sample** cases (hours on older hardware). citeturn10view4

**General OT / “visibility diagram” variants (Meyron et al.)**  
Meyron et al. (“Light in Power”) unify multiple caustic/non-imaging design problems under one light-energy conservation equation and solve them via intersecting a **3D power diagram** with planar/spherical domains to form “visibility cells,” then using a **damped Newton method**. They emphasize fabrication constraints like convexity/concavity as part of practical optics manufacturing. citeturn14view0turn13view0

### Fast approximate OT on grids (OTMap) powering practical lens generators

Nader & Guennebaud’s “Instant Transport Maps on 2D Grids” proposes a very fast solver for **L2-optimal maps from an arbitrary grid density to a uniform square**, and then recovers maps between general densities via inversion/composition—continuous and density-preserving but only approximately optimal. citeturn42view1turn42view0

This is directly used as the backbone of the open-source **fast_caustic_design** pipeline: OTMap gives a fast transport map, then inverse Snell gives target normals, then a nonlinear solve performs normal integration. Their README is unusually explicit about limitations: composition can introduce curl, causing distortions, and supporting non-square apertures requires rethinking the discrete operators / mesh domain. citeturn41view0turn2view0

### Differentiable rendering and end-to-end surface optimization

Recent work increasingly treats caustic design as true inverse rendering with differentiable simulators.

Sun et al. (“End-to-end Surface Optimization for Light Control”) iterate between a **face-based optimal transport correspondence update** and a **rendering-guided optimization** directly driven by image difference, and they explicitly discuss this as a route to (a) escaping local minima and (b) preserving details. They also discuss high-contrast issues and cite Schwartzburg-style non-bijective OT as key to pure-black regions. citeturn29view1turn30search6

Zhou et al. (“Computational Caustic Design for Surface Light Source”) focuses on the real killer in physical setups: most methods assume point/collimated sources, but real lights are extended. They propose (1) an **optimizable surface-light-source model** approximated by multiple point sources and (2) a **flux-based differentiable rendering model** for lens optimization, solved with L-BFGS (after a contraction mapping to remove constraints). They also compare against Mitsuba 3 and claim advantages in contrast/accuracy for caustic design. citeturn16view0turn17search11 fileciteturn0file1

The tool ecosystem enabling this includes differentiable renderers like **Mitsuba 3**, which exposes derivatives w.r.t. geometry/materials and has a public codebase. citeturn28search10turn28search14

### Wave-optics / diffractive and metasurface caustics

This is mostly *not* your CNC-acrylic lane, but it’s a complete “method family” researchers use to generate caustic-like images/patterns:

Sun et al. explicitly point out that inverse design extends to wave optics (e.g., Gerchberg–Saxton-style holography and full-color caustic generators using holographic optical elements). citeturn29view1turn24search23

Separate optics work engineers caustic fields via metasurfaces/phase design, including 3D-printed metasurfaces that shape caustic trajectories. citeturn15search21

The key takeaway for your project is that wave-optics methods are powerful for microscopic/phase devices but do not naturally output “a millable acrylic heightfield lens,” unless you’re deliberately approximating a phase mask with a thickness profile and you accept chromatic/diffraction behavior. citeturn29view1turn15search21

## Matrix of variables and method-by-method evaluation for CNC-milled acrylic

### Variables used in this matrix

I used these variables because they map directly to “ultra high-resolution + high-contrast + CNC acrylic” feasibility:

**Optical model** (geometric-ray vs wave), **source model** (collimated/point vs extended), **parameterization** (heightfield mesh vs patches vs general surface), **correspondence method** (stochastic, Poisson/PDE, OT), **supports true-black / singularities**, **fabrication constraints integrated**, **scalability**, **outputs mesh**, **open code availability**.

### Evaluation matrix

Legend:  
**Black/singularities** = can *intentionally* create deep-black regions or singular curves/points without collapsing the method.  
**Mesh output** = directly produces heightfield/mesh suitable for export to OBJ/STL (possibly after “solidify”).  
**Open code** = public implementation you can realistically lift into Python or call from Python.

| Method family (representative) | Optical model & source assumptions | Surface parameterization | Correspondence / solver core | Black / singularities | Fabrication-aware constraints | Mesh output | Open code / practical access |
|---|---|---|---|---|---|---|---|
| Analysis-by-synthesis (Finckh et al. 2010) | Rays; general point/scene setups possible, but in-loop rendering dominates | Mesh or B-spline surface; optimize z control points | GPU caustic rendering + SPSA; MSE objective | Not a focus; weak-intensity control noted as hard later | Possible but not central in the method | Yes (implicit in surface representation) | Paper PDF available; implementation details described but not turnkey code in that PDF citeturn43view0 |
| Micro-patch / Gaussian mixture (Goal-Based Caustics) | Rays; typically collimated-ish; patch focusing onto kernels | Array of continuous micro-patches | Nonnegative image decomposition into Gaussians + discrete assignment/arrangement | Limited by mixture/patch discretization vs continuous OT | Patch size/arrangement interacts with manufacturability | Yes (patch geometry to mill) | Project page & slides accessible; paper PDF fetch blocked in this environment, but technical description is clear citeturn26view0turn25view0 |
| Brightness warping (Caustic Art, 2012) | Rays; reflective or refractive; focuses on heightfield optics | Quadrilateral mesh / heightfield; normals integrated to heightfield | Optimize patch areas to match brightness; integrability term; gradient-based optimization | Not presented as “true black” method; aims at faithful reproduction under assumptions | Indirectly—heightfields and smoothness favor milling; polishing emphasized as limit | Yes | PDF available; algorithm family described with manufacturing perspective citeturn19view0 |
| Poisson continuous-surface (Yue et al. 2014) | Rays; assumes nearly parallel/normal incidence so entry face ignored | Single-valued exit surface heightfield | Continuous mapping + Poisson solves (mapping and surface) | Produces smooth images; later work argues it struggles with pure black/high contrast | Not explicit CNC constraint optimization, but heightfield is fabrication-friendly | Yes | Full paper PDF available; multiple open implementations exist (below) citeturn9view0 |
| High-contrast OT with power diagrams (Schwartzburg et al. 2014) | Rays; computes source irradiance then OT to target | Piecewise smooth surface; supports discontinuities in normal field | Semi-discrete OT via Voronoi/power diagrams; then 3D surface optimization | Yes: explicitly supports non-bijective mapping, singularities, and black regions citeturn10view1turn10view2 | Mentions fabrication & reducing ray deflection to avoid issues | Yes | Authors’ code not released per replicability review, but reimplementations exist citeturn36view0turn37view0 fileciteturn0file2 |
| General OT / visibility diagrams (Light in Power) | Rays; multiple problem types (mirror/lens, point/collimated, near/far) | Polyhedral/segmented surfaces; convex/concave variants | 3D power diagram intersection (“visibility cells”) + damped Newton | Can hit exact energy constraints; contrast depends on target discretization | Strong: explicitly discusses convex/concave for milling/molds | Yes | Paper accessible via arXiv/ar5iv; code not linked on arXiv page; but key subroutines have open libraries citeturn13view0turn14view0 |
| Fast grid OT (OTMap / Instant Transport Maps) | OT on 2D grids; exact L2 map to uniform square; approx elsewhere | Produces transport maps; downstream surface is your integration step | Fast iterative OT solver + inversion/composition | Not inherently; depends on downstream surface recovery and OT approximation error | Not directly | Indirect | Open C++ code; used in fast_caustic_design citeturn42view0turn42view1 |
| OTMap-based practical lens generator (fast_caustic_design) | Rays; designed for caustic “shadow image” projection | Square heightfield-ish lens mesh | OTMap for correspondence + inverse Snell + normal integration via Ceres | High contrast in practice; but admits distortions if OT has curl and is approx | Limited fabrication constraints; major practical limitation is square-only domain | Yes (exports model; workflow described) | Open repo; very explicit documentation of algorithm + limitations citeturn41view0turn2view0 |
| Poisson-based generator implementation (poisson_caustic_design) | Rays; aligns with Yue-style approach | Heightfield lens; also “solidified OBJ” export | Poisson-based algorithm; multithreaded Poisson solver | Better continuous-tone than discrete patches; weaker than high-contrast OT | Limited explicit constraints; includes focal length/thickness knobs | Yes | Open repo; explicitly exports solidified OBJ and simulatable outputs citeturn3view4 |
| End-to-end differentiable mesh optimization (End-to-end Surface Optimization for Light Control) | Rays; uses differentiable rendering + OT updates | Full surface mesh; OT on faces (semi-discrete OT) | Alternates OT correspondence and gradient optimization; aims to preserve details | Reports better high-contrast handling than earlier smooth-only methods | Explicitly mentions fabrication constraints and CNC prototypes in abstract | Yes | Paper accessible; I did not find an official public repo in the sources retrieved here citeturn29view1turn30search6 |
| Surface-light-source-aware differentiable caustics (Zhou et al. 2025) | Rays + flux formulation; explicitly models extended planar light sources | Front plane + back freeform mesh; triangle mesh with one-to-one correspondence | Optimize discrete point-source approximation of surface emitter + flux-based differentiable rendering; L-BFGS | Aims to reduce blur due to non-ideal light; contrast improves vs point-source design | Focus is source realism; fabrication mentioned as missing in other renderers; they include prototypes | Yes | Paper accessible on arXiv; code not identified in retrieved sources citeturn16view0turn17search11 fileciteturn0file1 |
| 3D caustic-pattern design with freeform optics (Optica 2023) | Flux transport + addresses diffraction limitations of geometric optics | Discretized freeform surface points; targets are discrete spatial points | Based on a Monge–Kantorovich dual formulation; iterative mapping between mesh points and targets | Designed for sculpting trajectories/3D patterns rather than 2D images | Not primarily about CNC acrylic windows; more about optical field tailoring | Potentially, but depends on implementation | Paper accessible; code not found in retrieved sources fileciteturn0file0 citeturn17search0 |

### Key findings extracted from the matrix

The methods that reliably produce **deep black regions and sharp, high-contrast features** are the ones that allow **discontinuities / non-bijective behavior in the mapping**, i.e., Schwartzburg-style OT. Smooth-only PDE approaches (classic Poisson mapping) systematically struggle when the target demands discontinuous intensity transitions. citeturn10view1turn10view2turn9view0turn29view1

If your illumination is anything like a real LED area emitter, the best-designed lens will still blur unless the method models the source extent. Among the surveyed material, Zhou et al.’s surface-light-source model is the most directly targeted fix. citeturn16view0turn17search11 fileciteturn0file1

The highest “pipeline readiness” (generate mesh + go fabricate) among open tools today is **fast_caustic_design** and **poisson_caustic_design**: both export geometry and document focal length/thickness/resolution parameters; fast_caustic_design is explicitly positioned as faster/higher contrast than the Poisson implementation. citeturn3view4turn41view0

## Publicly available codebases, tools, and building blocks you can feed to Claude Code

### End-to-end “make a lens mesh” generators

The most immediately useful repos for your stated pipeline (“generate OBJ for milling, validate by rendering”):

dylanmsu/fast_caustic_design: OTMap-based, exports a 3D model, explicitly documents (a) optimal transport role, (b) inverse Snell → normals, (c) normal integration via Ceres, plus the caveat that it currently produces **square** lenses and why. citeturn41view0turn2view0

dylanmsu/poisson_caustic_design: implements Yue et al.’s Poisson-based continuous surface method, exports a **solidified .obj**, supports multi-thread Poisson solving, and even exports an inverse transport map. citeturn3view4turn2view1

MattFerraro/causticsEngineering: Julia repo that generates 3D surface meshes; the linked write-up is a readable derivation of Poisson-based caustic design and includes explicit manufacturing notes (height variation on the order of mm, CAM workflow, polishing). citeturn4view0turn6view1turn5view0

briefkasten1988/Caustic-Image: ports Ferraro/Yue-style approach to MATLAB and exports STL (useful if you want a second reference implementation to cross-check your Python). citeturn40view0turn6view1

CompN3rd/ShapeFromCaustics: not a “design-from-image” tool per se (it’s a reconstruction pipeline), but it explicitly includes a **reimplementation script for Schwartzburg 2014** (`schwartzburg_2014/ma.py`) and points to required dependencies. This is currently the most direct public on-ramp to Schwartzburg-style high-contrast OT in a Python-centric stack. citeturn35view0

### OT solvers and geometry libraries that unlock higher-resolution and better domains

If you want to move beyond square-only OTMap heuristics and toward Schwartzburg/Meyron-grade transport:

ggael/otmap (OTMap): open C++ solver for transport maps on uniform 2D grids; outputs maps as quad meshes; supports exact L2-optimal map to uniform square and approximate general maps via inversion/composition. citeturn42view0turn42view1

mrgt/PyMongeAmpere + mrgt/MongeAmpere: semi-discrete OT / Monge–Ampère solvers using **Laguerre (power) diagrams**, i.e., exactly the computational primitive behind many power-diagram OT optics methods. citeturn39search0turn39search8

entity["organization","CGAL","computational geometry library"] SWIG bindings: practical Python access to computational geometry that comes up in power diagram + intersection workflows. citeturn39search1

FFT-OT (Lei et al.): proposes solving OT by turning the Monge–Ampère equation into a fixed point iteration and using FFT Poisson solves per iteration; fast_caustic_design itself calls out “FFT-OT” as a potential strategy to avoid curl/distortion because it solves a single potential. citeturn33search2turn41view0

### Renderers you can use as a “ground truth” validator

For validating “ultra high resolution” caustics you should assume you’ll need a real physically based renderer:

Mitsuba 3 has a public implementation and is explicitly a differentiable renderer (useful if you move toward end-to-end optimization). citeturn28search10turn28search14

Zhou et al. explicitly compare their caustic-tailored method to Mitsuba 3 and argue that generic path tracing is less tailored to caustic design needs and can be less efficient/accurate for this use-case. citeturn16view0 fileciteturn0file1

## Best candidates for your CNC cast-acrylic “ultra high-res + high-contrast” goal

### Short answer ranking

If I’m optimizing for what you *actually said you want* (high contrast, black regions, CNC acrylic, and public code you can cannibalize), here’s the blunt ranking:

Best “works-now, open source, mesh out” candidate: **dylanmsu/fast_caustic_design**. It already implements the modern OT→Snell→normal-integration pipeline, exports a model, and focuses on speed + contrast. The square-domain limitation is real but manageable if your physical piece is square or you can mask it. citeturn41view0turn2view0

Best “high-contrast theory, closest to ‘true black’ optics’” candidate: **Schwartzburg-style power-diagram OT**, but not from the original authors (code not released per replicability review). In practice, your best entry point is the **ShapeFromCaustics reimplementation** route plus power-diagram OT tooling (PyMongeAmpere / CGAL) if you want to push resolution rigorously. citeturn36view0turn37view0turn35view0turn10view3 fileciteturn0file2

Best “real light sources, less blur in the physical build” candidate: **Zhou et al.’s surface-light-source-aware method**, but I did not see a public repo in the retrieved sources. This is the one you’d reimplement if your illumination isn’t truly collimated and you refuse to accept blur. citeturn16view0turn17search11 fileciteturn0file1

### Why your current Ferraro (Poisson) pipeline is a good baseline but not the ceiling

Ferraro’s method is explicitly derived from Yue et al. and uses Poisson solves for both grid warping and height integration, which makes it *stable and hackable*. citeturn6view1turn9view0

But the Schwartzburg paper’s entire point is that globally smooth/bijective mapping approaches have a hard time with **pure black regions and extreme contrast transitions**, and they show black-region targets achieved via discontinuities in the transport map. citeturn10view2turn10view0turn29view1

So: keep Poisson as your “baseline generator,” but if your artistic targets genuinely involve deep blacks and tight bright strokes, you eventually need either (a) high-contrast OT with power diagrams or (b) end-to-end differentiable approaches that can directly optimize for those transitions.

## Implementation notes that matter for a high-resolution CNC acrylic pipeline

This section is intentionally practical: it’s the stuff that actually changes whether “8k caustics” look like mush.

### Treat “light source realism” as a first-class input, not a nuisance

If you want black backgrounds and razor edges, you must either:

Use a truly collimated source (sun, or a good collimator), aligning with the assumptions used by many classic methods. citeturn9view0turn19view0

Or explicitly model the emitter extent and optimize with it. Zhou et al.’s formulation approximates a planar surface emitter by multiple point sources with optimized positions/intensities and then optimizes the lens using a differentiable flux model; they explicitly position this as fixing blur from idealized-source assumptions. citeturn16view0turn17search11 fileciteturn0file1

If you’re going to reimplement something in Python to “upgrade” your pipeline, upgrading the source model is higher ROI than obsessing over the last 5% of your mesh export.

### Scaling to ultra high resolution: OT is the bottleneck, so pick your OT strategy deliberately

Schwartzburg reports that OT computation time is dominated by recomputing power diagrams each iteration and shows multi-minute to multi-hour runtimes as samples rise into the hundreds of thousands or millions. citeturn10view4

OTMap (grid OT) is designed for speed and interactive performance, but comes with the trade: only the map-to-uniform-square is truly L2-optimal; inversion/composition yields density-preserving but only approximately optimal maps. That approximation can inject curl and distort a lens when you integrate normals. citeturn42view1turn42view0turn41view0

So your “ultra high-res” path typically looks like one of these two:

Grid OT fast path: OTMap-family (or an FFT-based OT solver) + careful post-integration regularization. This is basically what fast_caustic_design does and why it’s fast. citeturn41view0turn33search2

Power-diagram OT rigorous path: semi-discrete OT with Laguerre cells / power diagrams (PyMongeAmpere / MongeAmpere++ / CGAL machinery) closer to Schwartzburg/Meyron. Harder engineering, but it’s the route to non-square domains and “true” OT behavior. citeturn39search0turn10view3turn14view0

### Normal integration is where good OT maps go to die—be strict about integrability

fast_caustic_design is unusually honest about this: if the map isn’t a proper gradient field (curl-free), normal integration effectively throws away the curl component and you get visible distortions. citeturn41view0

Your pipeline should therefore treat “integration residual” (or an integrability error metric) as a gate: if it’s high, the upstream map is suspect, not the integrator.

### CNC-specific realities you should bake into the optimization (even if papers don’t)

When papers talk about “fabrication constraints,” they usually mean some mix of bounded slopes/curvature, convexity/concavity, and minimum feature sizes. The Light-in-Power paper explicitly motivates convexity/concavity in the context of milling and mold-making. citeturn14view0

The end-to-end surface optimization paper’s abstract explicitly states that it enforces fabrication constraints to facilitate CNC milling/polishing and uses OT updates to avoid local minima. citeturn30search6turn29view1

At the hobbyist/experimental end, Ferraro’s manufacturing section is still one of the clearer practical accounts: standard 2.5D toolpaths, then sanding/polish; he also gives a concrete scale (mm-level height variation over a 10cm square). citeturn6view1turn5view0

The implication for your Python work is direct: add explicit terms for max slope / curvature and maybe even tool-radius filtering if your targets contain thin bright lines. Otherwise you’ll “solve” images the mill cannot physically resolve.

### What I’d implement next, if I were building your “next pipeline version”

This is opinionated, but it’s consistent with the matrix above:

Keep your existing Julia pipeline as the baseline generator, but add a Python “upgrade path” that can swap three modules independently: (1) OT/mapping solver, (2) normal/height integration solver, (3) rendering/validation and calibration loop. The modularity mirrors how the strongest papers structure their pipelines (mapping → normals → surface). citeturn10view0turn41view0turn6view1

For module (1), the most leverage is either migrating from Poisson warping to **high-contrast OT (power diagrams)**, or adding a **source-extent model** a la Zhou if you use LEDs. citeturn10view1turn16view0turn6view1

For module (3), validate with a physically based renderer (Mitsuba 3 is a realistic Python-integrable candidate) and measure error with at least MAE + SSIM, since recent work uses both as quantitative indicators. citeturn28search10turn29view1

As raw material to feed into Claude Code, the most “copyable” sources are: fast_caustic_design’s README (clear algorithm + pitfalls), Yue 2014 (clean Poisson formulation), Schwartzburg 2014 (the high-contrast design target and power-diagram OT details), and Zhou 2025 (source model + flux-based differentiable rendering). citeturn41view0turn9view0turn10view3turn16view0 fileciteturn0file2 fileciteturn0file1