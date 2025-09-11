#!/usr/bin/env bash
set -euo pipefail

WORLD="${1:-pool}"

echo "[+] Setting up and launching ITU AUV Gazebo (world=${WORLD})"

if ! command -v roslaunch >/dev/null 2>&1; then
  echo "ROS not found. Please install ROS Noetic first (see docs/itu_gazebo_setup.md)." >&2
  exit 1
fi

if [ ! -d "${HOME}/catkin_ws" ]; then
  echo "catkin_ws missing. Create and build it per docs/itu_gazebo_setup.md" >&2
  exit 1
fi

source /opt/ros/noetic/setup.bash
cd "${HOME}/catkin_ws"
source devel/setup.bash || true

exec roslaunch auv_sim_bringup start_gazebo.launch world:=${WORLD}

