#!/usr/bin/env python3
"""
analyze_woodblock_8in.py — Bit resolution analysis for 8" woodblock physical lens.
HANDOFF v001 Task 3.

MESH STRUCTURE: The solidify() function stores vertices as:
  First  n/2 nodes: flat base slab (constant Z = -offset)
  Second n/2 nodes: caustic surface (the machining target)
Both layers are stored in row-major order: for y in 1:height, for x in 1:width.
The transport map displaces XY positions, but the ENUMERATION ORDER is still grid-row-major.
"""

import numpy as np
from pathlib import Path
import time

OBJ_PATH = Path("/Users/admin/Documents/Claude/causticsEngineering_v1/Final cows/woodblock/8in/physical_lens_8x8.obj")

print("="*60)
print("Bit Resolution Analysis — Woodblock 8\" Physical Lens")
print("="*60)

# ── Parse OBJ ────────────────────────────────────────────────────────────────────
print("\nParsing OBJ ...")
t0 = time.time()
raw = OBJ_PATH.read_bytes()
lines = raw.split(b'\n')
v_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'v '))
verts = np.fromstring(v_buf.decode(), dtype=np.float64, sep=' ').reshape(-1, 3)
print(f"  Parsed in {time.time()-t0:.1f}s: {len(verts):,} vertices")

# ── Extract caustic surface (second half of vertex array) ─────────────────────────
n_total = len(verts)
n_half = n_total // 2
caustic_verts = verts[n_half:]  # second half = caustic surface from solidify()
slab_verts = verts[:n_half]     # first half = flat base slab

# Grid dimensions (1024px solver -> 1025x1025)
grid_side = int(round(np.sqrt(n_half)))
assert grid_side * grid_side == n_half, f"Grid not square: {n_half} != {grid_side}^2"
print(f"  Grid: {grid_side} x {grid_side} = {n_half:,} caustic vertices")

# Reshape to grid (row-major: y varies slowest)
# In the OBJ, vertices stored as: for y in 1:height, for x in 1:width
# So reshape to (height, width, 3) = (grid_side, grid_side, 3)
grid = caustic_verts.reshape(grid_side, grid_side, 3)

# Convert to inches
M_TO_IN = 1.0 / 0.0254
grid_in = grid * M_TO_IN
z_grid = grid_in[:, :, 2]  # Z surface in inches

xy_span_in = 8.0  # target physical size
cell_spacing = xy_span_in / (grid_side - 1)  # uniform grid spacing in inches

print(f"  XY span: {xy_span_in:.1f}\"")
print(f"  Z range: {z_grid.min():.6f}\" to {z_grid.max():.6f}\"")
relief_in = z_grid.max() - z_grid.min()
print(f"  Caustic relief: {relief_in:.4f}\" ({relief_in*25.4:.3f} mm)")

# ── 3A: Mesh cell size ──────────────────────────────────────────────────────────
print(f"\n── 3A: Mesh Cell Size ──────────────────────────────────")
print(f"  Grid spacing (uniform): {cell_spacing:.6f}\" ({cell_spacing*25.4:.4f} mm)")
print(f"  Grid cells per axis: {grid_side - 1}")
print(f"  Note: Transport map displaces XY, but Z sampling is at regular grid intervals.")
print(f"  For curvature analysis, the effective Z sampling rate is {cell_spacing:.6f}\"/cell.")

# ── 3C: Surface curvature analysis ───────────────────────────────────────────────
print(f"\n── 3C: Surface Curvature Analysis ──────────────────────")

# Second derivatives of Z via central differences on the uniform grid
d2z_dx2 = np.diff(z_grid, n=2, axis=1) / (cell_spacing ** 2)
d2z_dy2 = np.diff(z_grid, n=2, axis=0) / (cell_spacing ** 2)

# Trim to common interior region
# d2z_dx2 has shape (grid_side, grid_side-2)
# d2z_dy2 has shape (grid_side-2, grid_side)
interior_xx = d2z_dx2[1:-1, :]         # shape: (grid_side-2, grid_side-2)
interior_yy = d2z_dy2[:, 1:-1]         # shape: (grid_side-2, grid_side-2)

# Mean curvature (Laplacian / 2)
kappa_mean = 0.5 * (interior_xx + interior_yy)
kappa_abs = np.abs(kappa_mean)

# Principal curvatures (approximated from eigenvalues of Hessian)
# For a better radius estimate, use max of |d2z/dx2| and |d2z/dy2| individually
kappa_max = np.maximum(np.abs(interior_xx), np.abs(interior_yy))

