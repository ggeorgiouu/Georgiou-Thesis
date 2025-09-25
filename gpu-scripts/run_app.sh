#!/bin/bash

START_TIME=$SECONDS

sudo docker run -it \
  --gpus all \
  --ipc=host \
  --env="DISPLAY" \
  --mount type=bind,src=/tmp/.X11-unix,dst=/tmp/.X11-unix \
  --mount type=bind,src="$(pwd)",dst=/pvextractor \
  --mount type=volume,dst=/pvextractor/extractor/mapping/OpenSfM \
  --mount type=bind,src=/home/ggeo/storage,dst=/storage \
  pv-hawk-custom-build_apel \
  bash -c "python main.py /storage/pv-hawk-tutorial/new_workdir"

ELAPSED_TIME=$(( SECONDS - START_TIME ))
echo "=== Total time: $((ELAPSED_TIME / 60)) minutes and $((ELAPSED_TIME % 60)) seconds ==="
