import datetime as dt
import logging

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.ticker as ticker

import numpy as np
import csv
import time
import os

import techedge

IAT_Temp_Table = []

# Create figure for plotting
plt.rcParams['toolbar'] = 'None'
plt.style.use('dark_background')
fig = plt.figure()
fig.canvas.manager.set_window_title("VanPlot")
fig.canvas.manager.full_screen_toggle()

ax = fig.add_subplot(1, 1, 1)

ADC1readOut = plt.figtext(0, 0, '0', color = 'purple', fontsize = 'large')
ADC2readOut = plt.figtext(0.15, 0, '0', color = 'green', fontsize = 'large')
ADC3readOut = plt.figtext(0.3, 0, '0', color = 'blue', fontsize = 'large')

TC1readOut = plt.figtext(0.45, 0, '0', color = 'yellow', fontsize = 'large')

lambdaReadout = plt.figtext(0.6, 0, '0', color = 'red', fontsize = 'large')
rpmReadout = plt.figtext(0.75, 0, '0', color = 'pink', fontsize = 'large')

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

dateTimeToday = time.strftime("%d%b%Y%H%M%S")

csv_name = os.getenv("HOME") + "/vanagauge/logs/datalog_" + dateTimeToday + ".csv"
csvRow = "ADC1, ADC2, ADC3, TC1, TC2, TC3, lambda, RPM\n"
with open(csv_name,'a') as logFile:
    logFile.write(csvRow)

def scaleNTC(count, table): #channel, reference table

    seg = int(count / 64)       #round down to find what interval it's in
    print(f"seg: {seg}")
    
    counta = seg * 64             #count at the start of that interval
    print(f"counta: {counta}")

    offset = count - counta       #offset into the selected interval
    print(f"offset: {offset}")
    
    tempa = table[seg]      #temperature at the interval start
    print(f"tempa: {tempa}")

    tempb = table[seg + 1]  #and at the end of the interval
    print(f"tempb: {tempb}")

    m = (tempb - tempa) / 64      #slope of count vs. temperature
    print(f"m: {m}")

    temp = (m * offset) + tempa   #straight line interpolation y = mx + c
    print(f"temp: {temp}")
    
    return temp

# This function is called periodically from FuncAnimation
def animate(i, capture_times, captures_ADC1, captures_ADC2, captures_ADC3, captures_TC1, captures_TC2, captures_TC3, captures_lambda, captures_engineSpeed):
    global ADC1, ADC2, ADC3

    ADC1 = techedge.readADC(DAQ, 1) * 20 #adc1: 4.999 = 100%
    #ADC2 = 100 * (techedge.readADC(DAQ, 2) / 4 - 0.125) #adc2: MAP
    ADC2 = techedge.readADC(DAQ, 2) * 0.53 #adc2: MAP
    ADC3 = (5 - techedge.readADC(DAQ, 3)) * 113.8 - 283

    TC1 = techedge.readTC(DAQ, 1)
    TC2 = techedge.readTC(DAQ, 2)
    TC3 = techedge.readTC(DAQ, 3)

    widebandLambda = techedge.readLambda(DAQ)
    engineSpeed = techedge.readRPM(DAQ,1)

    csv_name = os.getenv("HOME") + "/vanagauge/logs/datalog_" + dateTimeToday + ".csv"
    csvRow = str(ADC1) + ", " + str(ADC2) + ", " + str(ADC3) + ", " + str(TC1) + ", " + str(TC2) + ", " + str(TC3) + ", " + str(widebandLambda) + ", " + str(engineSpeed) + '\n'
    with open(csv_name,'a') as logFile:
        logFile.write(csvRow)

    logging.warning(f"ADC1: {ADC1}")
    logging.warning(f"ADC2: {ADC2}")
    logging.warning(f"ADC2: {ADC3}")
    
    logging.warning(f"TC1: {TC1}")
    logging.warning(f"TC2: {TC2}")
    logging.warning(f"TC3: {TC3}")

    logging.warning(f"widebandLambda: {widebandLambda}")

    logging.warning(f"RPM: {engineSpeed}")

    # Add x and y to lists
    time_since_start = time.time() - start_time
    capture_times.append(time_since_start)

    captures_ADC1.append(ADC1)
    captures_ADC2.append(ADC2*100)  #by 100 since bar to % will be legible
    captures_ADC3.append(ADC3)

    captures_TC1.append(TC1 / 10)
    captures_TC2.append(TC2 / 10)
    captures_TC3.append(TC3 / 10)

    captures_lambda.append((widebandLambda * 100) - 100)
    captures_engineSpeed.append(engineSpeed / 100)

    # Limit x and y lists to 20 items
    capture_times = capture_times[-50:]

    captures_ADC1 = captures_ADC1[-50:]
    captures_ADC2 = captures_ADC2[-50:]
    captures_ADC3 = captures_ADC3[-50:]

    captures_TC1 = captures_TC1[-50:]
    captures_TC2 = captures_TC2[-50:]
    captures_TC3 = captures_TC3[-50:]

    captures_lambda = captures_lambda[-50:]
    captures_engineSpeed = captures_engineSpeed[-50:]

    ax.clear() #breaks the text updates for some reason? now it doesn't?

    ADC1readOut.set_text('TPS: ' + str(round(ADC1,1)) + ' %')
    ADC2readOut.set_text('MAP: ' + str(round(ADC2,2)) + ' bar')
    ADC3readOut.set_text('IAT: ' + str(round(ADC3,3)) + ' C')

    TC1readOut.set_text('EGT: ' + str(round(TC1,1)) + ' C')

    lambdaReadout.set_text('lambda: ' + str(round(widebandLambda,2)))
    rpmReadout.set_text('RPM: ' + str(round(engineSpeed,0)))

    ax.set(ylim=(0, 100))

    ax.plot(capture_times, captures_ADC1,lw=2,color='purple')
    ax.plot(capture_times, captures_ADC2,lw=2,color='green')
    ax.plot(capture_times, captures_ADC3,lw=2,color='blue')

    ax.plot(capture_times, captures_TC1,lw=2,color='yellow')
    #ax.plot(capture_times, captures_TC2,lw=2,color='orange')
    #ax.plot(capture_times, captures_TC3,lw=2,color='red')

    ax.plot(capture_times, captures_lambda,lw=2,color='red')
    ax.plot(capture_times, captures_engineSpeed,lw=2,color='pink')

    # Format plot - chaos.. what is desired: fixed width of ticks around whole numbers, rolling chart
    #plt.xticks(rotation=45, ha='right')
    #plt.xticks(rotation=0)
    #plt.xticks(np.arange(min(capture_times), max(capture_times)+1, 5.0))
    #plt.xticks(ticks=plt.xticks()[0], labels=plt.xticks()[0].astype(int))
    #ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%0.0f'))

    plt.grid(True)
    plt.subplots_adjust(left=0.1, bottom=0.1, right=0.95, top=0.95)
    plt.title('')
    plt.ylabel('Pressure BAR / Throttle % / Temperature degC')

if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.WARN)

    # Set up plot to call animate() function periodically
    ani = animation.FuncAnimation(fig, animate, fargs=(capture_times, captures_ADC1, captures_ADC2, captures_ADC3, captures_TC1, captures_TC2, captures_TC3, captures_lambda, captures_engineSpeed), interval=250, cache_frame_data=False)

    DAQ = techedge.init('/dev/ttyS0')

    plt.show()