# ANALYSIS — Woodblock 8" Bit Resolution
**Date:** 2026-04-08
**Session:** v001

---

## RECOMMENDATION: 1/8" ball nose finish — optimal for 8" woodblock

1/4" is viable but wastes mesh resolution. 1/8" matches the mesh perfectly.
1/16" and smaller are finer than the mesh can represent — no additional detail gained.

**Recommended combo:** 1/4" ball rough (40% stepover) + 1/8" ball finish (10% stepover)
**Total time:** ~56 min Normal / ~40 min Superfast

---

## Key Findings

### Mesh Cell Size (measured)
- Grid: 1025 x 1025 (1024px solver)
- Cell spacing: **0.00781"** (0.198 mm)
- This is the smallest feature the solver can encode

### Curvature: All bits clear — surface is extremely gentle
- Minimum concavity radius: **14.09"** (median: 155")
- Maximum slope: **1.39°** (mean: 0.67°)
- 100% of surface is fully resolvable by every bit size, including 1/32"
- No tight concavities anywhere — the caustic surface is a very gentle undulation
- This makes sense: 2.055mm relief over 203mm span = max slope ~0.6°

### Bit vs Mesh Resolution — the critical factor

| Bit | Stepover | Cells/step | Verdict |
|-----|----------|------------|---------|
| 1/4" @ 40% | 0.100" | 12.8 | **OVERSAMPLES** — skips 12 mesh cells per pass. Roughing only. |
| 1/4" @ 10% | 0.025" | 3.2 | **OVERSAMPLES** — still skips 3 cells. Misses fine caustic detail. |
| **1/8" @ 10%** | **0.0125"** | **1.6** | **MATCHES** — visits every ~1.5 cells. Captures all mesh detail. |
| 1/16" @ 8% | 0.005" | 0.6 | **FINER THAN MESH** — sub-cell interpolation. No new detail. |
| 1/32" @ 10% | 0.003" | 0.4 | **FINER THAN MESH** — pure waste at this mesh resolution. |

**1/8" at 10% stepover (0.0125") is the sweet spot**: it samples at ~1.6 mesh cells per pass, which captures all the detail the solver encoded without wasting time on sub-cell interpolation.

### Scallop Height

| Config | Scallop | % of Relief | Quality |
|--------|---------|-------------|---------|
| 1/4" @ 10% (0.025") | 15.9 μm | 0.77% | excellent |
| **1/8" @ 10% (0.0125")** | **8.0 μm** | **0.39%** | **excellent** |
| 1/16" @ 8% (0.005") | 2.5 μm | 0.12% | excellent |

All bits produce excellent scallop height relative to the 2.055mm relief. Even 1/4" @ 10% is under 1% of relief. Scallop is NOT the differentiator here — mesh resolution is.

### Cut Time Estimates (8" x 8" stock)

| Strategy | Normal | Superfast |
|----------|--------|-----------|
| Rough 1/4" + Finish 1/4" 10% | 22 min | 16 min |
| **Rough 1/4" + Finish 1/8" 10%** | **56 min** | **40 min** |
| Rough 1/4" + Finish 1/16" 8% | 182 min | 130 min |

### Surface Slopes

- Max slope: 1.39° — extremely gentle
- 100% of surface is below 5° — no steep-angle plunges needed
- CAUSTICFORGE steep threshold (0.005") is never triggered at this cell spacing
- Feed rate will stay constant through entire cut — no slowdowns

---

## Why 1/8" and not 1/4"?

The curvature analysis says 1/4" can physically enter every concavity. True — but that's not the whole picture.

The caustic image is encoded in **Z-height variations at the mesh cell scale** (0.0078"). At 1/4" @ 10% stepover (0.025"), the bit touches every 3.2 cells. It will mechanically smooth over features that span 1-3 cells — these are exactly the fine caustic lines that distinguish the woodblock image from a generic curve.

At 1/8" @ 10% (0.0125"), the bit touches every 1.6 cells — nearly every cell gets a direct measurement. The caustic pattern will be faithfully reproduced.

The cost is 56 min instead of 22 min. For a piece that took 5+ hours to solve and costs $30+ in acrylic, the extra 34 minutes is negligible.

---

## If cutting at 24" instead of 8"

At 24", the physical cell spacing scales to 0.0234" (24/1024). Now 1/4" @ 10% (0.025") gives 1.07 cells/step — which matches the mesh. **At 24", 1/4" is the right finish bit.** This confirms the prior recommendation in HANDOFF_24IN_PRODUCTION_2026-03-17.md.

The bit choice is size-dependent:
- **8" piece → 1/8" finish** (cell=0.0078", need stepover ≤ 0.013")
- **24" piece → 1/4" finish** (cell=0.023", need stepover ≤ 0.035")
