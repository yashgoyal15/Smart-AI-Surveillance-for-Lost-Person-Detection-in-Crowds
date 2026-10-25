"""
Makes a fake "camera" video from a photo, so you can test without any real camera.
It slowly pans across the photo, like a camera scanning a crowd.

    python tools/make_demo_video.py group_photo.jpg videos/cam3.mp4 --seconds 20
"""
import argparse
import cv2
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("image")
parser.add_argument("output")
parser.add_argument("--seconds", type=int, default=20)
parser.add_argument("--fps", type=int, default=15)
args = parser.parse_args()

img = cv2.imread(args.image)
if img is None:
    raise SystemExit("Cannot read image")

h, w = img.shape[:2]
out_w, out_h = 960, 540
view_w = min(w, int(h * out_w / out_h))   # window size inside the photo (same 16:9 shape)
view_h = int(view_w * out_h / out_w)

writer = cv2.VideoWriter(args.output, cv2.VideoWriter_fourcc(*"mp4v"), args.fps, (out_w, out_h))
total = args.seconds * args.fps
for i in range(total):
    t = (np.sin(i / total * 2 * np.pi - np.pi / 2) + 1) / 2     # smooth 0 -> 1 -> 0 sweep
    x = int((w - view_w) * t)
    y = int((h - view_h) / 2)
    view = img[y:y + view_h, x:x + view_w]
    writer.write(cv2.resize(view, (out_w, out_h)))
writer.release()
print(f"Wrote {args.output} ({args.seconds}s)")
