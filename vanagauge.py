import datetime as dt
import logging
import time
import os
import csv
from collections import deque

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.ticker as ticker
from matplotlib.widgets import Button
import numpy as np

import techedge
import gps_fused

# IAT sensor table, ohms resistance starting at -40degC and up to 140degC
IAT_Temp_Table = [45313, 26114, 15462, 9397, 5896, 3792, 2500, 1707, 1175, 834, 596, 436, 323, 243, 187, 144, 113, 89, 71]
#                   -40     -30     -20 -10   0     10    20    30

PST_TZ = dt.timezone(dt.timedelta(hours=-7), name="PST")

# Navigation quieting parameters
NAV_GOOD_FIX_MIN_SATS = 5
NAV_GOOD_FIX_REQUIRED = 3
STATIONARY_SPEED_KPH = 1.0
STATIONARY_SAMPLES_REQUIRED = 8     # ~2 s at 250 ms update
ALT_ALPHA_MOVING = 0.20
ALT_ALPHA_STATIONARY = 0.05
CLIMB_WINDOW_S = 3.0
CLIMB_DEADBAND_MPS = 0.05

nav_good_fix_count = 0
nav_ready = False
stationary_sample_count = 0
filtered_alt_m = None
climb_history = deque()

pending_event = "0"

# Create figure for plotting
plt.rcParams['toolbar'] = 'None'
plt.style.use('dark_background')
fig = plt.figure()
fig.canvas.manager.set_window_title("VanPlot")
fig.canvas.manager.full_screen_toggle()

button_ax_coast = fig.add_axes([0.00, 0.8, 0.15, 0.18])  # left, bottom, width, height
coast_button = Button(button_ax_coast, 'COAST\nDOWN', color='green', hovercolor='green')
coast_button.label.set_fontsize(20)

button_ax_hill = fig.add_axes([0.00, 0.6, 0.15, 0.18])  # left, bottom, width, height
hill_button = Button(button_ax_hill, 'HILL\nCLIMB', color='orange', hovercolor='orange')
hill_button.label.set_fontsize(20)

button_ax_weird = fig.add_axes([0.00, 0.4, 0.15, 0.18])  # left, bottom, width, height
weird_button = Button(button_ax_weird, 'WEIRD\nEVENT', color='blue', hovercolor='blue')
weird_button.label.set_fontsize(20)

button_ax_setting_change = fig.add_axes([0.00, 0.2, 0.15, 0.18])  # left, bottom, width, height
setting_change_button = Button(button_ax_setting_change, 'SETTING\nCHANGE', color='purple', hovercolor='purple')
setting_change_button.label.set_fontsize(20)

ax = fig.add_subplot(1, 1, 1)

# layout of chart:
# |
# |
# |
# |
# |
# OIL P   RPM        MAP        Lambda
# OIL T   Air T      MAT        EGT
# GPS lat_deg, lon_deg, speed_kmh, fused_alt_m, climb_rate_mps

ADC1readOut = plt.figtext(0, 0.1, '0', color='purple', fontsize='xx-large')   # OILP
ADC2readOut = plt.figtext(0.5, 0.1, '0', color='green', fontsize='xx-large')  # MAP
ADC3readOut = plt.figtext(0.5, 0.05, '0', color='blue', fontsize='xx-large')  # MAT

TC1readOut = plt.figtext(0.75, 0.05, '0', color='yellow', fontsize='xx-large')  # EGT
TC2readOut = plt.figtext(0, 0.05, '0', color='orange', fontsize='xx-large')     # OIL T
TC3readOut = plt.figtext(0.25, 0.05, '0', color='red', fontsize='xx-large')     # Air T

lambdaReadout = plt.figtext(0.75, 0.1, '0', color='red', fontsize='xx-large')
rpmReadout = plt.figtext(0.25, 0.1, '0', color='pink', fontsize='xx-large')

GPSlatitudeReadout = plt.figtext(0, 0, '0', color='cyan', fontsize='x-large')
GPSlongitudeReadout = plt.figtext(0.2, 0, '0', color='cyan', fontsize='x-large')
GPSspeedReadout = plt.figtext(0.4, 0, '0', color='cyan', fontsize='x-large')
GPSaltitudeReadout = plt.figtext(0.6, 0, '0', color='cyan', fontsize='x-large')
GPSclimbRateReadout = plt.figtext(0.8, 0, '0', color='cyan', fontsize='x-large')

