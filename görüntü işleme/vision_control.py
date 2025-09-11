import argparse
import time
import sys

import cv2
import numpy as np
import serial


def parse_args():
    p = argparse.ArgumentParser(description="AKINTAY Vision → ESP32 command sender")
    p.add_argument("--port", default="COM3", help="Serial port (e.g., COM3 or /dev/ttyUSB0)")
    p.add_argument("--baud", type=int, default=115200, help="Baud rate")
    p.add_argument("--speed", type=int, default=60, help="Command speed 0..100")
    p.add_argument("--cam", type=int, default=0, help="OpenCV camera index")
    p.add_argument("--center_tol", type=int, default=50, help="Pixel tolerance around image center")
    p.add_argument("--show", action="store_true", help="Show camera frames")
    return p.parse_args()


def send_cmd(ser, cmd_char, speed):
    speed = max(0, min(100, int(speed)))
    msg = f"CMD:{cmd_char};SPEED:{speed}\n".encode("ascii")
    ser.write(msg)


def main():
    args = parse_args()

    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.05)
    except Exception as e:
        print(f"Serial open failed: {e}")
        sys.exit(1)

    cap = cv2.VideoCapture(args.cam)
    if not cap.isOpened():
        print("Camera open failed")
        sys.exit(2)

    last_cmd = None
    last_send_ms = 0
    send_interval_ms = 150

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            lower_black = np.array([0, 0, 0])
            upper_black = np.array([180, 255, 50])
            mask = cv2.inRange(hsv, lower_black, upper_black)
            result = cv2.bitwise_and(frame, frame, mask=mask)
            result = cv2.GaussianBlur(result, (5, 5), 0)
            edges = cv2.Canny(result, 50, 150)
            edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

            contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            cmd = 'S'
            if contours:
                largest = max(contours, key=cv2.contourArea)
                M = cv2.moments(largest)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    frame_center = frame.shape[1] // 2
                    if cx < frame_center - args.center_tol:
                        cmd = 'L'
                    elif cx > frame_center + args.center_tol:
                        cmd = 'R'
                    else:
                        cmd = 'F'

            now_ms = int(time.time() * 1000)
            if cmd != last_cmd or (now_ms - last_send_ms) > send_interval_ms:
                send_cmd(ser, cmd, args.speed)
                last_cmd = cmd
                last_send_ms = now_ms

            if args.show:
                cv2.putText(frame, f"CMD:{cmd} SPEED:{args.speed}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow("AKINTAY-CAM", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    finally:
        try:
            send_cmd(ser, 'S', 0)
        except Exception:
            pass
        cap.release()
        cv2.destroyAllWindows()
        ser.close()


if __name__ == "__main__":
    main()


