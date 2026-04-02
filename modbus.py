#!/usr/bin/env python3

import argparse
import struct
import sys
import time
from typing import List

import serial


# ----------------------------
# User-adjustable settings
# ----------------------------

VOLTAGE_SLAVE_ID = 0x02
VOLTAGE_FUNCTION = 0x04
VOLTAGE_START_ADDR = 0x0000
VOLTAGE_NUM_REGS = 8

TEMP_SLAVE_ID = 0x01
TEMP_FUNCTION = 0x03
TEMP_START_ADDR = 0x0000
TEMP_NUM_REGS = 8

# Assumption for the 0-10 V module:
# raw value 10000 => 10.000 V
# so volts = raw / 1000.0
#
# If you later observe, for example, that 5.000 V reads as 5000 raw,
# this is correct. If not, change this constant.
VOLTAGE_COUNTS_PER_VOLT = 2002.5

# From your measured data:
# 0x00DD = 221 => 22.1 °C
# 0x3584 = 13700 => 1370.0 °C
TEMP_COUNTS_PER_DEGC = 10.0


# ----------------------------
# Modbus helpers
# ----------------------------

def modbus_crc16(data: bytes) -> int:
    """
    Compute Modbus RTU CRC16.
    Returned integer is the CRC value before little-endian packing.
    """
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def build_read_request(slave_id: int, function: int, start_addr: int, quantity: int) -> bytes:
    """
    Build a Modbus RTU read request for function 0x03 or 0x04.
    """
    pdu = struct.pack(">BBHH", slave_id, function, start_addr, quantity)
    crc = modbus_crc16(pdu)
    return pdu + struct.pack("<H", crc)


def read_registers(
    ser: serial.Serial,
    slave_id: int,
    function: int,
    start_addr: int,
    quantity: int,
) -> List[int]:
    """
    Send one Modbus RTU request and return a list of 16-bit register values.
    Raises RuntimeError on CRC, exception, timeout, or framing errors.
    """
    request = build_read_request(slave_id, function, start_addr, quantity)

    ser.reset_input_buffer()
    ser.write(request)
    ser.flush()

    # Expected normal response:
    # slave(1) + func(1) + bytecount(1) + data(2*quantity) + crc(2)
    expected_len = 3 + (2 * quantity) + 2
    response = ser.read(expected_len)

    if len(response) != expected_len:
        raise RuntimeError(
            f"Short response from slave {slave_id}: got {len(response)} bytes, expected {expected_len}"
        )

    # CRC check
    body = response[:-2]
    rx_crc = struct.unpack("<H", response[-2:])[0]
    calc_crc = modbus_crc16(body)
    if rx_crc != calc_crc:
        raise RuntimeError(
            f"CRC mismatch from slave {slave_id}: rx=0x{rx_crc:04X}, calc=0x{calc_crc:04X}"
        )

    rx_slave = response[0]
    rx_func = response[1]

    if rx_slave != slave_id:
        raise RuntimeError(f"Unexpected slave id: got {rx_slave}, expected {slave_id}")

    # Modbus exception
    if rx_func & 0x80:
        exc_code = response[2]
        raise RuntimeError(f"Modbus exception from slave {slave_id}: function=0x{rx_func:02X}, code=0x{exc_code:02X}")

    if rx_func != function:
        raise RuntimeError(f"Unexpected function: got 0x{rx_func:02X}, expected 0x{function:02X}")

    byte_count = response[2]
    expected_byte_count = 2 * quantity
    if byte_count != expected_byte_count:
        raise RuntimeError(
            f"Unexpected byte count from slave {slave_id}: got {byte_count}, expected {expected_byte_count}"
        )

    data = response[3:3 + byte_count]
    regs = list(struct.unpack(">" + ("H" * quantity), data))
    return regs


# ----------------------------
# Conversion helpers
# ----------------------------

def raw_to_volts(raw: int) -> float:
    """
    Convert raw register to volts.
    Default assumption: raw is millivolts for a 0-10 V range.
    """
    return raw / VOLTAGE_COUNTS_PER_VOLT


def raw_to_degc(raw: int) -> float:
    """
    Convert raw register to degrees C.
    Your observed mapping shows 0.1 °C per count.
    """
    return raw / TEMP_COUNTS_PER_DEGC


# ----------------------------
# Display
# ----------------------------

def format_hex_list(values: List[int]) -> str:
    return " ".join(f"{v:04X}" for v in values)


def print_snapshot(voltage_regs: List[int], temp_regs: List[int], timestamp: str) -> None:
    voltage_vals = [raw_to_volts(v) for v in voltage_regs]
    temp_vals = [raw_to_degc(t) for t in temp_regs]

    print(f"\n{timestamp}")
    print("Voltage ADC (slave 0x02, func 0x04)")
    for i, (raw, val) in enumerate(zip(voltage_regs, voltage_vals), start=1):
        print(f"  V{i}: raw=0x{raw:04X}  {raw:5d}  {val:7.3f} V")

    print("Thermocouple ADC (slave 0x01, func 0x03)")
    for i, (raw, val) in enumerate(zip(temp_regs, temp_vals), start=1):
        print(f"  T{i}: raw=0x{raw:04X}  {raw:5d}  {val:7.1f} °C")


# ----------------------------
# Main
# ----------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Poll two Modbus RTU devices and display 0-10V + 0-1370C inputs in real time.")
    parser.add_argument("--port", required=True, help="Serial port, e.g. /dev/ttyUSB0 or COM3")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate")
    parser.add_argument("--bytesize", type=int, default=8, choices=[5, 6, 7, 8], help="Data bits")
    parser.add_argument("--parity", default="N", choices=["N", "E", "O"], help="Parity")
    parser.add_argument("--stopbits", type=int, default=1, choices=[1, 2], help="Stop bits")
    parser.add_argument("--timeout", type=float, default=0.2, help="Serial timeout in seconds")
    parser.add_argument("--interval", type=float, default=0.5, help="Poll interval in seconds")
    args = parser.parse_args()

    try:
        with serial.Serial(
            port=args.port,
            baudrate=args.baud,
            bytesize=args.bytesize,
            parity=args.parity,
            stopbits=args.stopbits,
            timeout=args.timeout,
        ) as ser:
            print(f"Opened {args.port} @ {args.baud},{args.bytesize}{args.parity}{args.stopbits}")
            print(f"Voltage scale assumption: {VOLTAGE_COUNTS_PER_VOLT:.1f} counts/V")
            print("Press Ctrl+C to stop.")

            while True:
                try:
                    voltage_regs = read_registers(
                        ser,
                        slave_id=VOLTAGE_SLAVE_ID,
                        function=VOLTAGE_FUNCTION,
                        start_addr=VOLTAGE_START_ADDR,
                        quantity=VOLTAGE_NUM_REGS,
                    )

                    temp_regs = read_registers(
                        ser,
                        slave_id=TEMP_SLAVE_ID,
                        function=TEMP_FUNCTION,
                        start_addr=TEMP_START_ADDR,
                        quantity=TEMP_NUM_REGS,
                    )

                    ts = time.strftime("%Y-%m-%d %H:%M:%S")
                    print_snapshot(voltage_regs, temp_regs, ts)

                except RuntimeError as e:
                    ts = time.strftime("%Y-%m-%d %H:%M:%S")
                    print(f"\n{ts}  ERROR: {e}", file=sys.stderr)

                time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())