capture_times = []

captures_ADC1 = []
captures_ADC2 = []
captures_ADC3 = []

captures_TC1 = []
captures_TC2 = []
captures_TC3 = []

captures_lambda = []
captures_engineSpeed = []

start_time = time.time()

timestamp_for_file = dt.datetime.now().strftime("%Y%m%d%H%M%S")
csv_name = os.path.join(os.getenv("HOME"), "vanagauge", "logs", f"vanlog_{timestamp_for_file}.csv")

csv_file = open(csv_name, 'a', newline='')
csv_writer = csv.writer(csv_file)

csv_writer.writerow([
    "rtc_datetime",
    "gps_datetime_pst",
    "lat",
    "lon",
    "kph",
    "alt",
    "climb_mps",
    "OILP",
    "MAP",
    "MAT",
    "EGT",
    "OILT",
    "IAT",
    "lambda",
    "RPM",
    "event",
])
csv_file.flush()


def scaleNTC(count, table):
    if count == 0 or count is None:
        count = 4.9

    fixedResistor = 1800
    refVoltage = 5
    NTCresistance = (count * fixedResistor) / (refVoltage - count)

    index = 0
    while IAT_Temp_Table[index] > NTCresistance:
        index += 1

    lowerBound = IAT_Temp_Table[index - 1]
    upperBound = IAT_Temp_Table[index]
    offset = lowerBound - NTCresistance
    span = lowerBound - upperBound
    slope = offset / span
    correctedTemperature = (10 * slope) + (index * 10) - 50

    return correctedTemperature


def fmt0(value):
    if value is None:
        return ""
    return round(value, 0)


def fmt2(value):
    if value is None:
        return ""
    return round(value, 2)


def fmt4(value):
    if value is None:
        return ""
    return round(value, 4)


def fmt6(value):
    if value is None:
        return ""
    return round(value, 6)


def gps_datetime_pst_string(nav_sample):
    if nav_sample.utc_datetime is None:
        return ""
    return nav_sample.utc_datetime.astimezone(PST_TZ).strftime("%Y-%m-%dT%H:%M:%S")


def display_value(value, digits=1, suffix=""):
    if value is None:
        return "--"
    return f"{round(value, digits)}{suffix}"


def set_pending_event(name):
    global pending_event
    pending_event = name
    logging.warning(f"Event marker queued: {name}")


def on_coast_button(event):
    set_pending_event("coastdown")


def on_hill_button(event):
    set_pending_event("hill_climb")


def on_weird_button(event):
    set_pending_event("weird_event")


def on_setting_change_button(event):
    set_pending_event("setting_change")


def nav_good_fix(nav):
    return (
        nav.fix_valid
        and nav.fix_quality is not None
        and nav.fix_quality > 0
        and nav.sats is not None
        and nav.sats >= NAV_GOOD_FIX_MIN_SATS
        and nav.fused_alt_m is not None
    )


