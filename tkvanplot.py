import datetime as dt

from tkinter import * 
from tkinter import ttk
import sv_ttk

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.ticker as ticker
#import tmp102
import random
import time
#import techedge
#import threading
#import wensn
import numpy as np

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

temp_c = 500
temp_d = 500

# This function is called periodically from FuncAnimation
def animate(i, xs, ys, zs):
    global temp_c
    global temp_d

    # Read temperature (Celsius) from TMP102
    temp_c = temp_c + random.randint(-10, 10)
    temp_d = temp_d + random.randint(-10, 10)

    # Add x and y to lists
    time_since_start = time.time() - start_time
    xs.append(time_since_start)
    ys.append(temp_c)
    zs.append(temp_d)

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

# Set up plot to call animate() function periodically
ani = animation.FuncAnimation(fig, animate, fargs=(xs, ys, zs), interval=500, cache_frame_data=False)
plt.show()