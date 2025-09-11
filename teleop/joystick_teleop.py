import argparse
import time
import serial
import pygame


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def main():
    p = argparse.ArgumentParser(description="AKINTAY joystick teleop → ESP32 serial")
    p.add_argument("--port", default="COM3")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--mode", choices=["CMD", "VEL"], default="VEL")
    p.add_argument("--dead", type=float, default=0.15, help="Axis deadzone (0..1)")
    p.add_argument("--scale", type=float, default=1.0, help="Overall scale multiplier")
    args = p.parse_args()

    ser = serial.Serial(args.port, args.baud, timeout=0.01)
    time.sleep(1.0)

    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print("No joystick/gamepad detected")
        return
    js = pygame.joystick.Joystick(0)
    js.init()
    print(f"Using joystick: {js.get_name()}")

    last_send = 0
    send_hz = 15.0

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

            # Typical gamepad: left stick (axes 0,1), right stick (axes 2,3), triggers vary
            ax0 = js.get_axis(0)  # left X (sway/yaw)
            ax1 = js.get_axis(1)  # left Y (surge)
            ax2 = js.get_axis(2)  # right X (yaw)
            ax3 = js.get_axis(3)  # right Y (heave)

            def dz(v):
                return 0.0 if abs(v) < args.dead else v

            ax0, ax1, ax2, ax3 = dz(ax0), dz(ax1), dz(ax2), dz(ax3)

            now = time.time()
            if now - last_send > 1.0 / send_hz:
                if args.mode == "CMD":
                    # Map to discrete commands
                    cmd = 'S'
                    spd = int(60 * args.scale)
                    if ax1 < -args.dead:
                        cmd = 'F'
                    elif ax0 < -args.dead:
                        cmd = 'L'
                    elif ax0 > args.dead:
                        cmd = 'R'
                    ser.write(f"CMD:{cmd};SPEED:{spd}\n".encode("ascii"))
                else:
                    # VEL: surge,sway,heave,yaw in -100..100
                    surge = int(clamp(-ax1 * 100 * args.scale, -100, 100))
                    sway  = int(clamp(ax0 * 100 * args.scale, -100, 100))
                    heave = int(clamp(-ax3 * 100 * args.scale, -100, 100))
                    yaw   = int(clamp(ax2 * 100 * args.scale, -100, 100))
                    ser.write(f"VEL:{surge},{sway},{heave},{yaw}\n".encode("ascii"))

                last_send = now

            time.sleep(0.005)

    finally:
        ser.close()
        pygame.quit()


if __name__ == "__main__":
    main()


