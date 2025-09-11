import socket
import time
import math
import threading
from collections import deque

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
    server = UdpCommandServer()
    server.start()

    width, height = 900, 600
    center = np.array([width // 2, height // 2], dtype=float)

    # State
    pos = center.copy()
    vel = np.zeros(2, dtype=float)
    heading = -math.pi / 2  # up
    yaw_rate = 0.0

    # Parameters
    max_fwd_acc = 120.0  # px/s^2 at speed=100
    max_yaw_rate = math.radians(60.0)  # rad/s at speed=100
    lin_drag = 0.8  # per second
    yaw_drag = 1.0  # per second

    last_cmd = "(none)"
    last_speed = 0
    last_time = time.time()

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

            draw_arrow(img, pos[0], pos[1], heading, 60, (0, 255, 0), 2)

            hud = [
                f"CMD: {last_cmd}  SPEED: {last_speed}",
                f"POS: ({pos[0]:.1f}, {pos[1]:.1f})  V: ({vel[0]:.1f},{vel[1]:.1f})",
                f"HDG: {math.degrees(heading)%360:.1f} deg  YawRate: {math.degrees(yaw_rate):.1f} deg/s",
                "Listen UDP 127.0.0.1:5005  |  Press 'q' to quit",
            ]
            y0 = 20
            for line in hud:
                cv2.putText(img, line, (16, y0), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
                y0 += 24

            cv2.imshow("AKINTAY ROV 2D SIM", img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        server.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()


