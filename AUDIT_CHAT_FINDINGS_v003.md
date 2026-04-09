# AUDIT: Claude Chat Findings v003 — Independent Verification
**Date:** 2026-04-09
**Auditor:** Claude Code (overnight unattended session)
**Scope:** Verify 5 claims from Claude Chat before proceeding with V1/V2 comparison runs

---

## 1A. Source Image Identity
**CLAIM:** V1 and V2 copies of woodblock2.png are identical.
**RESULT: CONFIRMED ✓**
- V1 (`Final cows/woodblock2.png`): MD5 `c7ff322408426698f8946ae70d8e0625`
- V2 (`images/woodblock2.png`): MD5 `c7ff322408426698f8946ae70d8e0625`
- Identical files.

## 1B. V1 Stale Parameters
**CLAIM:** All Final Cows meshes used hardcoded `artifactSize=0.1m` / `focalLength=0.75m`.
**RESULT: CONFIRMED ✓**
- At commit `b845296` (woodblock PROD): `artifactSize = 0.1` and `focalLength = 0.75` hardcoded at lines 877-878 of `src/create_mesh.jl`
- Env var parsing (`CAUSTIC_ARTIFACT_SIZE`, `CAUSTIC_FOCAL_LENGTH`) added later in commit `3f0643c`
- No run logs contain `CAUSTIC_ARTIFACT_SIZE` print statements
- No `.sh` scripts set `CAUSTIC_*` environment variables (confirmed via grep)
- **All Final Cows meshes used 0.1m (3.94") / 0.75m (30" throw)**

## 1C. Throw-Scaling Under Uniform Scaling
**CLAIM:** Uniform scaling of a caustic lens changes effective throw proportionally when scaling to a different size.
**RESULT: CONFIRMED ✓**
- V1 `findSurface()` at line 690: `Nx[i,j] = tan(atan(dx/dz) * inv_n1m1)` — slopes are dimensionless ratios
- Slopes preserved under uniform scaling S. Hit position at distance d: `Sx + d·tan(θ)`. Intended: `Sx + S·f·tan(θ)`. Match only when `d = S·f`.
- V1 woodblock 24" OBJ: native 3.94", S=6.09×, effective throw = 30"×6.09 = **183"** (WRONG for 48")
- V2 woodblock2 8" OBJ: native 24", S=0.333×, effective throw = 48"×0.333 = **16"** (WRONG for 24")
- V1 new run at 8" with `artifactSize=0.2032`: net S=1.0, throw = **24"** (CORRECT)
- **COROLLARY:** `make_physical_lens.py` scaling to the SAME size as `artifactSize` preserves throw (S=1.0).

## 1D. V1's 1/512 saveObj! Divisor
**CLAIM:** Hardcoded `1/512` makes 1024px intermediate OBJ 2× too large; `make_physical_lens.py` corrects it.
**RESULT: CONFIRMED ✓**
- Line 898: `scale=1/512 * artifactSize`
- At 512px: 513 nodes × (artifactSize/512) = artifactSize ✓
- At 1024px: 1025 nodes × (artifactSize/512) = 2×artifactSize (2× too large)
- `make_physical_lens.py` with `CAUSTIC_TARGET_SIZE=artifactSize` dynamically computes scale from actual span → net scale 1.0
- Throw preserved per 1C proof.

## 1E. Physics Model Equivalence
**CLAIM:** V1's `(n-1)` formula and V2's single-surface Snell + 1/n correction are equivalent in paraxial limit.
**RESULT: CONFIRMED ✓**
- V1: `slope = tan(atan(dx/dz) / (n-1))`
- V2: Vector Snell's law with deflection × (1/n) correction
- At n=1.492, dx=4", dz=24" (9.5° deflection):
  - V1 slope: 0.348870
  - V2 corrected slope: 0.343091
  - Difference: **1.66%**
- Both converge at small angles. V2 is slightly more accurate at large angles.

## 1F. Path Migration
**RESULT: FIXED ✓**
- Old path `/Users/admin/causticsEngineering/` exists but contains only a G-code file
- Project lives at `/Users/admin/Documents/Claude/causticsEngineering_v1/`
- `make_physical_lens.py`: migrated to `PROJECT_ROOT = Path(__file__).resolve().parent`
- `run_cow_pipeline.sh`: migrated to `PROJECT="$(cd "$(dirname "$0")" && pwd)"`
- Committed as separate fix commit.

---

## Summary
All 5 Chat claims **CONFIRMED**. No adjustments needed to Phases 2-4.
Proceeding with comparison runs as planned.
