# Dataset Survey

Last updated: June 25, 2026

This document surveys available image sources for the 7 target wildlife species and documents the pull strategy, filtering results, and known risks.

---

## Sources

### Caltech Camera Traps

Metadata file: `caltech_images_20210113.json`
Total images: 243,100
Total annotations: 245,118

| Species | Annotations | Notes |
|---|---|---|
| Deer | 12,196 | Good coverage |
| Coyote | 16,601 | Good coverage |
| Raccoon | 11,390 | Good coverage |
| Cougar | 145 | Severe underrepresentation |
| Elk | 0 | Absent from dataset |
| Moose | 0 | Absent from dataset |
| Bear | 0 | Absent from dataset |

Three of the seven target species (elk, moose, bear) are entirely absent from Caltech Camera Traps. Cougar coverage is negligible at 145 annotations.

### iNaturalist — British Columbia

| Species | Observations |
|---|---|
| Deer | 30,681 |
| Bear | 9,604 |
| Raccoon | 4,470 |
| Moose | 4,396 |
| Coyote | 3,217 |
| Elk | 2,178 |
| Cougar | 332 |

### iNaturalist — Global (cougar only)

| Species | Observations |
|---|---|
| Cougar | 14,770 |

BC-only cougar count of 332 is insufficient for fine-tuning. Global pull approved for this species only. This introduces domain diversity outside BC, which is an accepted tradeoff.

---

## Pull Strategy

| Species | Source | Strategy |
|---|---|---|
| Deer | Caltech + iNaturalist BC | Cap at 500 initial pull |
| Coyote | Caltech + iNaturalist BC | Cap at 500 initial pull |
| Raccoon | Caltech + iNaturalist BC | Cap at 500 initial pull |
| Bear | iNaturalist BC | Cap at 500 initial pull |
| Moose | iNaturalist BC | All available |
| Elk | iNaturalist BC | Cap at 500 initial pull |
| Cougar | Caltech + iNaturalist global | Cap at 500 initial pull |

Deer, coyote, and raccoon are heavily over-represented in the combined source pool. Training caps are required to prevent class imbalance from suppressing learning on rare classes. Target training set per class: 300-500 images for the initial proof-of-concept pull.

---

## MegaDetector Filtering Results

Every downloaded image was run through MegaDetector v5a with a confidence threshold of 0.5. Images below this threshold were discarded.

| Species | Downloaded | Usable (conf >= 0.5) | Usable Rate | Notes |
|---|---|---|---|---|
| Deer | 484 | 479 | 99.0% | |
| Coyote | 473 | 450 | 95.1% | |
| Elk | 471 | 449 | 95.3% | |
| Raccoon | 454 | 397 | 87.4% | Manual FP review done |
| Bear | 437 | 421 | 96.3% | |
| Cougar | 380 | 348 | 91.6% | Global pull |
| Moose | 316 | 316 | 63.2% | Lowest usable rate |
| **Total** | **3,015** | **2,860** | **94.9%** | |

Moose has the lowest usable rate. Raccoon required additional manual false-positive review after MegaDetector filtering.

---

## Known Risks

1. **Domain shift.** The entire dataset is sourced from iNaturalist and Caltech Camera Traps, both of which are camera-trap style imagery (fixed low-angle, IR night, animals close and broadside). A dashcam presents a fundamentally different viewpoint. This was independently flagged by the WiRE Lab at UBC Biology as a genuine risk for model generalization. Supplementary dashcam-perspective data from LILA BC or iWildCam may help mitigate this.

2. **Cougar domain diversity.** The global iNaturalist pull for cougar introduces images from outside BC. The model may learn cougar features from non-BC habitats, which could affect performance on BC road corridors.

3. **Class imbalance.** Even after filtering, moose (316) has roughly 50% fewer usable images than deer (479). Augmentation will partially compensate, but moose and raccoon remain the weakest classes.

---

## External References

- [Dataset Survey Google Sheet](https://docs.google.com/spreadsheets/d/1Y6eoyN-Xk9b4K5EFB5Z_KzXpMCz_iQKWs1BjLjqWQ9k/edit?gid=0#gid=0)
- LILA BC (lila.science) — recommended by WiRE Lab as supplementary source
- iWildCam datasets — ship with MegaDetector bounding boxes pre-generated
