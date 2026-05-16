## Session - May 16, 2026
Present: Deepansh (solo)
Duration: [how long you worked]

### Completed
- Dataset survey finished for all seven target species across Caltech and iNaturalist
- Species counts and pull strategy documented in dataset_survey.md
- iNaturalist API tested and confirmed working (2,313 moose BC observations accessible)
- MegaDetector v5a installed and validated on 50 moose test images
- Detection rate on raw iNaturalist images: 57% usable (29/51 above 0.5 confidence)
- GPU runtime confirmed on Colab (Tesla T4)
- Google Drive mounted for persistent storage
- Directory structure created at MyDrive/bc-dashcam/
- Full download pipeline ready for all species

### Decisions
- Cougar: global iNaturalist pull approved due to insufficient BC-only coverage (332 images)
- Per-species download cap set at 500 images for initial pull
- MegaDetector confidence threshold set at 0.5 for usable annotation cutoff

### Blockers
- None on Deepansh's side
- Aditya: GPS spec and power budget confirmed committed to repo

### Deferred
- Full species downloads deferred to next session (pipeline ready, runtime takes 20-30 min per species)

### Next Session
- Run full download pipeline for all seven species in sequence
- Start MegaDetector batch annotation on downloaded images

---
