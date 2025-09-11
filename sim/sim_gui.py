import subprocess
import sys
import time
import socket
import threading
from tkinter import Tk, Frame, Button, Label, Scale, HORIZONTAL, StringVar, Entry


class TelemetryListener(threading.Thread):
    def __init__(self, host="127.0.0.1", port=5006):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.latest = ""
        self.running = True

    def run(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(1024)
                self.latest = data.decode("ascii", errors="ignore").strip()
            except Exception:
                time.sleep(0.05)

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass


class SimGUI:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title("AKINTAY Sim GUI")

        self.listen_port = StringVar(value="5007")
        self.speed = StringVar(value="60")
        self.telemetry = StringVar(value="POSE:")

        top = Frame(root)
        top.pack(padx=8, pady=8)

        Label(top, text="Listen Port").grid(row=0, column=0, sticky="w")
        Entry(top, textvariable=self.listen_port, width=8).grid(row=0, column=1)

        self.btn_start = Button(top, text="Start Sim", command=self.start_sim)
        self.btn_start.grid(row=0, column=2, padx=6)

        self.btn_stop = Button(top, text="Stop Sim", command=self.stop_sim, state="disabled")
        self.btn_stop.grid(row=0, column=3)

        Label(top, text="Speed").grid(row=1, column=0, sticky="w")
        self.sl = Scale(top, from_=0, to=100, orient=HORIZONTAL)
        self.sl.set(60)
        self.sl.grid(row=1, column=1, columnspan=3, sticky="ew")

        btns = Frame(root)
        btns.pack(padx=8, pady=6)

        Button(btns, text="Forward", width=10, command=lambda: self.send_cmd('F')).grid(row=0, column=1)
        Button(btns, text="Left", width=10, command=lambda: self.send_cmd('L')).grid(row=1, column=0)
        Button(btns, text="Stop", width=10, command=lambda: self.send_cmd('S')).grid(row=1, column=1)
        Button(btns, text="Right", width=10, command=lambda: self.send_cmd('R')).grid(row=1, column=2)

        self.lbl_tel = Label(root, textvariable=self.telemetry, anchor="w")
        self.lbl_tel.pack(fill="x", padx=8, pady=6)

        self.proc = None
        self.tel_listener = None
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def start_sim(self):
        try:
            port = int(self.listen_port.get())
        except Exception:
            port = 5007

        # Start simulator process
        self.proc = subprocess.Popen([
            sys.executable, "rov2d.py", "--listen_port", str(port), "--keyboard", "--trail", "--obstacles", "--telemetry"
        ], cwd=str((__file__).rsplit("\\", 1)[0]))

        # Start telemetry
        self.tel_listener = TelemetryListener(port=5006)
        self.tel_listener.start()
        self.root.after(200, self.poll_telemetry)

        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")

    def stop_sim(self):
        if self.proc:
            self.proc.terminate()
            self.proc = None
        if self.tel_listener:
            self.tel_listener.stop()
            self.tel_listener = None
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

    def poll_telemetry(self):
        if self.tel_listener:
            if self.tel_listener.latest:
                self.telemetry.set(self.tel_listener.latest)
            self.root.after(200, self.poll_telemetry)

    def send_cmd(self, c: str):
        try:
            port = int(self.listen_port.get())
        except Exception:
            port = 5007
        spd = int(self.sl.get())
        msg = f"CMD:{c};SPEED:{spd}\n".encode("ascii")
        self.udp.sendto(msg, ("127.0.0.1", port))


def main():
    root = Tk()
    gui = SimGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()


