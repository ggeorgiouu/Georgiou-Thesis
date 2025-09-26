import os
import time
import psutil
from PIL import Image
import numpy as np
import degirum as dg
import csv
import argparse

mask_root = "/home/ggeorgiou/storage/pv-hawk-tutorial/workdir/segmented_yolo/masks"
roi_root = "/home/ggeorgiou/storage/pv-hawk-tutorial/workdir/segmented_yolo/rois"
os.makedirs(mask_root, exist_ok=True)
os.makedirs(roi_root, exist_ok=True)

def run_inference(image_name=None):
    # ==== CONFIGURATION ====
    folder_path = "/home/ggeorgiou/storage/pv-hawk-tutorial/workdir/splitted/radiometric"
    model_name = "yolov8_seg"
    zoo_url = "/home/ggeorgiou/hailo/hailo_examples/models"
    inference_host_address = "@local"
    token = ''
    device_type = ['HAILORT/HAILO8']
    log_results = True
    output_log = "benchmark_results.csv"
    per_frame_log = "per_frame_log_full.csv"
    summary_log = "inference_summary.csv"
    # ========================

    # Measure model loading time
    model_load_start = time.time()
    model = dg.load_model(
        model_name=model_name,
        inference_host_address=inference_host_address,
        zoo_url=zoo_url,
        token=token,
        device_type=device_type
    )
    model_load_end = time.time()
    model_load_time = model_load_end - model_load_start

    process = psutil.Process(os.getpid())

    if image_name:
        tiff_files = [image_name]
    else:
        tiff_files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(".tiff")])

    num_files = len(tiff_files)

    if num_files == 0:
        print("No TIFF files found.")
        return

    total_time = 0
    peak_mem_usage = 0

    mem_before = process.memory_info().rss / (1024 ** 2)

    # === Initialize summary log ===
    if log_results:
        file_exists = os.path.isfile(summary_log)
        with open(summary_log, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["FrameID", "ModelLoadTime(s)", "PreprocessingTime(s)", "InferenceTime(s)", "PostprocessingTime(s)"])

    for idx, filename in enumerate(tiff_files):
        filepath = os.path.join(folder_path, filename)
        frame_id = os.path.splitext(filename)[0]

        ## ==== Preprocessing Timing ====
        pre_start = time.time()

        image = Image.open(filepath)
        np_image = np.array(image)

        # Normalize 16-bit to 8-bit
        if np_image.dtype == np.uint16:
            np_image = ((np_image - np_image.min()) / np_image.ptp() * 255).astype(np.uint8)

        # Ensure 3 channels
        if np_image.ndim == 2:
            np_image = np.stack([np_image] * 3, axis=-1)
        elif np_image.shape[2] == 1:
            np_image = np.repeat(np_image, 3, axis=2)

        pre_end = time.time()
        preprocessing_time = pre_end - pre_start

        ## ==== Inference Timing ====
        inf_start = time.time()
        result = model(np_image)
        inf_end = time.time()
        inference_time = inf_end - inf_start

        ## ==== Postprocessing Timing ====
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
        with open(roi_csv_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(roi_data)
        post_end = time.time()
        postprocessing_time = post_end - post_start

        ## ==== Log Summary ====
        if log_results:
            with open(summary_log, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    frame_id,
                    f"{model_load_time:.4f}",
                    f"{preprocessing_time:.4f}",
                    f"{inference_time:.4f}",
                    f"{postprocessing_time:.4f}"
                ])

        print(f"[{idx+1}/{num_files}] {frame_id}: Pre {preprocessing_time:.4f} | Inf {inference_time:.4f} | Post {postprocessing_time:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=str, help="Optional: process only a specific TIFF image (just filename, not full path)")
    args = parser.parse_args()

    run_inference(args.image)
