"""Simple 3D-like pool AUV visualization.

Usage:
  python rov_pool_3d.py --keyboard --telemetry

Controls (keyboard mode):
  W/A/D : forward / left / right (yaw)
  S     : stop
  R     : dive (increase depth)
  F     : rise (decrease depth)
  Q     : quit

This script receives the same UDP commands as the other sims (CMD:/VEL) and
visualizes a pseudo-3D AUV: depth affects vertical screen position and scale,
and shadow/blur show proximity to pool floor.
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


def parse_vel(line: str):
    # Expected: VEL:surge,sway,heave,yaw
    if not line or not line.startswith("VEL:"):
        return None
    vals = line.split(":", 1)[1]
    parts = vals.split(",")
    if len(parts) != 4:
        return None
    try:
        surge = int(parts[0]); sway = int(parts[1]); heave = int(parts[2]); yaw = int(parts[3])
        def clamp100(v):
            return max(-100, min(100, v))
        return [clamp100(surge), clamp100(sway), clamp100(heave), clamp100(yaw)]
    except Exception:
        return None


def draw_water_background(img):
    h, w = img.shape[:2]
    # vertical gradient (surface brighter)
    for y in range(h):
        t = y / h
        col = (int(70 + 100*(1-t)), int(130 + 90*(1-t)), int(200 + 55*(1-t)))
        cv2.line(img, (0, y), (w, y), col, 1)
    # slight vignette for depth feel
    overlay = img.copy()
    cv2.circle(overlay, (w//2, int(h*0.35)), int(min(w,h)*0.6), (0,0,0), -1)
    cv2.addWeighted(overlay, 0.05, img, 0.95, 0, img)


def draw_seabed(img, floor_y):
    """Draw a textured seabed (sand/tiles) below floor_y."""
    h, w = img.shape[:2]
    # simple noise texture
    sand = np.zeros((h, w, 3), dtype=np.uint8)
    rng = np.random.RandomState(42)
    noise = (rng.rand(h, w) * 40).astype(np.uint8)
    sand[:, :, 0] = 150 + noise
    sand[:, :, 1] = 140 + (noise // 2)
    sand[:, :, 2] = 110 + (noise // 3)
    # mask only below floor_y
    if floor_y < h:
        img[floor_y:h, :] = cv2.addWeighted(img[floor_y:h, :], 0.6, sand[floor_y:h, :], 0.4, 0)


def draw_pool_objects(img, floor_y):
    h, w = img.shape[:2]
    rng = np.random.default_rng(123)
    # place some rocks and lane markers similar to Gazebo pool
    for i in range(6):
        rx = int(w*0.12 + i*(w*0.12) + (rng.random()-0.5)*40)
        ry = int(floor_y - 20 - (rng.random()*40))
        rr = int(12 + rng.integers(0, 24))
        cv2.circle(img, (rx, ry), rr, (80, 80, 90), -1)
        cv2.circle(img, (rx+int(rr*0.4), ry-int(rr*0.2)), int(rr*0.4), (110,110,120), -1)
    # lane lines on floor
    for lx in range(1,4):
        x = int(w*0.25*lx)
        cv2.line(img, (x, floor_y-2), (x, h-10), (100,110,120), 2)


def project_3d_to_2d(x, y, z, cam_z, base_y, max_depth, height_scale=0.6):
    """Simple projection: x maps across screen, z (depth) affects vertical offset and scale.
    cam_z is camera height above surface (negative number, e.g. -300), base_y is surface Y coordinate on screen."""
    # normalized depth 0..1 (0 surface, 1 max_depth)
    nd = max(0.0, min(1.0, z / max_depth))
    # vertical shift: deeper => closer to bottom
    y2 = base_y + nd * (base_y * height_scale)
    # scale: deeper => slightly smaller
    scale = 1.0 - 0.45 * nd
    # small perspective x offset depending on depth (parallax)
    x2 = x + (nd - 0.5) * 20
    return int(x2), int(y2), scale


def draw_auv_3d(img, screen_x, screen_y, heading, scale, depth):
    # body dimensions scaled; add small pitch based on depth change for realism
    body_len = int(60 * scale)
    body_w = int(24 * scale)
    # compute a small pitch angle from depth (deeper -> small nose-up/down visual)
    pitch = max(-0.25, min(0.25, (depth - 50.0) / 300.0))
    # construct 3D-like hull (apply pitch by shifting nose/ tail in y)
    pts = np.array([
        [ body_len,  0 - pitch*20],
        [-body_len, -body_w + pitch*10],
        [-body_len,  body_w - pitch*10],
    ], dtype=float)
    ca, sa = math.cos(heading), math.sin(heading)
    rot = np.array([[ca, -sa],[sa, ca]])
    pos = np.array([screen_x, screen_y])
    pts_rot = (pts @ rot.T) + pos
    cv2.fillPoly(img, [pts_rot.astype(int)], (40, 100, 200))
    # top shading
    top = np.array([[body_len, 0 - pitch*18], [0, -int(body_w*0.6) + pitch*6], [-body_len+6, 0 + pitch*6]], dtype=float)
    top_rot = (top @ rot.T) + pos
    cv2.fillPoly(img, [top_rot.astype(int)], (90, 160, 240))
    # add small highlights
    cv2.line(img, tuple(pts_rot[0].astype(int)), tuple(((pts_rot[1]+pts_rot[2])/2).astype(int)), (160,200,240), 1)


def draw_shadow(img, screen_x, screen_y, scale, depth, floor_y):
    # shadow becomes larger and blurrier as the AUV approaches floor
    # depth: 0..max_depth; use proximity = (max_depth - depth)
    max_depth = 200.0
    prox = max(0.0, min(1.0, (max_depth - depth) / max_depth))
    r = int(30 * scale + 40*(1-prox))
    sx = int(screen_x)
    sy = int(floor_y)
    overlay = img.copy()
    alpha = 0.25 + 0.5*(1-prox)
    cv2.ellipse(overlay, (sx, sy), (r, int(r*0.5)), 0, 0, 360, (10, 20, 30), -1)
    cv2.addWeighted(overlay, alpha, img, 1-alpha, 0, img)


def main():
    parser = argparse.ArgumentParser(description="Pseudo-3D pool AUV sim")
    parser.add_argument("--listen_host", default="127.0.0.1")
    parser.add_argument("--listen_port", type=int, default=5005)
    parser.add_argument("--keyboard", action="store_true")
    parser.add_argument("--telemetry", action="store_true")
    parser.add_argument("--width", type=int, default=1000)
    parser.add_argument("--height", type=int, default=700)
    args = parser.parse_args()

    server = UdpCommandServer(args.listen_host, args.listen_port)
    server.start()

    w, h = args.width, args.height
    # logical world coordinates map to screen: use center
    world_center = np.array([w//2, h//3], dtype=float)

    pos = np.array([0.0, 0.0])  # x,y in world coordinates (relative)
    vel = np.zeros(2)
    heading = -math.pi/2
    yaw_rate = 0.0

    depth = 20.0  # meters (0=surface)
    vdepth = 0.0
    max_depth = 200.0
    buoyancy = -5.0  # positive sinks, negative floats (tweakable)

    max_fwd_acc = 160.0
    max_yaw_rate = math.radians(90)
    lin_drag = 0.9
    yaw_drag = 1.0

    last_cmd = '(none)'
    last_speed = 60
    last_time = time.time()

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

            line = server.get_latest()
            # defaults for this step
            fwd_acc = 0.0
            yaw_input = 0.0

            if line:
                vel_cmd = parse_vel(line)
                if vel_cmd is not None:
                    # VEL: surge,sway,heave,yaw
                    surge, sway, heave, yaw = vel_cmd
                    # map surge to forward acc; yaw to yaw_input; heave to vertical thrust
                    last_speed = int(abs(surge))
                    fwd_acc = (surge / 100.0) * max_fwd_acc
                    yaw_input = (yaw / 100.0) * max_yaw_rate
                    # heave positive -> descend
                    vdepth += (heave / 100.0) * 20.0 * dt
                else:
                    cparts = line.split(";")
                    # parse CMD if present
                    for p in cparts:
                        if p.startswith("CMD:"):
                            last_cmd = p.split(":",1)[1].strip()[:1]
                        if p.startswith("SPEED:"):
                            try:
                                last_speed = int(p.split(":",1)[1])
                            except Exception:
                                pass
                    if last_cmd == 'F':
                        fwd_acc = (last_speed/100.0)*max_fwd_acc
                    else:
                        fwd_acc = 0.0
                    if last_cmd == 'L':
                        yaw_input = - (last_speed/100.0) * max_yaw_rate
                    elif last_cmd == 'R':
                        yaw_input = (last_speed/100.0) * max_yaw_rate
                    else:
                        yaw_input = 0.0

            # keyboard controls
            key = cv2.waitKey(1) & 0xFF
            if args.keyboard:
                if key in (ord('w'), ord('W')):
                    last_cmd = 'F'; fwd_acc = (last_speed/100.0)*max_fwd_acc
                elif key in (ord('a'), ord('A')):
                    last_cmd = 'L'; yaw_input = - (last_speed/100.0) * max_yaw_rate
                elif key in (ord('d'), ord('D')):
                    last_cmd = 'R'; yaw_input = (last_speed/100.0) * max_yaw_rate
                elif key in (ord('s'), ord('S')):
                    last_cmd = 'S'; fwd_acc = 0.0; yaw_input = 0.0
                elif key in (ord('r'), ord('R')):
                    # dive
                    vdepth += 30.0 * dt
                elif key in (ord('f'), ord('F')):
                    # rise
                    vdepth -= 30.0 * dt
                elif key in (ord('q'), ord('Q')):
                    break

            # dynamics
            yaw_rate += (yaw_input - yaw_drag * yaw_rate) * dt
            heading += yaw_rate * dt

            forward = np.array([math.cos(heading), math.sin(heading)])
            acc_world = forward * fwd_acc
            vel += (acc_world - lin_drag * vel) * dt
            pos += vel * dt

            # vertical dynamics: buoyancy acts as constant force
            # simple PID-free: vdepth integrates and depth integrates
            vdepth += (buoyancy) * dt
            depth += vdepth * dt
            # clamp depth
            depth = max(0.0, min(max_depth, depth))

            # rendering
            img = np.zeros((h, w, 3), dtype=np.uint8)
            draw_water_background(img)

            # world->screen mapping: center plus pos offset
            screen_x = world_center[0] + pos[0]
            surface_y = int(h*0.25)
            sx, sy, scale = project_3d_to_2d(screen_x, world_center[1]+pos[1], depth, cam_z=-300, base_y=surface_y, max_depth=max_depth)

            # floor and objects to emulate Gazebo pool
            floor_y = int(h*0.85)
            draw_seabed(img, floor_y)
            draw_pool_objects(img, floor_y)

            # shadow on floor (use floor_y)
            draw_shadow(img, sx, sy, scale, depth, floor_y)

            draw_auv_3d(img, sx, sy, heading, scale, depth)

            # HUD + depth bar
            cv2.putText(img, f"Depth: {depth:.1f} m  vZ: {vdepth:.1f} m/s", (16, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            # depth gauge on right
            gx, gy = w-60, int(h*0.15)
            gh = int(h*0.6)
            cv2.rectangle(img, (gx, gy), (gx+20, gy+gh), (230,230,230), 1)
            dp = depth / max_depth
            fill_h = int(gh * min(1.0, dp))
            cv2.rectangle(img, (gx+2, gy+gh-fill_h+2), (gx+18, gy+gh-2), (200,80,80), -1)

            cv2.imshow("AUV Pool 3D", img)

            # telemetry
            if tele_sock is not None and tele_addr is not None:
                tele = {"pos": {"x": float(pos[0]), "y": float(pos[1]), "z": float(depth)},
                        "yaw_deg": float((math.degrees(heading) % 360.0)),
                        "vel": {"x": float(vel[0]), "y": float(vel[1])}}
                try:
                    tele_sock.sendto((json.dumps(tele)+"\n").encode('ascii'), tele_addr)
                except Exception:
                    pass

    finally:
        server.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