# Minimum radius of concavity (from maximum absolute curvature)
kappa_nz = kappa_max[kappa_max > 1e-10]
radii = 1.0 / kappa_nz

print(f"  Using maximum principal curvature (conservative for bit clearance)")
print(f"\n  Curvature |κ_max| statistics (1/inch):")
print(f"    Mean:     {kappa_max.mean():.4f}")
print(f"    Median:   {np.median(kappa_max):.4f}")
print(f"    95th pct: {np.percentile(kappa_max, 95):.4f}")
print(f"    99th pct: {np.percentile(kappa_max, 99):.4f}")
print(f"    Max:      {kappa_max.max():.4f}")

print(f"\n  Concavity radius R = 1/|κ_max| statistics (inches):")
print(f"    Mean R:    {radii.mean():.4f}\"")
print(f"    Median R:  {np.median(radii):.4f}\"")
print(f"    5th pct R: {np.percentile(radii, 5):.4f}\"")
print(f"    1st pct R: {np.percentile(radii, 1):.4f}\"")
print(f"    Min R:     {radii.min():.6f}\"")

# Bit clearance analysis
bit_radii = {
    '1/4" ball': 0.125,
    '1/8" ball': 0.0625,
    '1/16" ball': 0.03125,
    '1/32" ball': 0.015625,
}

print(f"\n  Bit clearance (% of surface with concavity radius < bit tip radius):")
print(f"  Interpretation: lower = better. Features with R < bit radius")
print(f"  will NOT be fully reached by the bit — they'll be smoothed/rounded.")
for name, r_bit in bit_radii.items():
    pct_too_small = 100.0 * (radii < r_bit).sum() / len(radii)
    pct_safe = 100.0 - pct_too_small
    print(f"    {name:12s} (tip R={r_bit:.4f}\"): {pct_too_small:.2f}% unresolvable, {pct_safe:.2f}% fully resolved")

# Also report using 70% safety margin (CAUSTICFORGE convention)
print(f"\n  With 70% safety margin (CAUSTICFORGE convention):")
for name, r_bit in bit_radii.items():
    r_safe = r_bit * 0.70
    pct_too_small = 100.0 * (radii < r_safe).sum() / len(radii)
    print(f"    {name:12s} (safe R={r_safe:.4f}\"): {pct_too_small:.2f}% unresolvable")

# ── 3B: Bit geometry vs mesh resolution ──────────────────────────────────────────
print(f"\n── 3B: Bit Geometry vs Mesh Resolution ─────────────────")
print(f"  Mesh cell spacing: {cell_spacing:.6f}\" ({cell_spacing*25.4:.4f} mm)")

bits = [
    ("1/4\" ball",  0.250, 0.125,  [(0.100, 40), (0.025, 10), (0.020, 8)]),
    ("1/8\" ball",  0.125, 0.0625, [(0.0125, 10), (0.010, 8)]),
    ("1/16\" ball", 0.0625, 0.03125, [(0.005, 8), (0.004, 6)]),
    ("1/32\" ball", 0.03125, 0.015625, [(0.003125, 10)]),
]

print(f"\n  {'Bit':12s}  {'Stepover':>10s}  {'Cells/step':>10s}  {'Status'}")
for name, dia, tip_r, stepovers in bits:
    for so, pct in stepovers:
        cells_per_step = so / cell_spacing
        if cells_per_step >= 2:
            status = "OVERSAMPLES mesh (stepover > 2 cells)"
        elif cells_per_step >= 1:
            status = "matches mesh resolution"
        else:
            status = f"finer than mesh ({cells_per_step:.1f} cells/step)"
        print(f"  {name:12s}  {so:.4f}\" ({pct}%)  {cells_per_step:>8.1f}      {status}")

# ── 3D: Scallop height ──────────────────────────────────────────────────────────
print(f"\n── 3D: Scallop Height ─────────────────────────────────")
print(f"  Total Z relief: {relief_in:.4f}\" ({relief_in*25.4:.3f} mm)")

scallop_configs = [
    ("1/4\" ball @ 10% (0.025\")", 0.125, 0.025),
    ("1/4\" ball @ 40% (0.100\")", 0.125, 0.100),
    ("1/8\" ball @ 10% (0.0125\")", 0.0625, 0.0125),
    ("1/16\" ball @ 8% (0.005\")", 0.03125, 0.005),
    ("1/32\" ball @ 10% (0.003\")", 0.015625, 0.003125),
]

