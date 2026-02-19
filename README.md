# Omron 2JCIE-BU01 Environment Sensor Dashboard

A real-time web dashboard for the [Omron 2JCIE-BU01](https://components.omron.com/eu-en/products/sensors/2JCIE-BU) USB environmental sensor, designed to run on a Raspberry Pi.

## What It Measures

| Metric | Unit | Description |
|---|---|---|
| Temperature | °C | Ambient temperature |
| Humidity | % | Relative humidity |
| Ambient Light | lx | Light intensity |
| Barometric Pressure | hPa | Atmospheric pressure |
| Sound Noise | dB | Sound pressure level |
| eTVOC | ppb | Estimated total volatile organic compounds |
| eCO2 | ppm | Estimated CO2 concentration |
| Discomfort Index | - | Thermal comfort indicator |
| Heat Stroke Risk | °C | WBGT-based heat stroke risk |

## Features

- **Live sensor cards** with color-coded thresholds (green/yellow/orange/red)
- **Historical charts** using Chart.js — temperature & humidity, air quality, pressure, sound & light
- **Selectable time range** — 1 hour to 7 days
- **Auto-pruning** SQLite storage — keeps 7 days of data
- **Auto-recovery** from sensor firmware freezes via USB reset
- **Mock mode** for development without the physical sensor
- **Dark theme** responsive layout

## Stack

- **Backend:** Python 3, Flask, SQLite
- **Frontend:** Chart.js, vanilla JavaScript
- **Sensor communication:** pyserial over ftdi_sio USB driver
- **Updates:** AJAX polling (cards every 5s, charts every 60s)

## Quick Start

```bash
# Install dependencies
pip3 install -r requirements.txt

# Set up USB driver (one-time, see HOWTO.md for permanent setup)
sudo modprobe ftdi_sio
sudo sh -c 'echo 0590 00d4 > /sys/bus/usb-serial/drivers/ftdi_sio/new_id'

# Run with real sensor
sudo python3 app.py

# Or run with simulated data
python3 app.py --mock
```

Open `http://<pi-ip>:5000` in a browser.

## Project Structure

```
├── app.py              # Flask app, API routes, background sensor thread
├── sensor.py           # 2JCIE-BU01 serial protocol (CRC-16, frame parsing)
├── database.py         # SQLite schema, read/write, auto-prune
├── requirements.txt    # pyserial, flask
├── HOWTO.md            # Detailed installation and setup guide
├── templates/
│   └── dashboard.html  # Single-page dashboard
└── static/
    ├── css/style.css   # Dark theme, card grid, chart layout
    └── js/dashboard.js # Polling, Chart.js rendering, threshold colors
```

## API

| Endpoint | Description |
|---|---|
| `GET /` | Dashboard page |
| `GET /api/latest` | Latest sensor reading as JSON |
| `GET /api/history?hours=24` | Historical readings (1–168 hours) |

## Sensor Auto-Recovery

The 2JCIE-BU01 firmware can occasionally freeze, returning identical readings. The dashboard detects this after 10 consecutive identical reads (~30s) and uses [`uhubctl`](https://github.com/mvp/uhubctl) to cut USB port power — fully resetting the sensor hardware, equivalent to a physical unplug/replug. Requires `sudo apt install uhubctl` and running as root. See [HOWTO.md](HOWTO.md) for details.

## Documentation

See [HOWTO.md](HOWTO.md) for detailed instructions on USB driver setup, installation, running as a systemd service, and troubleshooting.

## License

MIT
