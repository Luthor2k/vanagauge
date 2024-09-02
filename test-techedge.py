import techedge
import logging
import time

print("hello")


DAQ = techedge.init('/dev/ttyS0')

#IAT sensor table, ohms resistance starting at -40degC and up to 140degC
IAT_Temp_Table = [45313, 26114, 15462, 9397, 5896, 3792, 2500, 1707, 1175, 834, 596, 436, 323, 243, 187, 144, 113, 89, 71]
#                   -40     -30     -20 -10   0     10    20    30

def scaleNTC(count, table): #channel, reference table

    if count == 0 or count == None:
        count = 4

    print(f"count: {count}")

    fixedResistor = 1800
    refVoltage = 5

    NTCresistance = (count * fixedResistor) / (refVoltage - count)
    print(f"NTCresistance: {NTCresistance}")

    index = 0

    while IAT_Temp_Table[index] > NTCresistance:
        index += 1
    print(f"index: {index}")


    lowerBound = IAT_Temp_Table[index-1]
    print(f"lowerBound: {lowerBound}")
    upperBound = IAT_Temp_Table[index]
    print(f"upperBound: {upperBound}")

    offset = lowerBound - NTCresistance
    print(f"offset: {offset}")

    span = lowerBound - upperBound
    print(f"span: {span}")

    slope = offset / span
    print(f"slope: {slope}")

    correctedTemperature = (10 * slope) + (index * 10) - 50

    return correctedTemperature

while True:
    #logging.warning("tick")
    #TC1 = techedge.readTC(DAQ, 1)
    #print(f"TC1 Temperature: {TC1}")

    #adc = techedge.readADC(DAQ, 1)
    ##print(f"adc1: {adc}")

    #adc = techedge.readADC(DAQ, 2)
    #print(f"adc2: {adc}")    

    #temperatureManifold = DAQ.readTC(0, TYPE_K_LOOKUP_TABLE) #channel, reference table

    #throttlePosition = DAQ.readADC(0, 0, 1023) #channel, min, max

    #widebandLambda = techedge.readLambda(DAQ)
    #print(f"wideband: {widebandLambda}") 

    #bayTemperature = techedge.readThermistor(DAQ)
    #print(f"DAC Temperature: {bayTemperature}")

    #engineSpeed = techedge.readRPM(DAQ,1)
    #print(f"engineSpeed: {engineSpeed}") 

    #DAQstatus = DAQ.readStatus()

    #DAQstep = DAQ.readCounter()

    intakeTemperature = techedge.readADC(DAQ, 3)
    scaledTemperature = scaleNTC(intakeTemperature, IAT_Temp_Table)
    print(f"intakeTemperature: {scaledTemperature}\n\n") 


    time.sleep(0.25)