def quiet_nav(nav):
    global nav_good_fix_count
    global nav_ready
    global stationary_sample_count
    global filtered_alt_m
    global climb_history

    now_s = time.monotonic()
    good_fix = nav_good_fix(nav)

    lat = nav.lat_deg
    lon = nav.lon_deg
    speed_kph = nav.speed_kmh

    # 1) warmup suppress: do not publish alt/climb until nav is initialized
    if not nav_ready:
        if good_fix:
            nav_good_fix_count += 1
        else:
            nav_good_fix_count = 0

        if nav_good_fix_count >= NAV_GOOD_FIX_REQUIRED:
            nav_ready = True
            filtered_alt_m = nav.fused_alt_m
            climb_history.clear()
            if filtered_alt_m is not None:
                climb_history.append((now_s, filtered_alt_m))

        return {
            "lat": lat,
            "lon": lon,
            "speed_kph": speed_kph,
            "alt": None,
            "climb_mps": None,
            "stationary": False,
        }

    if not good_fix:
        return {
            "lat": lat,
            "lon": lon,
            "speed_kph": speed_kph,
            "alt": None,
            "climb_mps": None,
            "stationary": False,
        }

    # 2) stationary detector
    if speed_kph is not None and speed_kph < STATIONARY_SPEED_KPH:
        stationary_sample_count += 1
    else:
        stationary_sample_count = 0

    stationary = stationary_sample_count >= STATIONARY_SAMPLES_REQUIRED

    # 3) adaptive low-pass filter on altitude
    raw_alt = nav.fused_alt_m
    if raw_alt is not None:
        alpha = ALT_ALPHA_STATIONARY if stationary else ALT_ALPHA_MOVING
        if filtered_alt_m is None:
            filtered_alt_m = raw_alt
        else:
            filtered_alt_m = (alpha * raw_alt) + ((1.0 - alpha) * filtered_alt_m)

    # 4) long-window climb-rate estimate
    if filtered_alt_m is not None:
        climb_history.append((now_s, filtered_alt_m))
        while climb_history and (now_s - climb_history[0][0]) > CLIMB_WINDOW_S:
            climb_history.popleft()

    if stationary:
        climb_mps = 0.0
    elif len(climb_history) >= 2:
        t0, a0 = climb_history[0]
        t1, a1 = climb_history[-1]
        if t1 > t0:
            climb_mps = (a1 - a0) / (t1 - t0)
            if abs(climb_mps) < CLIMB_DEADBAND_MPS:
                climb_mps = 0.0
        else:
            climb_mps = None
    else:
        climb_mps = None

    return {
        "lat": lat,
        "lon": lon,
        "speed_kph": speed_kph,
        "alt": filtered_alt_m,
        "climb_mps": climb_mps,
        "stationary": stationary,
    }


