"""Omron 2JCIE-BU01 USB environmental sensor communication module.

Uses USB serial via ftdi_sio kernel module at 115200 baud.
Setup:
    sudo modprobe ftdi_sio
    sudo sh -c 'echo 0590 00d4 > /sys/bus/usb-serial/drivers/ftdi_sio/new_id'
"""

import struct
import time
import random
import logging

logger = logging.getLogger(__name__)


def _calc_crc(data):
    """Calculate CRC-16 and return as 2-byte little-endian bytearray."""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            carry = crc & 1
            crc >>= 1
            if carry:
                crc ^= 0xA001
    return bytearray([crc & 0xFF, crc >> 8])


def _build_read_command():
    """Build the binary frame to request Latest Data Long (address 0x5021)."""
    # Frame: Header(2) + Length(2) + Mode(1) + Address(2) + CRC(2)
    frame = bytearray([0x52, 0x42, 0x05, 0x00, 0x01, 0x21, 0x50])
    return frame + _calc_crc(frame)


def _parse_response(data):
    """Parse the sensor response into a dict of readings.

    Response layout (58 bytes for Latest Data Long):
      [0-1]  Header 0x52 0x42
      [2-3]  Length (LE)
      [4]    Response type (0x01)
      [5-6]  Address (LE)
      [7]    Sequence / padding byte
      [8-9]  Temperature (signed, x0.01 degC)
      [10-11] Humidity (x0.01 %)
      [12-13] Ambient Light (lx)
      [14-17] Barometric Pressure (x0.001 hPa)
      [18-19] Sound Noise (x0.01 dB)
      [20-21] eTVOC (ppb)
      [22-23] eCO2 (ppm)
      [24-25] Discomfort Index (x0.01)
      [26-27] Heat Stroke (signed, x0.01 degC)
    """
    if len(data) < 30:
        raise ValueError(f"Response too short: {len(data)} bytes")

    if data[0] != 0x52 or data[1] != 0x42:
        raise ValueError(f"Invalid header: {data[:2].hex()}")

    offset = 8  # Sensor data starts at byte 8

    temperature = struct.unpack_from('<h', data, offset)[0] * 0.01
    offset += 2
    humidity = struct.unpack_from('<H', data, offset)[0] * 0.01
    offset += 2
    light = struct.unpack_from('<H', data, offset)[0]
    offset += 2
    pressure = struct.unpack_from('<I', data, offset)[0] * 0.001
    offset += 4
    noise = struct.unpack_from('<H', data, offset)[0] * 0.01
    offset += 2
    etvoc = struct.unpack_from('<H', data, offset)[0]
    offset += 2
    eco2 = struct.unpack_from('<H', data, offset)[0]
    offset += 2
    discomfort = struct.unpack_from('<H', data, offset)[0] * 0.01
    offset += 2
    heat_stroke = struct.unpack_from('<h', data, offset)[0] * 0.01

    return {
        'temperature': round(temperature, 2),
        'humidity': round(humidity, 2),
        'light': light,
        'pressure': round(pressure, 3),
        'noise': round(noise, 2),
        'etvoc': etvoc,
        'eco2': eco2,
        'discomfort': round(discomfort, 2),
        'heat_stroke': round(heat_stroke, 2),
    }


class Sensor:
    """Interface to the Omron 2JCIE-BU01 USB sensor via serial."""

    def __init__(self, port='/dev/ttyUSB0', mock=False):
        self.port = port
        self.mock = mock
        self._serial = None

    def open(self):
        if self.mock:
            logger.info("Sensor running in mock mode")
            return
        import serial
        self._serial = serial.Serial(
            port=self.port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
        )
        logger.info("Sensor opened on %s", self.port)

    def close(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
            logger.info("Sensor closed")

    def read(self):
        """Read the latest sensor data. Returns a dict or None on error."""
        if self.mock:
            return self._mock_read()
        return self._real_read()

    def _real_read(self):
        try:
            self._serial.reset_input_buffer()
            cmd = _build_read_command()
            self._serial.write(cmd)
            time.sleep(0.1)

            data = self._serial.read(self._serial.in_waiting or 64)
            if len(data) < 30:
                # Retry once — sometimes the first read is short
                time.sleep(0.05)
                data += self._serial.read(self._serial.in_waiting or 64)

            if len(data) < 30:
                logger.warning("Short response: %d bytes", len(data))
                return None

            return _parse_response(data)
        except Exception:
            logger.exception("Error reading sensor")
            return None

    def _mock_read(self):
        t = time.time()
        return {
            'temperature': round(22.0 + 3.0 * _smooth_noise(t, 0.001), 2),
            'humidity': round(50.0 + 15.0 * _smooth_noise(t, 0.0007), 2),
            'light': max(0, int(300 + 200 * _smooth_noise(t, 0.0005))),
            'pressure': round(1013.25 + 5.0 * _smooth_noise(t, 0.0003), 3),
            'noise': round(40.0 + 10.0 * _smooth_noise(t, 0.002), 2),
            'etvoc': max(0, int(50 + 80 * _smooth_noise(t, 0.0008))),
            'eco2': max(400, int(600 + 300 * _smooth_noise(t, 0.0006))),
            'discomfort': round(70.0 + 5.0 * _smooth_noise(t, 0.001), 2),
            'heat_stroke': round(22.0 + 3.0 * _smooth_noise(t, 0.0009), 2),
        }


def _smooth_noise(t, freq):
    """Generate smooth pseudo-random noise using sine waves."""
    return (
        0.5 * __import__('math').sin(t * freq * 6.283)
        + 0.3 * __import__('math').sin(t * freq * 2.1 * 6.283 + 1.3)
        + 0.2 * random.gauss(0, 0.1)
    )
