"""
Extract frames from road / dashcam video for domain-matched training data.

The whole dataset so far is camera-trap style imagery, which the WiRE Lab
flagged as a domain-shift risk for a windshield-mounted camera. This script
turns real driving footage (our own collection drives, or public dashcam
wildlife video) into still frames that can then be run through MegaDetector
and folded into the training set the same way the iNaturalist images were.

Frames are sampled at a fixed interval so you don't get thousands of
near-identical stills from a single encounter.

Run:
    python scripts/extract-frames.py <video_path> <output_dir> [--every N]

Example:
    python scripts/extract-frames.py hwy97-clip1.mp4 data/road/deer --every 15
"""

import argparse
import os

import cv2


def extract(video_path, output_dir, every_n_frames):
    os.makedirs(output_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(video_path))[0]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise SystemExit(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    frame_idx = 0
    saved = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_idx % every_n_frames == 0:
            out_path = os.path.join(output_dir, f"{stem}-{frame_idx:06d}.jpg")
            cv2.imwrite(out_path, frame)
            saved += 1
        frame_idx += 1

    cap.release()
    print(f"{video_path}: read {frame_idx} frames at ~{fps:.0f} fps, "
          f"saved {saved} to {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract frames from video.")
    parser.add_argument("video_path")
    parser.add_argument("output_dir")
    parser.add_argument("--every", type=int, default=15,
                        help="save one frame every N frames (default 15)")
    args = parser.parse_args()
    extract(args.video_path, args.output_dir, args.every)
