# Omron 2JCIE-BU01 Environment Sensor Dashboard

How to install and run the web dashboard on a Raspberry Pi.

## Prerequisites

- Raspberry Pi (tested on Pi 4) running Raspberry Pi OS
- Omron 2JCIE-BU01 USB environmental sensor
- Python 3.7+
- `uhubctl` for automatic sensor recovery (install: `sudo apt install uhubctl`)
- Network access to the Pi (for viewing the dashboard)

## 1. USB Driver Setup

The 2JCIE-BU01 uses a vendor-specific USB interface that requires the `ftdi_sio` kernel module with the Omron device IDs registered.

### One-time setup (temporary, lost on reboot)

```bash
sudo modprobe ftdi_sio
sudo sh -c 'echo 0590 00d4 > /sys/bus/usb-serial/drivers/ftdi_sio/new_id'
```

Verify the sensor appears as a serial device:

```bash
ls /dev/ttyUSB*
# Should show: /dev/ttyUSB0
```

### Permanent setup (survives reboot)

Create a udev rule so the driver loads automatically when the sensor is plugged in:

```bash
sudo tee /etc/udev/rules.d/80-2jcie-bu01.rules << 'EOF'
ACTION=="add", ATTRS{idVendor}=="0590", ATTRS{idProduct}=="00d4", RUN+="/sbin/modprobe ftdi_sio", RUN+="/bin/sh -c 'echo 0590 00d4 > /sys/bus/usb-serial/drivers/ftdi_sio/new_id'"
EOF

sudo udevadm control --reload-rules
```

Unplug and replug the sensor to test. `/dev/ttyUSB0` should appear automatically.

## 2. Install the Dashboard

Copy the project files to the Pi (or clone from your repository):

```bash
cd ~
mkdir -p env.sensor/templates env.sensor/static/css env.sensor/static/js
```

The project structure should be:

```
env.sensor/
├── app.py
├── sensor.py
├── database.py
├── requirements.txt
├── templates/
│   └── dashboard.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── dashboard.js
```

Install Python dependencies:

```bash
cd ~/env.sensor
pip3 install -r requirements.txt
```

## 3. Run the Dashboard

### With the real sensor

Plug in the 2JCIE-BU01 and confirm `/dev/ttyUSB0` exists, then:

```bash
sudo python3 app.py
```

`sudo` is required to access the serial device. If your user is in the `dialout` group, you can run without sudo:

```bash
sudo usermod -aG dialout $USER
# Log out and back in, then:
python3 app.py
```

### With simulated data (no sensor needed)

For development or testing without the physical sensor:

```bash
python3 app.py --mock
```

### Command-line options

| Option | Default | Description |
|---|---|---|
| `--mock` | off | Use simulated sensor data |
| `--port` | `/dev/ttyUSB0` | Serial port for the sensor |
| `--host` | `0.0.0.0` | Listen address |
| `--flask-port` | `5000` | HTTP port |

## 4. Open the Dashboard

From any device on the same network, open a browser and go to:

```
http://<pi-ip-address>:5000
```

To find your Pi's IP address:

```bash
hostname -I
```

The dashboard shows:
- **Live cards** updating every 5 seconds: temperature, humidity, pressure, light, noise, eCO2, eTVOC, discomfort index, heat stroke risk
- **Historical charts** updating every 60 seconds: temperature/humidity, air quality, pressure, noise/light
- **History range selector**: 1 hour, 6 hours, 24 hours, 3 days, or 7 days

## 5. Run as a System Service (Optional)

To start the dashboard automatically on boot:

```bash
sudo tee /etc/systemd/system/sensor-dashboard.service << EOF
[Unit]
Description=Environment Sensor Dashboard
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/env.sensor/app.py
WorkingDirectory=/home/pi/env.sensor
User=root
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable sensor-dashboard
sudo systemctl start sensor-dashboard
```

Check status:

```bash
sudo systemctl status sensor-dashboard
```

View logs:

```bash
sudo journalctl -u sensor-dashboard -f
```

## Sensor Stale Detection and Auto-Recovery

The 2JCIE-BU01 firmware can occasionally freeze, causing it to return identical readings indefinitely while the USB connection remains active. The dashboard detects and recovers from this automatically:

1. The sensor module tracks consecutive identical readings
2. After **10 identical reads** (~30 seconds), it triggers an automatic recovery
3. Recovery uses `uhubctl` to cut USB port power for 3 seconds (equivalent to physically unplugging the sensor), then restores power, re-registers the `ftdi_sio` driver, and waits for `/dev/ttyUSB*` to reappear
4. A warning is logged: `Sensor stale (10 identical reads), resetting USB`

### Why uhubctl?

A simple USB unbind/rebind only resets the USB interface, not the sensor's internal microcontroller. The firmware stays frozen. `uhubctl` cuts electrical power to the USB port, fully resetting the sensor hardware — the same as physically unplugging and replugging the cable.

### Install uhubctl

```bash
sudo apt install uhubctl
```

Verify it can see your USB hub:

```bash
sudo uhubctl
```

This requires the app to run as **root** so it can control USB power. If running as a systemd service with `User=root`, this works out of the box.

If auto-recovery fails (e.g. `uhubctl` not installed or USB hub doesn't support per-port power switching), a physical unplug/replug of the sensor will always resolve the issue.

## Troubleshooting

### `/dev/ttyUSB0` does not appear

1. Check the sensor is plugged in: `lsusb | grep Omron`
2. Load the driver manually: `sudo modprobe ftdi_sio && sudo sh -c 'echo 0590 00d4 > /sys/bus/usb-serial/drivers/ftdi_sio/new_id'`
3. Check kernel messages: `dmesg | tail`

### "No data available" on the dashboard

The sensor thread needs a few seconds to get its first reading. Refresh the page after 5 seconds. If it persists, check that `/dev/ttyUSB0` exists and is accessible.

### Permission denied on `/dev/ttyUSB0`

Either run with `sudo` or add your user to the `dialout` group:

```bash
sudo usermod -aG dialout $USER
```

Log out and back in for the group change to take effect.

### Dashboard not reachable from other devices

- Confirm the Pi's firewall allows port 5000: `sudo ufw allow 5000/tcp`
- Verify the app is listening on `0.0.0.0` (the default), not `127.0.0.1`
