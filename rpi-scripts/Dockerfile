# Use ARM64-compatible Python base image
FROM python:3.9-slim

# Set working directory
WORKDIR /

# Install system dependencies including OpenCV
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential cmake git curl pkg-config \
    libsm6 libxext6 libxrender-dev python3-tk \
    libgl1-mesa-dev libglew-dev libegl1-mesa-dev \
    libwayland-dev libxkbcommon-dev wayland-protocols \
    libeigen3-dev doxygen libjpeg-dev libtiff-dev \
    libpng-dev libavcodec-dev libavformat-dev libswscale-dev \
    libv4l-dev libxvidcore-dev libx264-dev \
    libgtk-3-dev libcanberra-gtk* libatlas-base-dev gfortran \
    python3-dev qtdeclarative5-dev \
    libopencv-dev python3-opencv \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y libgeos-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Enhanced dependencies for Ceres Solver on ARM64
RUN apt-get update && apt-get install -y \
    python3-distutils python3-setuptools python3-wheel \
    build-essential proj-bin proj-data libproj-dev \
    libgoogle-glog-dev libgflags-dev libsuitesparse-dev \
    libblas-dev liblapack-dev \
    libatlas-base-dev \
    libeigen3-dev \
    libcxsparse3 \
    libmetis-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools
RUN pip install --upgrade pip setuptools wheel

# Install compatible setuptools version
RUN pip install "setuptools<60"

# Install pyproj with compatible version
RUN pip install "pyproj>=3.3,<3.5"

# Install numpy first (many packages depend on it)
RUN pip install "numpy>=1.21,<1.25"

# Copy and install Python requirements (remove opencv-python-headless from requirements.txt)
COPY requirements.txt /
RUN pip install -r /requirements.txt

# --------------------------
# Pangolin Viewer
# --------------------------
RUN python3 -m pip install pyopengl Pillow pybind11

WORKDIR /home
RUN git clone https://github.com/lukasbommes-forked-projects/Pangolin.git pangolin
WORKDIR /home/pangolin
RUN git submodule update --init
WORKDIR /home/pangolin/build
RUN cmake .. && cmake --build . -j1 && cmake --build . --target doc

# --------------------------
# Ceres Solver - Updated version and improved configuration
# --------------------------
WORKDIR /source
# Use a more recent version that has better ARM64 support
RUN curl -L http://ceres-solver.org/ceres-solver-2.1.0.tar.gz | tar xz
WORKDIR /source/ceres-solver-2.1.0

# Create build directory and configure with ARM64-optimized settings
RUN mkdir build && cd build && \
    cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_FLAGS="-fPIC -O2" \
    -DCMAKE_CXX_FLAGS="-fPIC -O2" \
    -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
    -DBUILD_EXAMPLES=OFF \
    -DBUILD_TESTING=OFF \
    -DMINIGLOG=ON \
    -DGFLAGS=OFF \
    -DSUITESPARSE=ON \
    -DCXSPARSE=ON \
    -DLAPACK=ON \
    -DBUILD_SHARED_LIBS=ON \
    && make -j1 && make install && ldconfig

# Clean up Ceres build files to save space
RUN rm -rf /source/ceres-solver-2.1.0

# --------------------------
# pyg2o
# --------------------------
WORKDIR /code
RUN git clone https://github.com/lukasbommes-forked-projects/g2opy.git
WORKDIR /code/g2opy
# Create build directory first
RUN mkdir -p build
WORKDIR /code/g2opy/build

# ❗ Remove -msse4.2 from any CMakeLists before building
RUN sed -i 's/-msse4.2//g' $(find .. -name "CMakeLists.txt") || true

# ✅ Now run cmake and build
RUN cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
    && make -j1 && make install && ldconfig

WORKDIR /code/g2opy
RUN python setup.py install


# --------------------------
# OpenSfM
# --------------------------
COPY ./extractor/mapping/OpenSfM /pvextractor/extractor/mapping/OpenSfM
WORKDIR /pvextractor/extractor/mapping/OpenSfM
RUN pip install "Sphinx>=3.4.3,<5.0"


RUN python setup.py build

# --------------------------
# Mask R-CNN
# --------------------------
COPY ./extractor/segmentation/Mask_RCNN /pvextractor/extractor/segmentation/Mask_RCNN
WORKDIR /pvextractor/extractor/segmentation/Mask_RCNN
RUN python setup.py install

# Final workdir
WORKDIR /pvextractor