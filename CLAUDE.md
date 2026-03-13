# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CausticsEngineering is a Julia package that generates 3D printable surface meshes designed to project specific caustic images when illuminated. It implements the algorithm from ["Poisson-Based Continuous Surface Generation for Goal-Based Caustics"](https://www.researchgate.net/profile/Yonghao_Yue/publication/274483217_Poisson-Based_Continuous_Surface_Generation_for_Goal-Based_Caustics/).

## Commands

**Run the main pipeline:**
```bash
julia run.jl
```

**Run tests:**
```bash
julia -e 'using Pkg; Pkg.test()'
```

**Build documentation:**
```bash
julia docs/make.jl
```

**Format code:**
```bash
julia --eval "using JuliaFormatter; format(@__DIR__)"
```

**Interactive development:** Use `src/scratchpad.jl` line-by-line in a Julia REPL.

## Architecture

### Core Pipeline (`src/create_mesh.jl`, ~960 lines)

The algorithm runs in `engineer_caustics()` and proceeds as follows:

1. **Input**: Grayscale image normalized so total brightness matches mesh area
2. **Iterative mesh deformation** (4 iterations via `oneIteration()`):
   - `getPixelArea()` — computes area of each mesh cell using triangle areas
   - Loss = difference between mesh pixel areas and target image brightness
   - `relax!()` — Successive Over-Relaxation (SOR) solver for Poisson's equation with Neumann boundary conditions (ω = 1.99)
   - `marchMesh!()` — deforms mesh along gradient of the solved potential field, finding triangle collision times via `findT()`
3. **Surface height computation** (`findSurface()`): applies refraction physics (n₁=1.49, n₂=1) to determine actual 3D heights from the deformed mesh
4. **Solidification** (`solidify()`): duplicates mesh as top surface, adds flat bottom, connects sides to create a watertight solid
5. **Output**: OBJ file at specified physical scale

### Data Structures (`src/utilities.jl`)

- `Point3D` — mutable struct: 3D coordinates (x, y, z) + grid indices (ix, iy)
- `Triangle` — immutable: three point indices into a nodes array
- `Mesh` — immutable: nodes vector, nodeArray (2D grid), triangles, width/height

### Module Entry (`src/CausticsEngineering.jl`)

Imports `DocStringExtensions`, `Images`, `Plots` (GR backend); includes utilities.jl and create_mesh.jl; exports `main` and `engineer_caustics`.

### OBJ I/O

- `Obj2Mesh()` — parses OBJ format into Mesh struct
- `saveObj!()` — writes Mesh to OBJ with optional scaling

## Key Notes

- The test suite (`test/runtests.jl`) is a skeleton with no implemented tests
- Generated `.obj` files are gitignored
- Julia compatibility: v1+; lockfile targets Julia 1.11.5
