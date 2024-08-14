import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import random
import time
import wensn

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

#setup dbl meter
dev = wensn.connect()

# set default modes: range="30-130", speed="slow", weight="A", maxMode="instant"
wensn.setMode(dev)

# This function is called periodically from FuncAnimation
def animate(i, xs, ys, zs):

    # Read temperature (Celsius) from TMP102
    temp_c = random.randint(0, 100)
    temp_d = random.randint(0, 100)

    dB, range, weight, speed = wensn.readSPL(dev)

    temp_c = dB
    temp_d = 0

    # Add x and y to lists
    time_since_start = time.time() - start_time
    xs.append(time_since_start)
    ys.append(temp_c)
    zs.append(temp_d)

    # Limit x and y lists to 20 items
    xs = xs[-30:]
    ys = ys[-30:]
    zs = zs[-30:]

    xlist = [xs, xs]
    ylist = [ys, zs]

    #print(ylist)
    #print(list(enumerate(ylist)))

    # Draw x and y lists
    ax.clear()

    #for linenumber in ylist:
        #ax.plot(xlist[linenumber], ylist[linenumber])

    ax.set(ylim=(0, 150))
    ax.plot(xlist[0], ylist[0],lw=2,color='green')
    ax.plot(xlist[1], ylist[1],lw=2,color='blue')

    # Format plot
    plt.xticks(rotation=45, ha='right')
    plt.grid(True)
    plt.subplots_adjust(left=0.1, bottom=0.1, right=1, top=0.95)
    plt.title('Exhaust Temperatures')
    plt.ylabel('Temperature degree C')

# Set up plot to call animate() function periodically
ani = animation.FuncAnimation(fig, animate, fargs=(xs, ys, zs), interval=100, cache_frame_data=False)
plt.show()