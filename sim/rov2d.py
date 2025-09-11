import socket
import time
import math
import threading
from collections import deque
import argparse

import cv2
import numpy as np


class UdpCommandServer(threading.Thread):
    def __init__(self, host: str = "127.0.0.1", port: int = 5005):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.queue = deque(maxlen=10)
        self.running = True

    def run(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(1024)
                self.queue.append(data.decode("utf-8", errors="ignore").strip())
            except Exception:
                time.sleep(0.01)

    def get_latest(self):
        if not self.queue:
            return None
        return self.queue.pop()

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass


def parse_cmd(line: str):
    # Expected: CMD:F;SPEED:60
    if not line:
        return None, None
    parts = line.split(";")
    cmd_char = None
    speed = 0
    for p in parts:
        if p.startswith("CMD:"):
            cmd_char = p.split(":", 1)[1].strip()[:1]
        elif p.startswith("SPEED:"):
            try:
                speed = int(p.split(":", 1)[1])
            except Exception:
                speed = 0
    return cmd_char, max(0, min(100, speed))


def draw_arrow(img, x, y, angle, length=50, color=(0, 255, 0), thickness=2):
    end_x = int(x + length * math.cos(angle))
    end_y = int(y + length * math.sin(angle))
    cv2.arrowedLine(img, (int(x), int(y)), (end_x, end_y), color, thickness, tipLength=0.25)


def main():
    parser = argparse.ArgumentParser(description="AKINTAY 2D ROV Simulator")
    parser.add_argument("--listen_host", default="127.0.0.1", help="UDP listen host for control")
    parser.add_argument("--listen_port", type=int, default=5005, help="UDP listen port for control")
    parser.add_argument("--keyboard", action="store_true", help="Enable keyboard control (W/A/D to drive, S to stop, +/- speed)")
    parser.add_argument("--trail", action="store_true", help="Draw motion trail")
    parser.add_argument("--obstacles", action="store_true", help="Add static circular obstacles")
    parser.add_argument("--telemetry", action="store_true", help="Enable UDP telemetry broadcast of pose")
    parser.add_argument("--telemetry_host", default="127.0.0.1", help="Telemetry UDP host")
    parser.add_argument("--telemetry_port", type=int, default=5006, help="Telemetry UDP port")
    parser.add_argument("--width", type=int, default=900, help="Window width")
    parser.add_argument("--height", type=int, default=600, help="Window height")
    parser.add_argument("--max_acc", type=float, default=120.0, help="Max forward acceleration (px/s^2) at speed=100")
    parser.add_argument("--max_yaw", type=float, default=60.0, help="Max yaw rate (deg/s) at speed=100")
    parser.add_argument("--lin_drag", type=float, default=0.8, help="Linear drag (1/s)")
    parser.add_argument("--yaw_drag", type=float, default=1.0, help="Yaw drag (1/s)")
    args = parser.parse_args()

    server = UdpCommandServer(args.listen_host, args.listen_port)
    server.start()

    width, height = args.width, args.height
    center = np.array([width // 2, height // 2], dtype=float)

    # State
    pos = center.copy()
    vel = np.zeros(2, dtype=float)
    heading = -math.pi / 2  # up
    yaw_rate = 0.0

    # Parameters
    max_fwd_acc = float(args.max_acc)  # px/s^2 at speed=100
    max_yaw_rate = math.radians(float(args.max_yaw))  # rad/s at speed=100
    lin_drag = float(args.lin_drag)  # per second
    yaw_drag = float(args.yaw_drag)  # per second

    last_cmd = "(none)"
    last_speed = 60  # default keyboard speed
    last_time = time.time()

    # Trail
    trail = deque(maxlen=500)

    # Obstacles
    rng = np.random.default_rng(42)
    obstacles = []
    if args.obstacles:
        for _ in range(8):
            x = float(rng.integers(60, width - 60))
            y = float(rng.integers(60, height - 60))
            r = float(rng.integers(20, 40))
            obstacles.append((x, y, r))

    # Telemetry socket
    tele_sock = None
    tele_addr = None
    if args.telemetry:
        tele_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        tele_addr = (args.telemetry_host, args.telemetry_port)

    try:
        while True:
            now = time.time()
            dt = max(1e-3, min(0.05, now - last_time))
            last_time = now

            # Handle incoming command
            line = server.get_latest()
            if line:
                c, s = parse_cmd(line)
                if c is not None:
                    last_cmd = c
                    last_speed = s

            # Keyboard override (if enabled)
            key = cv2.waitKey(1) & 0xFF
            if args.keyboard:
                if key in (ord('w'), ord('W')):
                    last_cmd = 'F'
                elif key in (ord('a'), ord('A')):
                    last_cmd = 'L'
                elif key in (ord('d'), ord('D')):
                    last_cmd = 'R'
                elif key in (ord('s'), ord('S')):
                    last_cmd = 'S'
                elif key in (ord('+'), ord('=')):
                    last_speed = min(100, last_speed + 5)
                elif key in (ord('-'), ord('_')):
                    last_speed = max(0, last_speed - 5)
                elif key == ord('q'):
                    break

            # Compute control inputs
            fwd_acc = 0.0
            yaw_input = 0.0
            if last_cmd == 'F':
                fwd_acc = (last_speed / 100.0) * max_fwd_acc
            elif last_cmd == 'L':
                yaw_input = -(last_speed / 100.0) * max_yaw_rate
            elif last_cmd == 'R':
                yaw_input = (last_speed / 100.0) * max_yaw_rate
            else:
                # 'S' or None → no thrust
                pass

            # Update yaw/heading
            yaw_rate += (yaw_input - yaw_drag * yaw_rate) * dt
            heading += yaw_rate * dt

            # Forward acceleration in world frame
            acc_world = np.array([math.cos(heading), math.sin(heading)]) * fwd_acc
            vel += (acc_world - lin_drag * vel) * dt
            pos += vel * dt

            # Boundaries wrap-around
            if pos[0] < 0: pos[0] += width
            if pos[0] > width: pos[0] -= width
            if pos[1] < 0: pos[1] += height
            if pos[1] > height: pos[1] -= height

            # Render
            img = np.zeros((height, width, 3), dtype=np.uint8)

            # Obstacles
            if obstacles:
                for (ox, oy, orad) in obstacles:
                    cv2.circle(img, (int(ox), int(oy)), int(orad), (80, 80, 80), thickness=2)
            # Body
            body_len = 40
            body_w = 20
            pts = np.array([
                [ body_len,  0],
                [-body_len, -body_w],
                [-body_len,  body_w],
            ], dtype=float)
            ca, sa = math.cos(heading), math.sin(heading)
            rot = np.array([[ca, -sa],[sa, ca]])
            pts_rot = (pts @ rot.T) + pos
            cv2.fillPoly(img, [pts_rot.astype(int)], (80, 160, 255))

            # Trail
            if args.trail:
                trail.append((int(pos[0]), int(pos[1])))
                if len(trail) > 2:
                    cv2.polylines(img, [np.array(trail, dtype=np.int32)], isClosed=False, color=(0, 200, 200), thickness=2)

            draw_arrow(img, pos[0], pos[1], heading, 60, (0, 255, 0), 2)

            hud = [
                f"CMD: {last_cmd}  SPEED: {last_speed}",
                f"POS: ({pos[0]:.1f}, {pos[1]:.1f})  V: ({vel[0]:.1f},{vel[1]:.1f})",
                f"HDG: {math.degrees(heading)%360:.1f} deg  YawRate: {math.degrees(yaw_rate):.1f} deg/s",
                f"Listen UDP {args.listen_host}:{args.listen_port}  |  Press 'q' to quit",
                f"Keys: W/A/D drive, S stop, +/- speed  |  trail={args.trail} obstacles={bool(obstacles)}",
            ]
            y0 = 20
            for line in hud:
                cv2.putText(img, line, (16, y0), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
                y0 += 24

            cv2.imshow("AKINTAY ROV 2D SIM", img)

            # Telemetry
            if tele_sock is not None:
                msg = f"POSE:{pos[0]:.2f},{pos[1]:.2f},{math.degrees(heading)%360:.2f}\n".encode("ascii")
                tele_sock.sendto(msg, tele_addr)

    finally:
        server.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()


