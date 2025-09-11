#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash /mnt/c/Users/<User>/Desktop/akıntay/Teknofest-Akintay/scripts/wsl_ros_full_setup.sh \
#        "/mnt/c/Users/<User>/Desktop/akıntay/auv-software"

REPO_WIN_MOUNT_PATH="${1:-/mnt/c/Users/Bahattin Yunus/Desktop/akıntay/auv-software}"

echo "[+] ROS Noetic + Gazebo setup"
sudo apt update
sudo apt install -y curl gnupg lsb-release
if [ ! -f /etc/apt/sources.list.d/ros-latest.list ]; then
  echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" | \
    sudo tee /etc/apt/sources.list.d/ros-latest.list >/dev/null
  curl -s https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | sudo apt-key add -
fi
sudo apt update
sudo apt install -y ros-noetic-desktop-full build-essential git \
  python3-rosdep python3-rosinstall python3-rosinstall-generator python3-wstool

echo "[+] rosdep init/update"
sudo rosdep init || true
rosdep update || true

echo "[+] Create catkin workspace and import auv-software"
mkdir -p "$HOME/catkin_ws/src"
if [ -d "$REPO_WIN_MOUNT_PATH" ]; then
  rsync -a --delete "$REPO_WIN_MOUNT_PATH" "$HOME/catkin_ws/src/" || cp -r "$REPO_WIN_MOUNT_PATH" "$HOME/catkin_ws/src/"
else
  echo "[!] Repo not found at $REPO_WIN_MOUNT_PATH" >&2
  exit 1
fi

echo "[+] Install dependencies and build"
cd "$HOME/catkin_ws"
source /opt/ros/noetic/setup.bash
rosdep install --from-paths src -i -y || true
catkin_make

echo "[+] Setup complete. To launch Gazebo:"
echo "    source /opt/ros/noetic/setup.bash"
echo "    cd ~/catkin_ws && source devel/setup.bash"
echo "    roslaunch auv_sim_bringup start_gazebo.launch world:=pool"

