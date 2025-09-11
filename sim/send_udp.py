import socket
import time
import argparse


def main():
    p = argparse.ArgumentParser(description="Send demo UDP commands to AKINTAY sim")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=5005)
    p.add_argument("--speed", type=int, default=60)
    args = p.parse_args()

    addr = (args.host, args.port)
    seq = [
        f"CMD:F;SPEED:{args.speed}\n",
        "CMD:L;SPEED:40\n",
        "CMD:R;SPEED:40\n",
        f"CMD:F;SPEED:{min(100, args.speed+20)}\n",
        "CMD:S;SPEED:0\n",
    ]

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for msg in seq:
        s.sendto(msg.encode("ascii"), addr)
        time.sleep(0.7)
    s.close()


if __name__ == "__main__":
    main()


