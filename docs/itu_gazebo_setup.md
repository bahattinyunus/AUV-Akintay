# İTÜ AUV Gazebo Sim — Hızlı Kurulum (WSL2 & Docker)

Bu rehber, `auv-software` deposundaki ROS+Gazebo tabanlı simülasyonu Windows üzerinde çalıştırmanın iki yolunu özetler: WSL2 veya Docker.

## 1) WSL2 (Önerilen)

Gereksinimler:
- Windows 11 (WSLg ile yerleşik GUI desteği)
- Microsoft Store’dan Ubuntu (WSL2) kurulmuş olmalı

Adımlar (WSL Ubuntu terminalinde):

```bash
# 1) ROS Noetic + Gazebo (Ubuntu 20.04 varsayılmıştır)
sudo apt update && sudo apt install -y curl gnupg lsb-release
sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'
curl -s https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | sudo apt-key add -
sudo apt update && sudo apt install -y ros-noetic-desktop-full

# 2) Gerekli araçlar
sudo apt install -y build-essential git python3-rosdep python3-rosinstall python3-rosinstall-generator python3-wstool
sudo rosdep init || true
rosdep update

# 3) Catkin çalışma alanı
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws/src
# Windows tarafında klonladığın auv-software klasörünü de buraya kopyala veya symlinkle
# Örn: cp -r /mnt/c/Users/<kullanıcı>/Desktop/akıntay/auv-software .

cd ~/catkin_ws
rosdep install --from-paths src -i -y
source /opt/ros/noetic/setup.bash
catkin_make
source devel/setup.bash

# 4) Gazebo’yu başlat (örn. havuz dünyası)
roslaunch auv_sim_bringup start_gazebo.launch world:=pool
```

Notlar:
- WSLg varsa ek X server gerekmez. Yoksa Windows’a X410/vcXsrv gibi bir X server kur ve `export DISPLAY` ayarla.
- Alternatif dünyalar: `seabed`, `semi_final_pool` vb. (launch altındaki world dosyalarına bak).

## 2) Docker

Gereksinimler:
- Docker Desktop + WSL2 backend
- `auv-software/docker` dizinindeki Dockerfile’lar

Kurulum/çalıştırma (PowerShell):

```powershell
# Derle
scripts\itu_sim_docker_build.ps1

# Çalıştır (GUI için WSLg veya X server gerekir)
scripts\itu_sim_docker_run.ps1
```

`itu_sim_docker_run.ps1`, konteyner içinde `roslaunch auv_sim_bringup start_gazebo.launch` komutunu çalıştırır. Gerekirse script içinde `world:=pool` parametresini değiştir.

## AKINTAY ile birlikte kullanım

- Control/teleop tarafında AKINTAY’daki `CMD:...`/`VEL:...` komut şemasını koruyarak köprü bir node ile ROS topiklerine bağlanabilirsin (ör. `cmd_vel` benzeri). Bu entegrasyon ileride eklenecektir.
