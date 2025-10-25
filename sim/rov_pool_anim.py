"""A lightweight 2D pool-style AUV animation.

Usage: python rov_pool_anim.py [--listen_port 5005] [--keyboard] [--telemetry]

This reuses the simple command parsing from the original sim but improves
rendering: pool border, water gradient, subtle caustics, and bubble particles
generated when thrust is applied.
"""
import argparse
import math
import time
import threading
import socket
import json
import numpy as np
import cv2
from collections import deque


class UdpCommandServer(threading.Thread):
    def __init__(self, host: str = "127.0.0.1", port: int = 5005):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.queue = deque(maxlen=20)
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
    if not line:
        return None, 0
    parts = line.split(";")
    cmd = None
    speed = 0
    for p in parts:
        if p.startswith("CMD:"):
            cmd = p.split(":", 1)[1].strip()[:1]
        elif p.startswith("SPEED:"):
            try:
                speed = int(p.split(":", 1)[1])
            except Exception:
                speed = 0
    return cmd, max(0, min(100, speed))


class Bubble:
    def __init__(self, pos, vel, life=1.2):
        self.pos = np.array(pos, dtype=float)
        self.vel = np.array(vel, dtype=float)
        self.life = life

    def update(self, dt):
        self.pos += self.vel * dt
        self.vel += np.array([0.0, -10.0]) * dt  # slight rise
        self.life -= dt


def draw_pool_background(img):
    h, w = img.shape[:2]
    # gradient: deeper (bottom) darker
    for y in range(h):
        t = y / h
        color = (int(200*(1-0.6*t)), int(210*(1-0.8*t)), int(255*(1-0.95*t)))
        cv2.line(img, (0, y), (w, y), color, 1)
    # subtle caustics: sinusoidal bright lines
    for i in range(6):
        freq = 0.02 + i*0.005
        amp = 8 + i*2
        offset = i*30
        for x in range(0, w, 4):
            y = int(h*0.2 + math.sin(x*freq + offset)*amp)
            cv2.line(img, (x, max(0,y-1)), (x, min(h-1,y+1)), (220,230,255), 1)


def draw_pool_border(img, margin=20):
    h, w = img.shape[:2]
    cv2.rectangle(img, (margin, margin), (w-margin, h-margin), (180, 200, 220), 4)
    # depth markers
    for i in range(1, 5):
        y = margin + i*(h - 2*margin)//5
        cv2.line(img, (margin, y), (w-margin, y), (180,200,220), 1, lineType=cv2.LINE_AA)


def draw_auv(img, pos, heading, depth, thrust_level):
    # pos: [x,y]; draw a stylized AUV with thrusters
    x, y = int(pos[0]), int(pos[1])
    body_len = 60
    body_w = 24
    pts = np.array([
        [ body_len,  0],
        [-body_len, -body_w],
        [-body_len,  body_w],
    ], dtype=float)
    ca, sa = math.cos(heading), math.sin(heading)
    rot = np.array([[ca, -sa],[sa, ca]])
    pts_rot = (pts @ rot.T) + np.array([x, y])
    cv2.fillPoly(img, [pts_rot.astype(int)], (60, 120, 200))
    # nose highlight
    nose = np.array([[body_len, 0], [body_len-14, -8], [body_len-14, 8]], dtype=float)
    nose_rot = (nose @ rot.T) + np.array([x, y])
    cv2.fillPoly(img, [nose_rot.astype(int)], (120, 190, 255))
    # thrusters (rear) — draw circles and faint glow depending on thrust
    thr_pos_local = np.array([[-body_len+6, -12], [-body_len+6, 12], [-body_len+18, -12], [-body_len+18, 12]], dtype=float)
    for tp in thr_pos_local:
        p = (tp @ rot.T) + np.array([x, y])
        radius = 6 + int(thrust_level*0.05)
        cv2.circle(img, (int(p[0]), int(p[1])), radius, (240, 250, 255), -1)
        # glow
        cv2.circle(img, (int(p[0]), int(p[1])), radius+8, (200, 230, 255), 2)


