import os
import sys
import time
import select
from PIL import Image
import numpy as np
import degirum as dg

# Paths
mask_root = "/home/ggeorgiou/storage/pv-hawk-tutorial/workdir/segmented_yolo/masks"
roi_root = "/home/ggeorgiou/storage/pv-hawk-tutorial/workdir/segmented_yolo/rois"
folder_path = "/home/ggeorgiou/storage/pv-hawk-tutorial/workdir/splitted/radiometric"
csv_log_path = "/home/ggeorgiou/storage/pv-hawk-tutorial/workdir/segmentation_timings.csv"

os.makedirs(mask_root, exist_ok=True)
os.makedirs(roi_root, exist_ok=True)

# Initialize CSV log
if not os.path.exists(csv_log_path):
    with open(csv_log_path, "w") as f:
        f.write("frame_id,model_load_time_s,preprocessing_time_s,inference_time_s,postprocessing_time_s\n")

# Load the model once
print("[INFO] Loading HAILO model...")
model_load_start = time.time()
model = dg.load_model(
    model_name="yolov8_seg",
    inference_host_address="@local",
    zoo_url="/home/ggeorgiou/hailo/hailo_examples/models",
    device_type=['HAILORT/HAILO8']
)
model_load_time = time.time() - model_load_start
print(f"[INFO] Model loaded in {model_load_time:.4f}s. Waiting for frames...")

# Open FIFO (stdin)
fifo_fd = sys.stdin.fileno()

while True:
    # Wait until FIFO has data
    rlist, _, _ = select.select([fifo_fd], [], [], 1.0)
    if fifo_fd not in rlist:
        continue  # Timeout, no input

    line = sys.stdin.readline()
    if not line:
        continue  # EOF or empty line

    image_name = line.strip()
    if not image_name:
        continue

    frame_id = os.path.splitext(image_name)[0]
    image_path = os.path.join(folder_path, image_name)

    if not os.path.exists(image_path):
        print(f"[WARN] File not found: {image_path}")
        continue

    print(f"[INFO] Processing {frame_id}")

    # Measure times
    pre_start = time.time()

    # Preprocess
    image = Image.open(image_path)
    np_image = np.array(image)

    if np_image.dtype == np.uint16:
        np_image = ((np_image - np_image.min()) / np_image.ptp() * 255).astype(np.uint8)
    if np_image.ndim == 2:
        np_image = np.stack([np_image] * 3, axis=-1)
    elif np_image.shape[2] == 1:
        np_image = np.repeat(np_image, 3, axis=2)

    pre_end = time.time()

    # Inference
    inf_start = time.time()
    result = model(np_image)
    inf_end = time.time()

    # Postprocess and save
    post_start = time.time()
    detections = result.results
    frame_mask_dir = os.path.join(mask_root, frame_id)
    os.makedirs(frame_mask_dir, exist_ok=True)
    roi_data = []

    for i, det in enumerate(detections):
        mask = det["mask"]
        mask_img = (mask * 255).astype(np.uint8)
        mask_pil = Image.fromarray(mask_img)
        mask_pil.save(os.path.join(frame_mask_dir, f"mask_{i:06d}.png"))

        x1, y1, x2, y2 = map(int, det["bbox"])
        score = float(det["score"])
        roi_data.append([x1, y1, x2, y2, 1, score])

    roi_csv_path = os.path.join(roi_root, f"{frame_id}.csv")
    with open(roi_csv_path, "w") as f:
        for row in roi_data:
            f.write(",".join(map(str, row)) + "\n")

    post_end = time.time()

    # Log timings
    with open(csv_log_path, "a") as f:
        f.write(f"{frame_id},{model_load_time:.4f},{pre_end - pre_start:.4f},{inf_end - inf_start:.4f},{post_end - post_start:.4f}\n")

    print(f"[DONE] {frame_id} timings saved to CSV.")
