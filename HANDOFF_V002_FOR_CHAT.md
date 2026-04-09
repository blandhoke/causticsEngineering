# HANDOFF — V002 Session Results for Claude Chat
**Date:** 2026-04-09
**From:** Claude Code (v002 session)
**To:** Claude Chat

---

## What was done

Three tasks from HANDOFF_v002, all complete. No code changes — read-only forensic analysis.

---

## Task 1: Source Image Verification

**V1 and V2 used DIFFERENT source images.**

- V1 PROD woodblock mesh: `INKFORGE/woodblock.png` (457KB, grayscale, MD5 `a08bb8...`)
- V2: `woodblock2.png` (1.39MB, RGB, MD5 `c7ff32...`)
- Pixel correlation r=0.907 — same subject (woodblock cow), different rendering
- Mean pixel difference: 48.45 (out of 255)

The confusion arose because a stale 512px `run.log` in the mesh directory referred to `Final cows/woodblock.png` (which was a copy of woodblock2.png), but the actual 1024px PROD mesh was built from `INKFORGE/woodblock.png` in a later run that didn't update the log.

**Full report:** `VERIFICATION_woodblock_source.md`

---

## Task 2: Physics Model Forensic Comparison

### The big discovery: V1's woodblock mesh uses STALE solver parameters

At the time of the PROD woodblock run (commit `b845296`, Mar 17):
- `artifactSize = 0.1m` (3.94") — hardcoded
- `focalLength = 0.75m` (30" throw) — hardcoded

The 24" / 48" defaults were added in commit `3f0643c` AFTER the woodblock run. V1's woodblock mesh was designed for a **3.94" lens at 30" throw**, not 24" at 48".

### Depth comparison (both at 8" physical)

| | V1 | V2 |
|--|-----|-----|
| CNC cut depth | 2.055mm (0.081") | 9.59mm (0.378") |
| Throw distance | 30" | 48" |
| Native lens size | 3.94" | 24" |
| Source image | INKFORGE/woodblock.png | woodblock2.png |
| Resolution | 1024px (2.1M faces) | 128px (16k faces) |

The 4.66x depth ratio is NOT a physics error. It's the compound result of different physical configurations.

### Physics models are equivalent

Both pipelines produce `slope = delta / (f * (n-1))` in the paraxial limit. V2 is slightly more accurate at large angles (1.6% error vs V1's 5.6% at 14° max deflection) because it uses exact vector Snell's law for the single-surface step.

V2's dual-surface correction verified at exactly 1/n: corrected/uncorrected depth ratio = 0.669 vs theoretical 0.670.

### V2 cross-review of V1

V2 wrote `docs/V1_CROSS_REVIEW.md` with 7 findings about V1. Key ones:

1. **FOCAL_DIST mismatch (I2):** V1 ray tracer has `FOCAL_DIST=0.75` but current solver default is `1.219`. For the woodblock mesh this is actually correct (solver was at 0.75 when it was built), but it's a landmine for future meshes.
2. **Point source vs collimated (I1):** V1 solver assumes collimated light, ray tracer uses point source. ~2-4% edge error.
3. **fliplr mystery (I5):** V1 applies a horizontal flip in the renderer. V2 validated no flips needed. Suggests a coordinate convention issue baked into V1's solver.

**Full report:** `COMPARISON_v1_v2_woodblock_8in.md`

---

## Task 3: V2 G-code Status

Three G-code files ready in `causticengineering_v2/output/`:

| File | Lines | Tool | Strategy |
|------|-------|------|----------|
| Roughing | 50,363 | 1/4" ball | Y-raster, 0.100" DOC, 60% stepover |
| Finishing | 64,035 | 1/4" ball | Archimedean spiral, 20% stepover |
| Square cut | 4,537 | 1/2" O-flute | 0.150" DOC, 7 passes, 4 tabs |

1/4" ball for finishing is appropriate at 128px mesh resolution (0.0625" cell spacing). If V2 goes to 256px+, should switch to 1/8" ball per V1's bit analysis.

---

## Decisions needed from Claude Chat

1. **Re-run V1 woodblock at 24"/48" config?** The current V1 woodblock mesh is orphaned (30" throw). Re-running with the current defaults would give a fair V1-vs-V2 comparison on the same physical target. Requires Julia solver run (~8 min).

2. **Run V2 at 256px?** V2's state.json shows `edge_r` improves from 0.225 (128px) to 0.241 (256px). 128px mesh is coarser than the CNC toolpath. Production should be 256px minimum.

3. **Same-image controlled comparison?** Neither pipeline has been run on the other's source image. Running both on `woodblock2.png` at the same resolution with the same throw would isolate the pipeline physics difference from the input/config differences.

4. **Proceed with V2 128px cut as proof-of-concept?** V2 has G-code ready. A quick 128px cut at 48" throw would physically validate the pipeline even if the resolution is suboptimal.

5. **Address V2's findings about V1?** The point-source ray tracer and fliplr issues are real but low-urgency. Worth fixing before V1 production cuts.

---

## Files produced this session

- `VERIFICATION_woodblock_source.md` — source image confirmation
- `COMPARISON_v1_v2_woodblock_8in.md` — comprehensive forensic comparison
- `comparison_v1v2_centerline.png` — 4-panel comparison plot
- Updated `state.json` (blockers resolved, stale params flagged, comparison data added)

## Git

- Start: `31abdef` (v002: session start snapshot)
- End: `0b6f849` (v002: Forensic V1/V2 comparison)
