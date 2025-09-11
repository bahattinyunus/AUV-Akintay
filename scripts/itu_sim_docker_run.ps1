param(
  [string]$World = "pool"
)

# For WSLg GUI, DISPLAY should be set automatically in WSL. On Windows with X server,
# set DISPLAY and mount X socket if needed.

Write-Host "Running ITU AUV container (world=$World) ..." -ForegroundColor Cyan
docker run --rm -it \
  -e DISPLAY=$env:DISPLAY \
  --name itu-auv-sim \
  itu-auv \
  bash -lc "source /opt/ros/noetic/setup.bash && roslaunch auv_sim_bringup start_gazebo.launch world:=$World"
exit $LASTEXITCODE

