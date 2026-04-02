from __future__ import annotations

import argparse
import json
import logging
import math
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

from serial import Serial
from serial.threaded import LineReader, ReaderThread

try:
    import board
    import busio
    from adafruit_bme280 import basic as adafruit_bme280
except Exception:
    board = None
    busio = None
    adafruit_bme280 = None


@dataclass
class FusedNavSample:
    utc_datetime: Optional[datetime] = None
    fix_valid: bool = False
    fix_quality: Optional[int] = None
    sats: Optional[int] = None
    lat_deg: Optional[float] = None
    lon_deg: Optional[float] = None
    speed_knots: Optional[float] = None
    speed_kmh: Optional[float] = None
    course_deg: Optional[float] = None

    gps_alt_m: Optional[float] = None

    baro_temp_c: Optional[float] = None
    baro_pressure_hpa: Optional[float] = None
    baro_humidity_pct: Optional[float] = None
    baro_alt_rel_m: Optional[float] = None

    fused_alt_m: Optional[float] = None
    climb_rate_mps: Optional[float] = None

    gps_sentence_count: int = 0
    bme_sample_count: int = 0
    last_gps_monotonic_s: Optional[float] = None
    last_bme_monotonic_s: Optional[float] = None


@dataclass
class FusionConfig:
    gps_correction_gain: float = 0.06
    climb_rate_alpha: float = 0.25
    bme_poll_hz: float = 10.0