def main():
    parser = argparse.ArgumentParser(description="Pool-style AUV animation")
    parser.add_argument("--listen_host", default="127.0.0.1")
    parser.add_argument("--listen_port", type=int, default=5005)
    parser.add_argument("--keyboard", action="store_true")
    parser.add_argument("--telemetry", action="store_true")
    parser.add_argument("--width", type=int, default=1000)
    parser.add_argument("--height", type=int, default=700)
    args = parser.parse_args()

    server = UdpCommandServer(args.listen_host, args.listen_port)
    server.start()

    width, height = args.width, args.height
    pos = np.array([width//2, height//2], dtype=float)
    vel = np.zeros(2, dtype=float)
    heading = -math.pi/2
    yaw_rate = 0.0
    depth = 0.0

    max_fwd_acc = 140.0
    max_yaw_rate = math.radians(80)
    lin_drag = 0.9
    yaw_drag = 1.0

    last_cmd = '(none)'
    last_speed = 60
    last_time = time.time()

    bubbles = []

    tele_sock = None
    tele_addr = None
    if args.telemetry:
        tele_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        tele_addr = ("127.0.0.1", 5006)

    try:
        while True:
            now = time.time()
            dt = max(1e-3, min(0.05, now - last_time))
            last_time = now

            # commands
            line = server.get_latest()
            if line:
                c, s = parse_cmd(line)
                if c is not None:
                    last_cmd = c
                    last_speed = s

            # keyboard
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
                elif key == ord('q'):
                    break

            fwd_acc = 0.0
            yaw_input = 0.0
            thrust_level = 0.0
            if last_cmd == 'F':
                fwd_acc = (last_speed / 100.0) * max_fwd_acc
                thrust_level = last_speed
            elif last_cmd == 'L':
                yaw_input = -(last_speed / 100.0) * max_yaw_rate
            elif last_cmd == 'R':
                yaw_input = (last_speed / 100.0) * max_yaw_rate

            yaw_rate += (yaw_input - yaw_drag * yaw_rate) * dt
            heading += yaw_rate * dt

            forward = np.array([math.cos(heading), math.sin(heading)])
            left = np.array([-math.sin(heading), math.cos(heading)])
            acc_world = forward * fwd_acc
            vel += (acc_world - lin_drag * vel) * dt
            pos += vel * dt

            # keep inside pool margins
            margin = 40
            pos[0] = max(margin, min(width - margin, pos[0]))
            pos[1] = max(margin, min(height - margin, pos[1]))

            # bubbles when thrust
            if thrust_level > 10:
                # emit a few bubbles from rear
                for _ in range(2):
                    angle = heading + math.pi + (np.random.rand()-0.5)*0.4
                    speed = 40 + np.random.rand()*40
                    bx = pos[0] - math.cos(heading)*(60) + (np.random.rand()-0.5)*8
                    by = pos[1] - math.sin(heading)*(60) + (np.random.rand()-0.5)*8
                    bvel = np.array([math.cos(angle)*speed, math.sin(angle)*speed*0.6])
                    bubbles.append(Bubble((bx, by), bvel, life=1.2 + np.random.rand()*0.6))

            # update bubbles
            bubbles = [b for b in bubbles if b.life > 0]
            for b in bubbles:
                b.update(dt)

            # render
            img = np.zeros((height, width, 3), dtype=np.uint8)
            draw_pool_background(img)
            draw_pool_border(img, margin=margin)

            # draw bubbles (behind AUV)
            for b in bubbles:
                alpha = max(0.0, min(1.0, b.life / 1.5))
                r = int(4 + (1-alpha)*6)
                col = (int(230*alpha + 200*(1-alpha)), int(245*alpha + 220*(1-alpha)), int(255*alpha))
                cv2.circle(img, (int(b.pos[0]), int(b.pos[1])), r, col, -1, lineType=cv2.LINE_AA)
                # faint outline
                cv2.circle(img, (int(b.pos[0]), int(b.pos[1])), r+2, (200,220,240), 1)

            draw_auv(img, pos, heading, depth, thrust_level)

            # hud
            cv2.putText(img, f"CMD: {last_cmd}  SPD: {last_speed}", (16, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

            cv2.imshow("AUV Pool Sim", img)

            # telemetry
            if tele_sock is not None and tele_addr is not None:
                tele = {
                    "pos": {"x": float(pos[0]), "y": float(pos[1]), "z": float(depth)},
                    "yaw_deg": float((math.degrees(heading) % 360.0)),
                    "cmd": last_cmd,
                    "speed": int(last_speed),
                }
                try:
                    tele_sock.sendto((json.dumps(tele)+"\n").encode('ascii'), tele_addr)
                except Exception:
                    pass

    finally:
        server.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
