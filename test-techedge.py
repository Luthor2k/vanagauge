import techedgemodule
import logging
import time

print("hello")


DAQ = techedgemodule.init('/dev/ttyUSB0')

while True:
    logging.warning("tick")
    TC1 = techedgemodule.getReadings(DAQ)
    print(TC1)

    adc = techedgemodule.readADC(DAQ, 1)
    print(f"adc1: {adc}")

    adc = techedgemodule.readADC(DAQ, 2)
    print(f"adc2: {adc}")    

    '''
    temperatureManifold = DAQ.readTC(0, TYPE_K_LOOKUP_TABLE) #channel, reference table

    throttlePosition = DAQ.readADC(0, 0, 1023) #channel, min, max

    wideband = DAQ.readLambda()

    bayTemperature = DAQ.readThermistor()

    engineSpeed = DAQ.readRPM()

    DAQstatus = DAQ.readStatus()

    DAQstep = DAQ.readCounter()
    '''

    time.sleep(0.25)