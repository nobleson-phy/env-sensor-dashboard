"""Flask application for the Omron 2JCIE-BU01 sensor dashboard."""

import argparse
import threading
import time
import logging

from flask import Flask, jsonify, render_template, request

from sensor import Sensor
from database import init_db, insert_reading, get_latest, get_history

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# In-memory cache for the latest reading (avoids DB hit on every poll)
_latest_lock = threading.Lock()
_latest_reading = None


def sensor_loop(sensor, interval=3):
    """Background thread: read sensor and store in DB."""
    global _latest_reading
    while True:
        data = sensor.read()
        if data:
            with _latest_lock:
                _latest_reading = data
            try:
                insert_reading(data)
            except Exception:
                logger.exception("Failed to insert reading")
        time.sleep(interval)


# ── Routes ──────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/api/latest')
def api_latest():
    with _latest_lock:
        data = _latest_reading
    if data is None:
        data = get_latest()
    if data is None:
        return jsonify({'error': 'No data available'}), 503
    return jsonify(data)


@app.route('/api/history')
def api_history():
    hours = request.args.get('hours', 24, type=int)
    hours = max(1, min(hours, 168))  # clamp 1h – 7d
    rows = get_history(hours)
    return jsonify(rows)


# ── Main ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='2JCIE-BU01 Sensor Dashboard')
    parser.add_argument('--mock', action='store_true', help='Use simulated sensor data')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port (default: /dev/ttyUSB0)')
    parser.add_argument('--host', default='0.0.0.0', help='Listen address (default: 0.0.0.0)')
    parser.add_argument('--flask-port', default=5000, type=int, help='HTTP port (default: 5000)')
    args = parser.parse_args()

    init_db()

    sensor = Sensor(port=args.port, mock=args.mock)
    sensor.open()

    t = threading.Thread(target=sensor_loop, args=(sensor,), daemon=True)
    t.start()
    logger.info("Sensor thread started (mock=%s)", args.mock)

    app.run(host=args.host, port=args.flask_port, debug=False)


if __name__ == '__main__':
    main()