print(f"\n  {'Config':35s}  {'Scallop H':>10s}  {'% of relief':>12s}  {'μm':>6s}  {'Quality'}")
for label, R, stepover in scallop_configs:
    scallop = R - np.sqrt(R**2 - (stepover/2)**2)
    pct = scallop / relief_in * 100
    um = scallop * 25400  # micrometers
    quality = "excellent" if pct < 1 else ("good" if pct < 5 else ("acceptable" if pct < 10 else "rough"))
    print(f"  {label:35s}  {scallop:.6f}\"  {pct:>10.2f}%  {um:>6.1f}  {quality}")

# ── 3E: Cut time estimates ──────────────────────────────────────────────────────
print(f"\n── 3E: Cut Time Estimates ──────────────────────────────")
stock_size = 8.0

time_configs = [
    ("1/4\" ball rough  40%", 0.100, 144, 201.6),
    ("1/4\" ball finish 10%", 0.025, 144, 201.6),
    ("1/8\" ball finish 10%", 0.0125, 100, 140.0),
    ("1/16\" ball finish 8%", 0.005, 72, 100.8),
    ("1/32\" ball finish 10%", 0.003125, 40, 56.0),
]

print(f"  Stock: {stock_size}\" x {stock_size}\"")
print(f"\n  {'Config':24s}  {'Rows':>6s}  {'Travel':>8s}  {'Normal':>8s}  {'Superfast':>10s}")
for label, stepover, feed_n, feed_f in time_configs:
    rows = int(np.ceil(stock_size / stepover))
    travel = rows * stock_size
    time_n = travel / feed_n
    time_f = travel / feed_f
    print(f"  {label:24s}  {rows:>6d}  {travel:>7.0f}\"  {time_n:>6.1f}m   {time_f:>8.1f}m")

# ── Combined strategy estimates ──────────────────────────────────────────────────
print(f"\n── Combined Strategies ────────────────────────────────")
strategies = [
    ("Rough 1/4\" + Finish 1/4\" 10%", [(0.100, 144, "rough"), (0.025, 144, "finish")]),
    ("Rough 1/4\" + Finish 1/8\" 10%", [(0.100, 144, "rough"), (0.0125, 100, "finish")]),
    ("Rough 1/4\" + Finish 1/16\" 8%", [(0.100, 144, "rough"), (0.005, 72, "finish")]),
]

for label, passes in strategies:
    total_n = 0
    for stepover, feed, _ in passes:
        rows = int(np.ceil(stock_size / stepover))
        total_n += rows * stock_size / feed
    print(f"  {label:38s}  Total: {total_n:.0f} min Normal")

# ── Surface slope analysis ──────────────────────────────────────────────────────
print(f"\n── Surface Slope Analysis ──────────────────────────────")

dz_dx = np.diff(z_grid, axis=1) / cell_spacing
dz_dy = np.diff(z_grid, axis=0) / cell_spacing

# Gradient magnitude at interior points
min_r = min(dz_dx.shape[0], dz_dy.shape[0])
min_c = min(dz_dx.shape[1], dz_dy.shape[1])
grad_mag = np.sqrt(dz_dx[:min_r, :min_c]**2 + dz_dy[:min_r, :min_c]**2)
angles = np.degrees(np.arctan(grad_mag))

print(f"  Max slope angle: {angles.max():.2f}°")
print(f"  Mean slope angle: {angles.mean():.2f}°")
print(f"  Median slope angle: {np.median(angles):.2f}°")
print(f"  95th pct angle: {np.percentile(angles, 95):.2f}°")
print(f"  % area < 1°:  {100*(angles < 1).sum()/angles.size:.1f}%")
print(f"  % area < 5°:  {100*(angles < 5).sum()/angles.size:.1f}%")
print(f"  % area < 15°: {100*(angles < 15).sum()/angles.size:.1f}%")
print(f"  % area < 30°: {100*(angles < 30).sum()/angles.size:.1f}%")

print(f"\n  CAUSTICFORGE steep-angle threshold (default 5 thou / 0.005\"):")
print(f"  Plunge feed used when drop between adjacent points > threshold")
print(f"  At {cell_spacing:.6f}\" cell spacing, a 5° slope = {np.tan(np.radians(5))*cell_spacing:.6f}\" drop")
print(f"  This is {'above' if np.tan(np.radians(5))*cell_spacing > 0.005 else 'below'} the 0.005\" threshold")

print(f"\n{'='*60}")
print("Analysis complete.")
