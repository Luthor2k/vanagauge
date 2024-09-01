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

ADC1readOut = plt.figtext(0, 0, '0', color = 'white', fontsize = 'large')
ADC2readOut = plt.figtext(0.2, 0, '0', color = 'white', fontsize = 'large')
ADC3readOut = plt.figtext(0.4, 0, '0', color = 'white', fontsize = 'large')

TC1readOut = plt.figtext(0.6, 0, '0', color = 'white', fontsize = 'large')

capture_times = []

captures_ADC1 = []
captures_ADC2 = []
captures_ADC3 = []

captures_TC1 = []
captures_TC2 = []
captures_TC3 = []

start_time = time.time()

# This function is called periodically from FuncAnimation
def animate(i, capture_times, captures_ADC1, captures_ADC2, captures_ADC3, captures_TC1, captures_TC2, captures_TC3):
    global ADC1, ADC2, ADC3

    ADC1 = techedgemodule.readADC(DAQ, 1) * 20 #adc1: 4.999 = 100%
    ADC2 = techedgemodule.readADC(DAQ, 2) * 7.2 #adc2: 4.150390625 = 30PSI
    ADC3 = techedgemodule.readADC(DAQ, 3) #* 72

    TC1 = techedgemodule.readTC(DAQ, 1)
    TC2 = techedgemodule.readTC(DAQ, 2)
    TC3 = techedgemodule.readTC(DAQ, 3)

    logging.warning(f"ADC1: {ADC1}")
    logging.warning(f"ADC2: {ADC2}")
    logging.warning(f"ADC2: {ADC3}")
    
    logging.warning(f"TC1: {TC1}")
    logging.warning(f"TC2: {TC2}")
    logging.warning(f"TC3: {TC3}")

    # Add x and y to lists
    time_since_start = time.time() - start_time
    capture_times.append(time_since_start)

    captures_ADC1.append(ADC1)
    captures_ADC2.append(ADC2)
    captures_ADC3.append(ADC3)

    captures_TC1.append(TC1)
    captures_TC2.append(TC2)
    captures_TC3.append(TC3)

    # Limit x and y lists to 20 items
    capture_times = capture_times[-50:]

    captures_ADC1 = captures_ADC1[-50:]
    captures_ADC2 = captures_ADC2[-50:]
    captures_ADC3 = captures_ADC3[-50:]

    captures_TC1 = captures_TC1[-50:]
    captures_TC2 = captures_TC2[-50:]
    captures_TC3 = captures_TC3[-50:]

    ax.clear() #breaks the text updates for some reason? now it doesn't?

    ADC1readOut.set_text('TPS: ' + str(round(ADC1,1)) + ' %')
    ADC2readOut.set_text('MAP: ' + str(round(ADC2,1)) + ' PSI')
    ADC3readOut.set_text('IAT: ' + str(round(ADC3,1)) + ' C')

    TC1readOut.set_text('EGT: ' + str(round(TC1,1)) + ' C')

    ax.set(ylim=(0, 100))

    ax.plot(capture_times, captures_ADC1,lw=2,color='purple')
    ax.plot(capture_times, captures_ADC2,lw=2,color='green')
    ax.plot(capture_times, captures_ADC3,lw=2,color='blue')

    ax.plot(capture_times, captures_TC1,lw=2,color='yellow')
    ax.plot(capture_times, captures_TC2,lw=2,color='orange')
    ax.plot(capture_times, captures_TC3,lw=2,color='red')

    

    # Format plot - chaos.. what is desired: fixed width of ticks around whole numbers, rolling chart
    #plt.xticks(rotation=45, ha='right')
    #plt.xticks(rotation=0)
    #plt.xticks(np.arange(min(capture_times), max(capture_times)+1, 5.0))
    #plt.xticks(ticks=plt.xticks()[0], labels=plt.xticks()[0].astype(int))
    #ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%0.0f'))

    plt.grid(True)
    plt.subplots_adjust(left=0.1, bottom=0.1, right=0.95, top=0.95)
    plt.title('Exhaust Temperatures')
    plt.ylabel('Pressure PSI / Throttle % / Temperature degC')

    

if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.WARN)

    # Set up plot to call animate() function periodically
    ani = animation.FuncAnimation(fig, animate, fargs=(capture_times, captures_ADC1, captures_ADC2, captures_ADC3, captures_TC1, captures_TC2, captures_TC3), interval=500, cache_frame_data=False)

    DAQ = techedgemodule.init('/dev/ttyS0')

    plt.show()