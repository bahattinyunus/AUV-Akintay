# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2025-09-11

### Added
- MODE:VEL and `VEL:surge,sway,heave,yaw` support in `AKINTAY_Main_Firmware.ino`
- 2D simulator enhancements: keyboard controls, trail, obstacles, adjustable physics, telemetry
- Simulation GUI `sim/sim_gui.py` (Start/Stop, directional buttons, speed slider, telemetry)
- Joystick teleop `teleop/joystick_teleop.py` (CMD/VEL modes)

### Changed
- README updated with simulation, GUI, and teleop usage
- requirements.txt updated (pygame, argparse)

## [0.1.0] - 2025-09-11

### Added
- Unified ESP32 firmware `deneyap/AKINTAY_Main_Firmware.ino` (MANUAL/VISION/STAB, failsafe, RPi PHOTO/VIDEO commands)
- Vision command sender `görüntü işleme/vision_control.py` with parameterized protocol `CMD:X;SPEED:Y`
- CI workflow (Python lint), issue templates

### Changed
- README overhauled; added structure, usage, protocol, roadmap

### Removed
- Legacy demos, experiments and large ML model files to simplify the repo


