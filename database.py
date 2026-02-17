"""SQLite storage for sensor readings."""

import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sensor_data.db')
PRUNE_DAYS = 7


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the readings table if it doesn't exist."""
    with _connect() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                temperature REAL,
                humidity REAL,
                light INTEGER,
                pressure REAL,
                noise REAL,
                etvoc INTEGER,
                eco2 INTEGER,
                discomfort REAL,
                heat_stroke REAL
            )
        ''')
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_readings_timestamp
            ON readings(timestamp)
        ''')
    logger.info("Database initialized at %s", DB_PATH)


def insert_reading(data):
    """Insert a sensor reading dict and prune old records."""
    with _connect() as conn:
        conn.execute(
            '''INSERT INTO readings
               (temperature, humidity, light, pressure, noise, etvoc, eco2, discomfort, heat_stroke)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                data['temperature'], data['humidity'], data['light'],
                data['pressure'], data['noise'], data['etvoc'],
                data['eco2'], data['discomfort'], data['heat_stroke'],
            )
        )
        # Auto-prune old data
        conn.execute(
            "DELETE FROM readings WHERE timestamp < datetime('now', ?)",
            (f'-{PRUNE_DAYS} days',)
        )


def get_latest():
    """Return the most recent reading as a dict, or None."""
    with _connect() as conn:
        row = conn.execute(
            'SELECT * FROM readings ORDER BY id DESC LIMIT 1'
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def get_history(hours=24):
    """Return readings from the last N hours as a list of dicts."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM readings WHERE timestamp >= datetime('now', ?) ORDER BY timestamp ASC",
            (f'-{hours} hours',)
        ).fetchall()
    return [dict(r) for r in rows]