class GPSFusedProtocol(LineReader):
    TERMINATOR = b"\n"

    def __init__(
        self,
        *,
        enable_bme: bool = True,
        bme_address: int = 0x76,
        fusion: Optional[FusionConfig] = None,
        log_raw_nmea: bool = False,
    ) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._sample = FusedNavSample()
        self._fusion = fusion or FusionConfig()
        self._log_raw_nmea = log_raw_nmea

        self._enable_bme = enable_bme
        self._bme_address = bme_address
        self._bme = None
        self._bme_thread: Optional[threading.Thread] = None

        self._stop_event = threading.Event()

        self._baro_reference_pressure_hpa: Optional[float] = None
        self._baro_to_gps_offset_m: Optional[float] = None
        self._last_fused_time_s: Optional[float] = None

        self._reader = None
        self._serial_port = None

    def connection_made(self, transport) -> None:
        super().connection_made(transport)
        logging.info("GPS serial connected")
        if self._enable_bme:
            self._start_bme()

    def connection_lost(self, exc) -> None:
        self._stop_event.set()
        super().connection_lost(exc)

    def close(self) -> None:
        self._stop_event.set()

        if self._reader is not None:
            try:
                self._reader.close()
            except Exception:
                pass

        if self._serial_port is not None:
            try:
                self._serial_port.close()
            except Exception:
                pass

    def attach_handles(self, *, reader, serial_port) -> None:
        self._reader = reader
        self._serial_port = serial_port

    def handle_line(self, line: str) -> None:
        line = line.strip()
        if not line or not line.startswith("$"):
            return

        if self._log_raw_nmea:
            logging.info("NMEA %s", line)

        if not nmea_checksum_ok(line):
            logging.debug("GPS checksum failed: %s", line)
            return

        body = line[1:line.index("*")]
        fields = body.split(",")
        sentence = fields[0]
        now_s = time.monotonic()

        with self._lock:
            self._sample.gps_sentence_count += 1
            self._sample.last_gps_monotonic_s = now_s

            if sentence in ("GPRMC", "GNRMC"):
                self._handle_rmc(fields)
            elif sentence in ("GPGGA", "GNGGA"):
                self._handle_gga(fields, now_s)

    def snapshot(self) -> FusedNavSample:
        with self._lock:
            return FusedNavSample(**asdict(self._sample))

    def snapshot_dict(self) -> dict:
        with self._lock:
            out = asdict(self._sample)
        if out["utc_datetime"] is not None:
            out["utc_datetime"] = out["utc_datetime"].isoformat()
        return out

    def _handle_rmc(self, fields: list[str]) -> None:
        if len(fields) < 10:
            return

        utc_dt = parse_rmc_datetime(fields[1], fields[9])
        fix_valid = fields[2] == "A"
        lat = parse_lat_lon(fields[3], fields[4])
        lon = parse_lat_lon(fields[5], fields[6])
        speed_knots = parse_float(fields[7])
        course_deg = parse_float(fields[8])

        if utc_dt is not None:
            self._sample.utc_datetime = utc_dt
        self._sample.fix_valid = fix_valid
        if lat is not None:
            self._sample.lat_deg = lat
        if lon is not None:
            self._sample.lon_deg = lon
        if speed_knots is not None:
            self._sample.speed_knots = speed_knots
            self._sample.speed_kmh = speed_knots * 1.852
        if course_deg is not None:
            self._sample.course_deg = course_deg

    def _handle_gga(self, fields: list[str], now_s: float) -> None:
        if len(fields) < 10:
            return

        lat = parse_lat_lon(fields[2], fields[3])
        lon = parse_lat_lon(fields[4], fields[5])
        fix_quality = parse_int(fields[6])
        sats = parse_int(fields[7])
        gps_alt_m = parse_float(fields[9])

        if lat is not None:
            self._sample.lat_deg = lat
        if lon is not None:
            self._sample.lon_deg = lon
        self._sample.fix_quality = fix_quality
        self._sample.sats = sats

        if gps_alt_m is None:
            return

        self._sample.gps_alt_m = gps_alt_m

        gps_good = bool((fix_quality or 0) > 0)
        if not gps_good:
            return

        if self._sample.baro_alt_rel_m is not None:
            if self._baro_to_gps_offset_m is None:
                self._baro_to_gps_offset_m = gps_alt_m - self._sample.baro_alt_rel_m
            else:
                predicted = self._sample.baro_alt_rel_m + self._baro_to_gps_offset_m
                error_m = gps_alt_m - predicted
                self._baro_to_gps_offset_m += self._fusion.gps_correction_gain * error_m

            fused = self._sample.baro_alt_rel_m + self._baro_to_gps_offset_m
            self._update_fused_altitude(fused, now_s)
        else:
            if self._sample.fused_alt_m is None:
                self._update_fused_altitude(gps_alt_m, now_s)
            else:
                corrected = self._sample.fused_alt_m + self._fusion.gps_correction_gain * (gps_alt_m - self._sample.fused_alt_m)
                self._update_fused_altitude(corrected, now_s)

    def _start_bme(self) -> None:
        if adafruit_bme280 is None or board is None or busio is None:
            raise RuntimeError(
                "BME280 support requested, but CircuitPython BME280 dependencies are not available"
            )

        i2c = busio.I2C(board.SCL, board.SDA)
        self._bme = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=self._bme_address)
        self._bme_thread = threading.Thread(target=self._bme_loop, name="bme280", daemon=True)
        self._bme_thread.start()

    def _bme_loop(self) -> None:
        assert self._bme is not None
        poll_period_s = 1.0 / max(self._fusion.bme_poll_hz, 0.5)

        while not self._stop_event.is_set():
            now_s = time.monotonic()
            try:
                temp_c = float(self._bme.temperature)
                pressure_hpa = float(self._bme.pressure)
                humidity_pct = float(self._bme.humidity)
            except Exception as exc:
                logging.warning("BME280 read failed: %s", exc)
                time.sleep(poll_period_s)
                continue

            with self._lock:
                self._sample.bme_sample_count += 1
                self._sample.last_bme_monotonic_s = now_s
                self._sample.baro_temp_c = temp_c
                self._sample.baro_pressure_hpa = pressure_hpa
                self._sample.baro_humidity_pct = humidity_pct

                if self._baro_reference_pressure_hpa is None:
                    self._baro_reference_pressure_hpa = pressure_hpa

                baro_alt_rel_m = pressure_to_altitude_delta_m(
                    pressure_hpa,
                    self._baro_reference_pressure_hpa,
                )
                self._sample.baro_alt_rel_m = baro_alt_rel_m

                if self._baro_to_gps_offset_m is not None:
                    fused = baro_alt_rel_m + self._baro_to_gps_offset_m
                    self._update_fused_altitude(fused, now_s)
                elif self._sample.fused_alt_m is None:
                    self._update_fused_altitude(baro_alt_rel_m, now_s)

            time.sleep(poll_period_s)

    def _update_fused_altitude(self, new_alt_m: Optional[float], now_s: float) -> None:
        if new_alt_m is None:
            return

        prev_alt = self._sample.fused_alt_m
        prev_time = self._last_fused_time_s

        self._sample.fused_alt_m = new_alt_m

        if prev_alt is not None and prev_time is not None and now_s > prev_time:
            inst_rate = (new_alt_m - prev_alt) / (now_s - prev_time)
            if self._sample.climb_rate_mps is None:
                self._sample.climb_rate_mps = inst_rate
            else:
                alpha = self._fusion.climb_rate_alpha
                self._sample.climb_rate_mps = alpha * inst_rate + (1.0 - alpha) * self._sample.climb_rate_mps

        self._last_fused_time_s = now_s


def parse_float(text: str) -> Optional[float]:
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(text: str) -> Optional[int]:
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def nmea_checksum_ok(line: str) -> bool:
    if not line.startswith("$") or "*" not in line:
        return False

    body, checksum_text = line[1:].split("*", 1)
    checksum = 0
    for ch in body:
        checksum ^= ord(ch)

    try:
        expected = int(checksum_text[:2], 16)
    except ValueError:
        return False

    return checksum == expected


