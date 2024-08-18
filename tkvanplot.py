import datetime as dt
import logging

from tkinter import * 
from tkinter import ttk
import sv_ttk

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.ticker as ticker
#import tmp102
import random
import time
#import threading
#import wensn
import numpy as np
import techedgemodule

# Create figure for plotting
plt.rcParams['toolbar'] = 'None'
plt.style.use('dark_background')
fig = plt.figure()
fig.canvas.manager.set_window_title("VanPlot")
fig.canvas.manager.full_screen_toggle()

ax = fig.add_subplot(1, 1, 1)

xs = []
ys = []
zs = []

# Initialize communication with TMP102
#tmp102.init()

start_time = time.time()

ADC1 = 500
ADC2 = 500

# This function is called periodically from FuncAnimation
def animate(i, xs, ys, zs):
    global ADC1
    global ADC2

    # Read temperature (Celsius) from TMP102
    ADC1 = ADC1 + random.randint(-10, 10)
    ADC2 = ADC2 + random.randint(-10, 10)

    ADC1 = techedgemodule.readADC(DAQ, 1) * 200 #adc1: 4.999 = 100%
    ADC2 = techedgemodule.readADC(DAQ, 2) * 72 #adc2: 4.150390625 = 30PSI

    logging.info(f"ADC1: {ADC1}")
    logging.info(f"ADC2: {ADC2}")
    


    # Add x and y to lists
    time_since_start = time.time() - start_time
    xs.append(time_since_start)
    ys.append(ADC1)
    zs.append(ADC2)

    # Limit x and y lists to 20 items
    xs = xs[-50:]
    ys = ys[-50:]
    zs = zs[-50:]

    xlist = [xs, xs]
    ylist = [ys, zs]

    #print(ylist)
    #print(list(enumerate(ylist)))

    # Draw x and y lists
    ax.clear()

    #for linenumber in ylist:
        #ax.plot(xlist[linenumber], ylist[linenumber])

    ax.set(ylim=(0, 1000))
    ax.plot(xlist[0], ylist[0],lw=2,color='green')
    ax.plot(xlist[1], ylist[1],lw=2,color='blue')

    # Format plot - chaos.. what is desired: fixed width of ticks around whole numbers, rolling chart
    #plt.xticks(rotation=45, ha='right')
    #plt.xticks(rotation=0)
    #plt.xticks(np.arange(min(xs), max(xs)+1, 5.0))
    #plt.xticks(ticks=plt.xticks()[0], labels=plt.xticks()[0].astype(int))
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%0.0f'))

    plt.grid(True)
    plt.subplots_adjust(left=0.1, bottom=0.1, right=0.95, top=0.95)
    plt.title('Exhaust Temperatures')
    plt.ylabel('Temperature degree C')

if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.WARNING)

    # Set up plot to call animate() function periodically
    ani = animation.FuncAnimation(fig, animate, fargs=(xs, ys, zs), interval=500, cache_frame_data=False)
    #set_cursor(cursor)

    DAQ = techedgemodule.init('/dev/ttyUSB0')

    plt.show()