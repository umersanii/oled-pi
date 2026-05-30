#!/usr/bin/env python3
"""
OLED system display daemon for Raspberry Pi 4.
Rotates through three info pages on a 128x64 SSD1306 over I2C.

Run:  python3 oled_display.py
Service: sudo systemctl start oled-display
"""

import signal
import socket
import subprocess
import sys
import time

import psutil
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306

# ── Config ────────────────────────────────────────────────────────────────────
I2C_PORT    = 1
I2C_ADDRESS = 0x3C
PAGE_SECS   = 5      # seconds each page is shown
UPDATE_HZ   = 10     # redraws per second while a page is shown

SERVICES = [
    ("BadComp", "badcomputer"),
    ("NPM",     "nginx-proxy-manager"),
    ("Docker",  "docker"),
]

# ── Device setup ─────────────────────────────────────────────────────────────
def make_device():
    serial = i2c(port=I2C_PORT, address=I2C_ADDRESS)
    return ssd1306(serial, width=128, height=64)


# ── Data helpers ──────────────────────────────────────────────────────────────
def cpu_percent():
    return psutil.cpu_percent(interval=None)

def cpu_temp():
    try:
        t = psutil.sensors_temperatures()
        for key in ("cpu_thermal", "coretemp", "soc_thermal"):
            if key in t:
                return t[key][0].current
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return float(f.read()) / 1000
    except Exception:
        return 0.0

def ram():
    m = psutil.virtual_memory()
    return m.percent, m.used / 1e9, m.total / 1e9   # %, GB used, GB total

def disk():
    d = psutil.disk_usage("/")
    return d.percent, d.free / 1e9, d.total / 1e9   # %, GB free, GB total

def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "?.?.?.?"

def tailscale_ip():
    try:
        return subprocess.check_output(
            ["tailscale", "ip", "-4"], text=True, timeout=2
        ).strip()
    except Exception:
        return "not connected"

def service_status(name):
    try:
        r = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True, text=True, timeout=2
        )
        return r.stdout.strip()
    except Exception:
        return "unknown"

def uptime():
    secs = int(time.monotonic())
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    if d:
        return f"{d}d {h}h {m}m"
    return f"{h}h {m}m"


# ── Pages ─────────────────────────────────────────────────────────────────────
def draw_header(draw, title):
    """Top bar with title and time."""
    now = time.strftime("%H:%M:%S")
    draw.rectangle([0, 0, 127, 11], fill="white")
    draw.text((2, 1), title, fill="black")
    draw.text((128 - len(now) * 6 - 2, 1), now, fill="black")


def page_stats(draw):
    cpu = cpu_percent()
    temp = cpu_temp()
    rp, ru, rt = ram()
    dp, df, dt = disk()

    draw_header(draw, "System Stats")
    draw.text((0, 14), f"CPU:  {cpu:5.1f}%   {temp:.1f}C", fill="white")
    draw.text((0, 26), f"RAM:  {rp:5.1f}%  {ru:.1f}/{rt:.1f}G", fill="white")
    draw.text((0, 38), f"Disk: {dp:5.1f}%  {df:.0f}G free", fill="white")
    draw.text((0, 50), f"Up: {uptime()}", fill="white")


def page_network(draw):
    lip  = local_ip()
    tsip = tailscale_ip()
    host = socket.gethostname()

    draw_header(draw, "Network")
    draw.text((0, 14), f"Host: {host}",  fill="white")
    draw.text((0, 26), f"LAN:  {lip}",   fill="white")
    draw.text((0, 38), f"VPN:  {tsip}",  fill="white")


def page_services(draw):
    draw_header(draw, "Services")
    y = 14
    for label, svc in SERVICES:
        status = service_status(svc)
        dot = "+" if status == "active" else "-"
        draw.text((0, y), f"[{dot}] {label}: {status}", fill="white")
        y += 12


PAGES = [page_stats, page_network, page_services]


# ── Main loop ─────────────────────────────────────────────────────────────────
class Runner:
    def __init__(self):
        self.running = True
        signal.signal(signal.SIGTERM, self._stop)
        signal.signal(signal.SIGINT,  self._stop)

    def _stop(self, *_):
        self.running = False

    def run(self):
        device = make_device()
        page_idx = 0
        page_start = time.monotonic()
        interval = 1.0 / UPDATE_HZ

        # prime cpu_percent (first call always returns 0.0)
        psutil.cpu_percent(interval=None)

        print(f"oled-display running — {len(PAGES)} pages, {PAGE_SECS}s each")

        while self.running:
            tick = time.monotonic()

            if tick - page_start >= PAGE_SECS:
                page_idx = (page_idx + 1) % len(PAGES)
                page_start = tick

            with canvas(device) as draw:
                PAGES[page_idx](draw)

            elapsed = time.monotonic() - tick
            sleep = max(0.0, interval - elapsed)
            time.sleep(sleep)

        # blank on exit
        with canvas(device) as draw:
            draw.rectangle([0, 0, 127, 63], fill="black")

        print("oled-display stopped")


if __name__ == "__main__":
    Runner().run()
