#!/bin/bash

START_TIME=$SECONDS

WORKDIR="/home/ggeorgiou/storage/pv-hawk-tutorial/workdir"
DOCKER_IMAGE="pvhawk-pi5"
YOLO_SCRIPT="/home/ggeorgiou/power_monitor/inference_server.py"
YOLO_ENV="/home/ggeorgiou/hailo/hailo_examples/degirum_env/bin/activate"
FIFO_PATH="/tmp/hailo_pipe"

# Step 0: Get all frame IDs (assumes radiometric TIFFs)
FRAME_DIR="$WORKDIR/splitted/radiometric"
FRAME_IDS=$(ls $FRAME_DIR | sed 's/\.[^.]*$//' | sort)

echo "Found $(echo "$FRAME_IDS" | wc -l) frames to process."

# Step 1: Set up FIFO
if [[ ! -p $FIFO_PATH ]]; then
  echo "Creating FIFO at $FIFO_PATH"
  mkfifo $FIFO_PATH
fi

# Step 2: Start persistent inference server with log file
echo "Starting segmentation server..."
source $YOLO_ENV
python3 $YOLO_SCRIPT < $FIFO_PATH > inference_server.log 2>&1 &
INFER_PID=$!
echo "Segmentation server PID: $INFER_PID"
sleep 1  # Give it time to start

# Step 3: Initialize CSV output
echo "frame_id,duration_sec,inter_frame_latency_sec" > frame_timings_seg_and_tracking.csv

last_end_time=""

# Step 4: Process frames
for FRAME_ID in $FRAME_IDS; do
  echo "=== Processing frame: $FRAME_ID ==="
  start_time=$(date +%s.%3N)

  # Calculate inter-frame latency (if not first frame)
  if [[ -n "$last_end_time" ]]; then
    inter_latency=$(echo "$start_time - $last_end_time" | bc)
  else
    inter_latency=0
  fi

  # Step 4.1: Run segmentation by sending frame name to FIFO
  echo "-> Sending $FRAME_ID.tiff to inference server"
  echo "$FRAME_ID.tiff" > $FIFO_PATH

  # Step 4.2: Wait for segmentation output (ROI CSV file) with timeout
  ROI_PATH="$WORKDIR/segmented_yolo/rois/${FRAME_ID}.csv"
  timeout=30
  elapsed=0
  while [[ ! -f "$ROI_PATH" && $(echo "$elapsed < $timeout" | bc) -eq 1 ]]; do
    sleep 0.1
    elapsed=$(echo "$elapsed + 0.1" | bc)
  done

  if [[ ! -f "$ROI_PATH" ]]; then
    echo "Timeout waiting for ROI file: $ROI_PATH"
    kill $INFER_PID
    wait $INFER_PID 2>/dev/null
    rm -f $FIFO_PATH
    exit 1
  fi

  # Step 4.3: Run tracking + quads inside Docker
  echo "-> Running tracking + quads for $FRAME_ID"
  sudo docker run --rm -it \
    --ipc=host \
    --env="DISPLAY" \
    --mount type=bind,src=/tmp/.X11-unix,dst=/tmp/.X11-unix \
    --mount type=bind,src="$(pwd)",dst=/pvextractor \
    --mount type=volume,dst=/pvextractor/extractor/mapping/OpenSfm \
    --mount type=bind,src=/home/ggeorgiou/storage,dst=/storage \
    $DOCKER_IMAGE \
    bash -c "python main.py /storage/pv-hawk-tutorial/workdir --frame_id $FRAME_ID"

  end_time=$(date +%s.%3N)
  duration_sec=$(echo "$end_time - $start_time" | bc)

  echo "=== Done with frame: $FRAME_ID in ${duration_sec} seconds ==="
  echo "$FRAME_ID,$duration_sec,$inter_latency" >> frame_timings_seg_and_tracking.csv

  # Update last_end_time for next iteration
  last_end_time=$end_time
done

#python3 publish_folders.py


# Step 5: Done — cleanup
echo "All frames processed. Cleaning up..."

# Kill the Python inference server
kill $INFER_PID
wait $INFER_PID 2>/dev/null

# Remove FIFO
rm -f $FIFO_PATH

ELAPSED_TIME=$(( SECONDS - START_TIME ))
echo "=== Total time: $((ELAPSED_TIME / 60)) minutes and $((ELAPSED_TIME % 60)) seconds ==="