# This function is called periodically from FuncAnimation
def animate(i, capture_times, captures_ADC1, captures_ADC2, captures_ADC3,
            captures_TC1, captures_TC2, captures_TC3, captures_lambda, captures_engineSpeed):
    global ADC1, ADC2, ADC3
    global pending_event

    ADC1 = ((techedge.readADC(DAQ, 1) - 0.5) / 4) * 100 + 3.3   # oil pressure
    ADC2 = (techedge.readADC(DAQ, 2) * 0.53 - 0.26)             # MAP
    ADC3 = scaleNTC(techedge.readADC(DAQ, 3), IAT_Temp_Table)   # intake NTC temp

    TC1 = techedge.readTC(DAQ, 1)
    TC2 = techedge.readTC(DAQ, 2)
    TC3 = techedge.readTC(DAQ, 3)

    widebandLambda = techedge.readLambda(DAQ)
    engineSpeed = techedge.readRPM(DAQ, 1)

    nav = NAV.snapshot()
    qnav = quiet_nav(nav)

    now = dt.datetime.now()
    rtc_datetime = now.strftime("%Y-%m-%dT%H:%M:%S") + f".{now.microsecond // 100000}"
    gps_datetime_pst = gps_datetime_pst_string(nav)

    lat = fmt2(qnav["lat"])
    lon = fmt2(qnav["lon"])
    speed_kph = fmt0(qnav["speed_kph"])
    fused_alt = fmt2(qnav["alt"])
    climb_rate = fmt2(qnav["climb_mps"])

    event_marker = pending_event

    csv_writer.writerow([
        rtc_datetime,
        gps_datetime_pst,
        lat,
        lon,
        speed_kph,
        fused_alt,
        climb_rate,
        fmt2(ADC1),
        fmt2(ADC2),
        fmt2(ADC3),
        fmt0(TC1),
        fmt0(TC2),
        fmt0(TC3),
        fmt4(widebandLambda),
        round(engineSpeed, 4) if engineSpeed is not None else "",
        event_marker,
    ])
    csv_file.flush()

    pending_event = "0"

    logging.warning(f"ADC1: {ADC1}")
    logging.warning(f"ADC2: {ADC2}")
    logging.warning(f"ADC3: {ADC3}")

    logging.warning(f"TC1: {TC1}")
    logging.warning(f"TC2: {TC2}")
    logging.warning(f"TC3: {TC3}")

    logging.warning(f"widebandLambda: {widebandLambda}")
    logging.warning(f"RPM: {engineSpeed}")

    logging.warning(f"GPS datetime PST: {gps_datetime_pst}")
    logging.warning(f"Lat: {lat}")
    logging.warning(f"Lon: {lon}")
    logging.warning(f"Speed kph: {speed_kph}")
    logging.warning(f"Fused alt: {fused_alt}")
    logging.warning(f"Climb rate: {climb_rate}")
    logging.warning(f"Event: {event_marker}")

    # Add x and y to lists
    time_since_start = time.time() - start_time
    capture_times.append(time_since_start)

    captures_ADC1.append(ADC1)
    captures_ADC2.append(ADC2 * 100)
    captures_ADC3.append(ADC3)

    captures_TC1.append(TC1 / 10)
    captures_TC2.append(TC2 / 10)
    captures_TC3.append(TC3 / 10)

    captures_lambda.append((widebandLambda * 100) - 100)
    captures_engineSpeed.append(engineSpeed / 100)

    # Limit x and y lists to 50 items, in place
    del capture_times[:-50]
    del captures_ADC1[:-50]
    del captures_ADC2[:-50]
    del captures_ADC3[:-50]
    del captures_TC1[:-50]
    del captures_TC2[:-50]
    del captures_TC3[:-50]
    del captures_lambda[:-50]
    del captures_engineSpeed[:-50]

    ax.clear()

    ADC1readOut.set_text('OIL P: ' + display_value(ADC1, 1, ' PSI'))
    ADC2readOut.set_text('MAN P: ' + display_value(ADC2, 1, ' bar'))
    ADC3readOut.set_text('MAN T: ' + display_value(ADC3, 1, chr(176) + 'C'))

    TC1readOut.set_text('EGT: ' + display_value(TC1, 1, chr(176) + 'C'))
    TC2readOut.set_text('OIL T: ' + display_value(TC2, 1, chr(176) + 'C'))
    TC3readOut.set_text('Air T: ' + display_value(TC3, 1, chr(176) + 'C'))

    lambdaReadout.set_text('lambda: ' + display_value(widebandLambda, 2))
    rpmReadout.set_text('RPM: ' + display_value(engineSpeed, 0))

    GPSlatitudeReadout.set_text('Lat: ' + display_value(qnav["lat"], 2))
    GPSlongitudeReadout.set_text('Lon: ' + display_value(qnav["lon"], 2))
    GPSspeedReadout.set_text('Speed kph: ' + display_value(qnav["speed_kph"], 0))
    GPSaltitudeReadout.set_text('Alt m: ' + display_value(qnav["alt"], 0))
    GPSclimbRateReadout.set_text('Climb m/s: ' + display_value(qnav["climb_mps"], 1))

    ax.set(ylim=(0, 100))

    ax.plot(capture_times, captures_ADC1, lw=2, color='purple')
    ax.plot(capture_times, captures_ADC2, lw=5, color='green')
    ax.plot(capture_times, captures_ADC3, lw=2, color='blue')

    ax.plot(capture_times, captures_TC1, lw=2, color='yellow')
    ax.plot(capture_times, captures_TC2, lw=2, color='orange')
    ax.plot(capture_times, captures_TC3, lw=2, color='red')

    ax.plot(capture_times, captures_lambda, lw=2, color='red')
    ax.plot(capture_times, captures_engineSpeed, lw=2, color='pink')

    plt.grid(True)
    plt.subplots_adjust(left=0.25, bottom=0.2, right=0.99, top=0.99)
    plt.title('')
    plt.ylabel('Pressure BAR / Throttle % / Temperature degC')


if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.WARN)

    DAQ = techedge.init('/dev/ttyS0')
    NAV = gps_fused.init(
        gps_port='/dev/ttyAMA3',
        gps_baud=9600,
        enable_bme=True,
        bme_address=0x76,
    )

    coast_button.on_clicked(on_coast_button)
    hill_button.on_clicked(on_hill_button)
    weird_button.on_clicked(on_weird_button)
    setting_change_button.on_clicked(on_setting_change_button)

    ani = animation.FuncAnimation(
        fig,
        animate,
        fargs=(capture_times, captures_ADC1, captures_ADC2, captures_ADC3,
               captures_TC1, captures_TC2, captures_TC3, captures_lambda, captures_engineSpeed),
        interval=250,
        cache_frame_data=False
    )

    try:
        plt.show()
    finally:
        try:
            NAV.close()
        except Exception:
            pass
        csv_file.close()