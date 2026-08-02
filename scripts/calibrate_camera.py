"""
OpenCV checkerboard camera calibration.

Produces the two files docs/interface_contract.md section 2 specifies as
Aditya's deliverable: camera_matrix.npy (3x3) and dist_coeffs.npy (1x5).
Also prints the focal length in pixels (camera_matrix[0][0], the fx term),
which is the value src/distance.py's thin_lens_distance_m() needs and
scripts/run_wildlife_detection.py currently uses a placeholder for
(FOCAL_LENGTH_PX_PLACEHOLDER).

Needs a folder of checkerboard photos taken with the actual mounted camera
-- print a standard checkerboard (default assumes 9x6 internal corners,
25mm squares; adjust --cols/--rows/--square-size-mm if a different board is
used), photograph it from many angles/distances/positions in frame, and
point this script at that folder.

Run:
    python scripts/calibrate_camera.py <checkerboard_photos_dir> [options]

Example:
    python scripts/calibrate_camera.py data/calibration_photos \\
        --cols 9 --rows 6 --square-size-mm 25 \\
        --output-dir config/
"""

import argparse
import glob
import os

import cv2
import numpy as np


def calibrate(photos_dir, cols, rows, square_size_mm, output_dir):
    # Object points for one checkerboard, in the board's own coordinate
    # frame (z=0, units = mm so camera_matrix/dist_coeffs come out in
    # consistent real-world units).
    objp = np.zeros((rows * cols, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2) * square_size_mm

    obj_points = []   # 3D points in board space, one array per accepted photo
    img_points = []   # corresponding 2D corner points in image space
    image_size = None

    photo_paths = sorted(
        glob.glob(os.path.join(photos_dir, "*.jpg"))
        + glob.glob(os.path.join(photos_dir, "*.jpeg"))
        + glob.glob(os.path.join(photos_dir, "*.png"))
    )
    if not photo_paths:
        raise SystemExit(f"No images found in {photos_dir}")

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    accepted = 0
    for path in photo_paths:
        img = cv2.imread(path)
        if img is None:
            print(f"  skip (unreadable): {path}")
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if image_size is None:
            image_size = gray.shape[::-1]  # (width, height)

        found, corners = cv2.findChessboardCorners(gray, (cols, rows), None)
        if not found:
            print(f"  skip (no checkerboard found): {path}")
            continue

        corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        obj_points.append(objp)
        img_points.append(corners_refined)
        accepted += 1
        print(f"  accepted: {path}")

    if accepted < 10:
        print(
            f"\nWARNING: only {accepted} usable photos. OpenCV's docs recommend "
            "15-20+ from varied angles/distances/frame positions for a stable "
            "calibration -- treat this result as provisional if below that."
        )

    print(f"\nRunning cv2.calibrateCamera on {accepted} accepted photos...")
    reproj_error, camera_matrix, dist_coeffs, _rvecs, _tvecs = cv2.calibrateCamera(
        obj_points, img_points, image_size, None, None
    )

    os.makedirs(output_dir, exist_ok=True)
    matrix_path = os.path.join(output_dir, "camera_matrix.npy")
    dist_path = os.path.join(output_dir, "dist_coeffs.npy")
    np.save(matrix_path, camera_matrix)
    np.save(dist_path, dist_coeffs)

    fx, fy = camera_matrix[0, 0], camera_matrix[1, 1]
    print(f"\nSaved: {matrix_path}")
    print(f"Saved: {dist_path}")
    print(f"Reprojection error: {reproj_error:.4f} px (lower is better; >1.0 is usually a sign of a bad calibration)")
    print(f"Focal length: fx={fx:.2f}px, fy={fy:.2f}px")
    print(
        f"\n-> Use fx ({fx:.2f}) as --focal-length-px in "
        "scripts/run_wildlife_detection.py, replacing FOCAL_LENGTH_PX_PLACEHOLDER."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenCV checkerboard camera calibration.")
    parser.add_argument("photos_dir", help="Directory of checkerboard photos")
    parser.add_argument("--cols", type=int, default=9, help="Internal corners across (default 9)")
    parser.add_argument("--rows", type=int, default=6, help="Internal corners down (default 6)")
    parser.add_argument("--square-size-mm", type=float, default=25.0, help="Checkerboard square size in mm (default 25)")
    parser.add_argument("--output-dir", default="config", help="Where to save the .npy files (default config/)")
    args = parser.parse_args()

    calibrate(args.photos_dir, args.cols, args.rows, args.square_size_mm, args.output_dir)
