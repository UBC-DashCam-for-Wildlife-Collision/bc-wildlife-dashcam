# Hailo INT8 Quantization Checklist — `best.pt` → `model.hef`

For a Claude Code session running on the **Mac**. Picks up right after: Colab Pro
purchased (49 GB high-RAM runtime available), Hailo Developer Zone account
created, Dataflow Compiler (DFC) `.whl` downloaded. This is Phase 3 in
`docs/development_phases.md` — read that section's exit criteria too.

Context you need: `best.pt` (mAP50 0.823, mAP50-95 0.638) is backed up in three
places — T7 SSD (`models/run1-7class/best.pt`), Mac Downloads, Google Drive.
Trained at `imgsz=640`. Classes are **alphabetical and must stay in this exact
order** (fixed by `scripts/build-yolo-dataset.py`, mirrored in
`config/species.yaml`):

```
0 bear   1 cougar   2 coyote   3 deer   4 elk   5 moose   6 raccoon
```

The raw 2,860-image dataset lives only on the T7 SSD — do not move the full
set anywhere else. Only a small calibration subset leaves the SSD.

---

## 1. Gather inputs (on the Mac, SSD attached)

- [ ] Confirm `best.pt` is reachable (Downloads copy is fine, or from SSD).
- [ ] Build an INT8 **calibration set**: ~300–500 images sampled across all 7
      classes proportionally (don't need labels, just representative images —
      lighting variety matters since confidence must account for lighting per
      the supervisor's requirement). Pull from the SSD's training split, not
      the held-out test split (don't contaminate the test set used for the
      mAP-drop measurement in step 4).
- [ ] Zip the calibration set (e.g. `calib_images.zip`).
- [ ] Have the DFC `.whl` file location ready (from Hailo Developer Zone).

## 2. Upload to Google Drive

- [ ] `best.pt`
- [ ] `calib_images.zip`
- [ ] the DFC `.whl`
- [ ] a small held-out **validation subset with labels** (for the float32 vs
      INT8 mAP comparison in step 4) — or just reuse the existing 10% test
      split already sitting in the local dataset build.

Put all of these in one Drive folder so the Colab notebook can mount Drive
once and reach everything.

## 3. Colab notebook

- [ ] New notebook, Runtime → Change runtime type → confirm **high-RAM**
      (Colab Pro). Sanity check with `!cat /proc/meminfo | head -1` — expect
      ~49 GB.
- [ ] Mount Drive, `cd` into the shared folder.
- [ ] `pip install` the DFC wheel from Drive. Check its required Python
      version against Colab's default — pin a venv if they mismatch.
- [ ] `pip install ultralytics` (only needed for the ONNX export step, not the
      quantization itself).
- [ ] Export to ONNX:
      ```python
      from ultralytics import YOLO
      model = YOLO("best.pt")
      model.export(format="onnx", imgsz=640, opset=11)
      ```
- [ ] Hailo parse: ONNX → HAR (`hailo parser onnx ...`), targeting the
      **Hailo-8L** architecture (not plain Hailo-8 — this project's chip is
      the 8L, 13 TOPS).
- [ ] Hailo optimize: HAR → quantized HAR, INT8, using `calib_images.zip` as
      the calibration set.
- [ ] Hailo compile: quantized HAR → `model.hef`, again targeting `hailo8l`.
- [ ] Copy `model.hef` back to the shared Drive folder.

## 4. Validate before calling it done

- [ ] Measure mAP50 / mAP50-95 on the INT8 model against the held-out test
      split and compare to the float32 baseline (0.823 / 0.638). Document the
      drop — this is an explicit Phase 3 exit criterion.
- [ ] Check per-class numbers specifically for the two weak classes flagged
      in CLAUDE.md §14 — **raccoon** (float32 mAP50-95 0.492) and **elk**
      (0.573) — INT8 quantization tends to hurt already-weak classes more.
- [ ] Re-calibrate per-class confidence thresholds if needed (supervisor
      requirement: confidence must account for lighting — check performance
      split by day/night images if your calibration/test images have that
      metadata).

## 5. Handoff to the Pi

- [ ] Get `model.hef` onto the Pi (Drive download, `scp`, or USB) —
      **only the `.hef` goes to the Pi, never the raw dataset or `best.pt`**.
- [ ] Note the measured INT8 mAP drop and any re-calibrated thresholds
      somewhere durable (`docs/meeting_log.md` is where prior sessions have
      logged this kind of milestone).
- [ ] Ping back — next step after this is wiring `model.hef` into the actual
      camera → Hailo inference pipeline in `src/` (currently a placeholder for
      the detection callback), which is a separate piece of work.
