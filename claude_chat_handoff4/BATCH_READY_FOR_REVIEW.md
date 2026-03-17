# Final Cows Batch — Ready for Claude Chat Review
# Date: 2026-03-16
# Status: 10/10 PASSED

---

## Pass/Fail Summary

All 10 runs completed successfully in 7 minutes total (vs ~80 min estimate —
Julia is faster at 256px/512px for these images).

| Image    | FAST  | NORMAL | Status |
|----------|-------|--------|--------|
| banknote | 34s   | 67s    | ✓ ✓    |
| charcol  | 23s   | 57s    | ✓ ✓    |
| inkbrush | 23s   | 52s    | ✓ ✓    |
| nikon    | 23s   | 57s    | ✓ ✓    |
| woodblock| 23s   | 58s    | ✓ ✓    |

---

## Timing + Physics Table

| Image     | FAST time | FAST faces | FAST sigma | NORMAL time | NORMAL faces | NORMAL sigma |
|-----------|-----------|------------|------------|-------------|--------------|--------------|
| banknote  | 34s       | 131,072    | 3.002      | 67s         | 524,292      | 1.501        |
| charcol   | 23s       | 131,072    | 3.002      | 57s         | 524,288      | 1.501        |
| inkbrush  | 23s       | 132,054    | 2.991      | 52s         | 526,254      | 1.498        |
| nikon     | 23s       | 131,711    | 2.995      | 57s         | 525,564      | 1.499        |
| woodblock | 23s       | 131,072    | 3.002      | 58s         | 524,288      | 1.501        |

FAST (256px): ~131k faces, sigma≈3.0
NORMAL (512px): ~525k faces, sigma≈1.5

---

## Review Instructions for Claude Chat

Upload N_contact_sheet.jpg and review all 10 panels (5 images × 2 speeds).

**Q1 — Ranking:**
Rank all 5 treatments from most to least compelling caustic output.
Consider: recognizability, contrast (dark bg / bright caustic), sharpness, artistic quality.
[rank 1–5 with brief reason for each]

**Q2 — FAST vs NORMAL quality difference:**
Does the NORMAL (512px) render show meaningful improvement over FAST (256px)?
Or are they visually comparable for each image?
[note any image where the quality jump is significant]

**Q3 — Physics errors:**
Flag any render that looks flat (no dark background), washed out, doubled, or wrong.
[list any problem renders with description]

**Q4 — Production recommendation:**
Which 1–2 treatments should run at PRODUCTION (1024px, ~45 min Julia, ~35 min ray trace)?
Production is the CNC-ready output. Choose the treatment most likely to produce
a compelling physical caustic.
[top 1–2 with reason]

---

## Where to Write Answers

Write to: claude_chat_handoff4/PRODUCTION_SELECTION.md

Claude Code reads that file and runs the selected treatment(s) at 1024px.

---

## Output Files

All renders: Final cows/<slug>/<speed>/caustic.png (10 files)
Contact sheet: Final cows/comparison_contact_sheet.png
Handoff JPEG: claude_chat_handoff4/N_contact_sheet.jpg (271KB)
