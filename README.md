# oled-display

A Python daemon that drives a 128×64 SSD1306 OLED over I2C on a Raspberry Pi, rotating through three pages every 5 seconds:

- **System Stats** — CPU %, temperature, RAM, disk, uptime
- **Network** — hostname, LAN IP, Tailscale VPN IP
- **Services** — active/inactive status for configured systemd services

---

## Wiring (SSD1306 → Raspberry Pi 4)

| OLED Pin | Pi Pin | GPIO |
|----------|--------|------|
| VCC | Pin 1 | 3.3 V |
| GND | Pin 6 | GND |
| SDA | Pin 3 | GPIO 2 |
| SCL | Pin 5 | GPIO 3 |

I2C address: `0x3C` on `/dev/i2c-1`

---

## Requirements

```bash
sudo apt install python3-luma.oled python3-pillow python3-psutil
```

Enable I2C if not already on:
```bash
sudo raspi-config  # Interface Options → I2C → Enable
```

---

## Run

**Manually:**
```bash
python3 oled_display.py
```

**As a systemd service:**
```bash
# Edit oled_display.service — update the path in ExecStart to match your username
sudo cp oled_display.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now oled_display
sudo systemctl status oled_display
```

---

## Configuration

Edit the constants at the top of `oled_display.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `I2C_ADDRESS` | `0x3C` | OLED I2C address |
| `PAGE_SECS` | `5` | Seconds per page |
| `UPDATE_HZ` | `10` | Redraws per second |
| `SERVICES` | see file | systemd services to monitor |
