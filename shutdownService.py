#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import subprocess

PIN = 17              # BCM numbering
LOW_HOLD_S = 0.250    # 250 ms

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

try:
    print(f"Watching GPIO{PIN} with internal pull-up enabled")
    print(f"Will shut down if held LOW for >= {int(LOW_HOLD_S * 1000)} ms")

    low_since = None
    shutdown_requested = False

    while True:
        state = GPIO.input(PIN)
        now = time.monotonic()

        if state == GPIO.LOW:
            if low_since is None:
                low_since = now

            if not shutdown_requested and (now - low_since) >= LOW_HOLD_S:
                shutdown_requested = True
                print("Shutdown requested")

                # Graceful shutdown via systemd
                subprocess.run(
                    ["/usr/bin/systemctl", "poweroff"],
                    check=False
                )

                break
        else:
            low_since = None

        time.sleep(0.01)

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()