#!/bin/bash

START_TIME=$SECONDS

WORKDIR="/home/ggeorgiou/storage/pv-hawk-tutorial/workdir"
DOCKER_IMAGE="pvhawk-pi5"

# 1. Copy pre-segmentation config and run pipeline up to segmentation
cp $WORKDIR/config_pre.yml $WORKDIR/config.yml
sudo docker run --rm -it \
  --ipc=host \
  --env="DISPLAY" \
  --mount type=bind,src=/tmp/.X11-unix,dst=/tmp/.X11-unix \
  --mount type=bind,src="$(pwd)",dst=/pvextractor \
  --mount type=volume,dst=/pvextractor/extractor/mapping/OpenSfm \
  --mount type=bind,src=/home/ggeorgiou/storage,dst=/storage \
  $DOCKER_IMAGE \
  bash -c "python main.py /storage/pv-hawk-tutorial/workdir"

# 2. Run segmentation outside Docker in your YOLOv8 env
source /home/ggeorgiou/hailo/hailo_examples/degirum_env/bin/activate
python3 /home/ggeorgiou/power_monitor/inference_yolo.py
deactivate

# 3. Copy post-segmentation config and run rest of pipeline
cp $WORKDIR/config_after.yml $WORKDIR/config.yml
sudo docker run --rm -it \
  --ipc=host \
  --env="DISPLAY" \
  --mount type=bind,src=/tmp/.X11-unix,dst=/tmp/.X11-unix \
  --mount type=bind,src="$(pwd)",dst=/pvextractor \
  --mount type=volume,dst=/pvextractor/extractor/mapping/OpenSfm \
  --mount type=bind,src=/home/ggeorgiou/storage,dst=/storage \
  $DOCKER_IMAGE \
  bash -c "python main.py /storage/pv-hawk-tutorial/workdir"

ELAPSED_TIME=$(( SECONDS - START_TIME ))
echo "=== Total time: $((ELAPSED_TIME / 60)) minutes and $((ELAPSED_TIME % 60)) seconds ==="