def parse_lat_lon(value: str, hemi: str) -> Optional[float]:
    if not value or not hemi:
        return None

    raw = parse_float(value)
    if raw is None:
        return None

    degrees = int(raw / 100.0)
    minutes = raw - (degrees * 100.0)
    coord = degrees + (minutes / 60.0)

    if hemi in ("S", "W"):
        coord = -coord
    elif hemi not in ("N", "E"):
        return None

    return coord


def parse_rmc_datetime(hhmmss: str, ddmmyy: str) -> Optional[datetime]:
    if len(hhmmss) < 6 or len(ddmmyy) != 6:
        return None

    try:
        hour = int(hhmmss[0:2])
        minute = int(hhmmss[2:4])
        second = int(float(hhmmss[4:]))
        day = int(ddmmyy[0:2])
        month = int(ddmmyy[2:4])
        year = 2000 + int(ddmmyy[4:6])
        return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    except ValueError:
        return None


def pressure_to_altitude_delta_m(pressure_hpa: float, reference_pressure_hpa: float) -> float:
    if pressure_hpa <= 0.0 or reference_pressure_hpa <= 0.0:
        return 0.0
    return 44330.0 * (1.0 - math.pow(pressure_hpa / reference_pressure_hpa, 0.1903))


def init(
    gps_port: str = "/dev/ttyACM0",
    gps_baud: int = 57200,
    *,
    enable_bme: bool = True,
    bme_address: int = 0x76,
    gps_correction_gain: float = 0.06,
    climb_rate_alpha: float = 0.25,
    bme_poll_hz: float = 10.0,
    log_raw_nmea: bool = False,
) -> GPSFusedProtocol:
    fusion = FusionConfig(
        gps_correction_gain=gps_correction_gain,
        climb_rate_alpha=climb_rate_alpha,
        bme_poll_hz=bme_poll_hz,
    )

    serial_port = Serial(gps_port, gps_baud, timeout=1)
    reader = ReaderThread(
        serial_port,
        lambda: GPSFusedProtocol(
            enable_bme=enable_bme,
            bme_address=bme_address,
            fusion=fusion,
            log_raw_nmea=log_raw_nmea,
        ),
    )
    reader.start()
    _, protocol = reader.connect()
    protocol.attach_handles(reader=reader, serial_port=serial_port)
    return protocol


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GPS + BME280 fused navigation reader")
    parser.add_argument("--port", default="/dev/ttyACM0", help="GPS serial port")
    parser.add_argument("--baud", type=int, default=57200, help="GPS serial baud rate")
    parser.add_argument("--no-bme", action="store_true", help="Disable BME280 support")
    parser.add_argument("--bme-address", type=lambda x: int(x, 0), default=0x76, help="BME280 I2C address")
    parser.add_argument("--bme-poll-hz", type=float, default=10.0, help="BME280 poll rate")
    parser.add_argument("--gps-correction-gain", type=float, default=0.06, help="GPS correction gain for fused altitude")
    parser.add_argument("--climb-rate-alpha", type=float, default=0.25, help="Low-pass filter alpha for climb rate")
    parser.add_argument("--interval", type=float, default=1.0, help="Print interval in seconds")
    parser.add_argument("--duration", type=float, default=0.0, help="Optional run duration in seconds; 0 means forever")
    parser.add_argument("--json", action="store_true", help="Print snapshots as JSON")
    parser.add_argument("--raw-nmea", action="store_true", help="Log raw NMEA lines")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level",
    )
    return parser


def cli_main(argv: Optional[list[str]] = None) -> int:
    parser = build_argparser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    nav = init(
        gps_port=args.port,
        gps_baud=args.baud,
        enable_bme=not args.no_bme,
        bme_address=args.bme_address,
        gps_correction_gain=args.gps_correction_gain,
        climb_rate_alpha=args.climb_rate_alpha,
        bme_poll_hz=args.bme_poll_hz,
        log_raw_nmea=args.raw_nmea,
    )

    start = time.monotonic()
    try:
        while True:
            sample = nav.snapshot_dict()

            if args.json:
                print(json.dumps(sample, sort_keys=True))
            else:
                print(
                    f"utc={sample.get('utc_datetime')} "
                    f"fix_valid={sample.get('fix_valid')} "
                    f"fixq={sample.get('fix_quality')} sats={sample.get('sats')} "
                    f"lat={sample.get('lat_deg')} lon={sample.get('lon_deg')} "
                    f"spd_kmh={sample.get('speed_kmh')} gps_alt={sample.get('gps_alt_m')} "
                    f"baro_rel={sample.get('baro_alt_rel_m')} fused_alt={sample.get('fused_alt_m')} "
                    f"climb_mps={sample.get('climb_rate_mps')} "
                    f"P={sample.get('baro_pressure_hpa')} T={sample.get('baro_temp_c')}"
                )

            if args.duration > 0.0 and (time.monotonic() - start) >= args.duration:
                break

            time.sleep(max(args.interval, 0.05))
    except KeyboardInterrupt:
        pass
    finally:
        nav.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
