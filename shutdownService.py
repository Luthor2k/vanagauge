#!/usr/bin/env python3

#wait for gpio edge to trigger a safe shutdown

import time
import RPi.GPIO as GPIO 

shutdown_pin = 17
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(shutdown_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def shut_down():
    print("shutting down")
    command = "/usr/bin/sudo /sbin/shutdown -h now"
    import subprocess
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    print(output)

while True:
    channel = GPIO.wait_for_edge(shutdown_pin, GPIO.RISING, bouncetime=200)

    if channel is None:
        print('channel is None')
    else:
        print('GPIO.wait_for_edge(shutdown_pin, GPIO.RISING')
        shut_down()