import serial

ENGINE_PULSES_PER_REV = 1

#DAQ_Temp_Table = [-63, -27, -14, -5, 2, 8, 14, 19, 25, 31, 37, 44, 51, 61, 75, 98, 161] #max temperarture is 161 degC and corrospondes to b0, min temperature is -63 degC and corrosponds to b1024
DAQ_Temp_Table = [161, 98, 75, 61, 51, 44, 37, 31, 25, 19, 14, 8, 2, -5, -14, -27, -63]

K_Type_Thermocouple_Table = [0, 76,  151, 229, 304, 378, 452, 524, 597, 670, 744, 819, 896, 974, 1054, 1136, 1220]

#oil pressure measurements
#supply to sensor 5.0V, blue=signal, black=5V, grey=GND
#0psi = 0.487V
#30 = 1.42
#45 = 1.91
#60 = 2.45
#75 = 2.90
#90 = 3.29

#0.5 - 4.5 = 0 to 120 PSI, trim afterwards

#manifold pressure sensor is spec'd at 30PSI, 0.5V-4.5V
#supply to sensor 5.0V, blue=signal, black=5V, grey=GND

def lookupReference(rawValue, rawMax, lookupTable):
    if rawValue > rawMax:
        return 0

    tableBracketCount = len(lookupTable)
    #print(f"tableBracketCount: {tableBracketCount}")

    rawFraction = rawValue / rawMax
    #print(f"rawFraction: {rawFraction}")

    scaledToLookup = rawFraction * (tableBracketCount - 1) #its minus 1 because we're going to add the adjustment to the lowerbound
    #print(f"scaledToLookup: {scaledToLookup}")

    upperBound = lookupTable[int(scaledToLookup)]
    lowerBound = lookupTable[int(scaledToLookup) + 1] 

    #print(f"upperBound: {upperBound}")
    #print(f"lowerBound: {lowerBound}")

    linearAdjustment = scaledToLookup - int(scaledToLookup) #get remainder for the linearlization
    #print(f"linearAdjustment: {linearAdjustment}")

    intervalWidth = upperBound - lowerBound
    #print(f"intervalWidth: {intervalWidth}")

    adjustment = intervalWidth * linearAdjustment
    #print(f"adjustment: {adjustment}")

    scaledValue = lowerBound + adjustment
    #print(f"scaledValue: {scaledValue}")

    return scaledValue

def init(ser):
    #ser = serial.Serial('/dev/ttyUSB0', 19200, timeout=1)  # open serial port
    print(ser.name)         # check which port was really used

    techedgeActive = True

    while techedgeActive:
        incomingSerial = bytes(ser.read(size=28))
        #print(incomingSerial)
        if len(incomingSerial) < 1:
            techedgeActive = False
            print("no data from serial port")
            break

        #check for header
        headerLocation = incomingSerial.find('\x5a\xa5'.encode())
        print(f"found header: {headerLocation}")

        if headerLocation == -1:
            print("good header")

            #check the checksum

            #parse the frame
            sequence_counter = incomingSerial[2]
            
            DAQRawLambda16 = (int(incomingSerial[4]) * 256) + int(incomingSerial[5])

            DAQRawUser1 = (int(incomingSerial[9]) * 256) + int(incomingSerial[10])      #boost pressure
            DAQRawUser2 = (int(incomingSerial[11]) * 256) + int(incomingSerial[12])    #throttle position
            DAQRawUser3 = (int(incomingSerial[13]) * 256) + int(incomingSerial[14])    #intake temperature

            DAQRawThermocouple1 = (int(incomingSerial[15]) * 256) + int(incomingSerial[16])  #egt, needs correcting curve to be applied
            DAQRawThermocouple2 = (int(incomingSerial[17]) * 256) + int(incomingSerial[18])  #oil temp
            DAQRawThermocouple3 = (int(incomingSerial[19]) * 256) + int(incomingSerial[20])  #turbo temp

            DAQRawOnboardThermistor = (int(incomingSerial[21]) * 256) + int(incomingSerial[22])
            DAQRawRPMCount = (int(incomingSerial[23]) * 256) + int(incomingSerial[24])

            DAQRawSensorState = byte(incomingSerial[24]) & byte(0x07);  #wideband pump cell pid state bits
            DAQRawHeaterState = byte(incomingSerial[25]) & byte(0x07);  #wideband heater pid state bits
            '''
            print(sequence_counter)
            print(DAQRawUser1)
            print(DAQRawUser2)
            print(DAQRawUser3)
            print(DAQRawThermocouple1)
            print(DAQRawThermocouple2)
            print(DAQRawThermocouple3)
            print(f"DAQRawOnboardThermistor: {DAQRawOnboardThermistor}")
            '''

            if DAQRawRPMCount != 0:
                measuredRPM = 12000000 / (DAQRawRPMCount * ENGINE_PULSES_PER_REV)
            else:
                measuredRPM = 0

            #measuredDAQTemperature = 
            #for (parsingLoopCounter = 1; DAQRawOnboardThermistor < DAQ_Temp_Table[parsingLoopCounter]; parsingLoopCounter = parsingLoopCounter + 2) { }
            #DAQTemperatureC = map(DAQRawOnboardThermistor, DAQ_Temp_Table[parsingLoopCounter - 2], DAQ_Temp_Table[parsingLoopCounter], DAQ_Temp_Table[parsingLoopCounter - 3], DAQ_Temp_Table[parsingLoopCounter - 1]);

            #DAQ raw temp readings will be 0 - 1024 and non linear.
            #max temperarture is 161 degC and corrospondes to b0, min temperature is -63 degC and corrosponds to b1024
            #the lookup table contains 17 values
            #select the bounds and linearize between the two values in question
            
            DAQThermistorScaled = lookupReference(DAQRawOnboardThermistor, 1023, DAQ_Temp_Table)
            print(f"DAQThermistorScaled: {DAQThermistorScaled} degC")
            
            #ManifoldTemperature =  
            #PreCatTemperature = 
            #PostCatTemperature = 

            IntakeTemperature =  DAQRawUser1 / 8184 * 5
            print(f"IntakeTemperature: {IntakeTemperature} degC")

            #IntakePressure =  ((DAQRawUser2 / DAQMAX * 5 VOLTS) - 0.5 VOLT OFFSET ) / 4 VOLT SPAN * 30PSI SPAN
            IntakePressure =  ((DAQRawUser2 / 8184 * 5) - 0.5 ) / 4 * 30
            print(f"IntakePressure: {IntakePressure} PSI")

            #oil pressure max = 120PSI
            OilPressure = ((DAQRawUser2 / 8184 * 5) - 0.5) / 4 * 120
            print(f"OilPressure: {OilPressure} PSI")

            #Voltage = 
            
            #print the variables
            print("\n")

    ser.close()             # close port

def readCounter():
    
    return sequence_counter