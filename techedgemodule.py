import logging
from serial import Serial
from serial.threaded import ReaderThread, Protocol, LineReader
import time

#tech edge frame format:
'''
2.0 Data Frame Format

  1   - Frame Header byte 1 (0x5A)
  2   - Frame Header byte 2 (0xA5)

  3   - Frame Sequence counter

  4   - Tick [high] (1 tick = 1/100 Second)
  5   - Tick [low] byte

  6   - λ-16 or Ipx(0), (or ADC) [high] byte
  7   - λ-16 or Ipx(0), (or ADC) [low] byte

  8   - Ipx(1) [high] (8192=F/A, 4096=Ipx[0])
  9   - Ipx(1) [low] byte

  10 - User 1 ADC [high] (V1 input)
  11 - User 1 ADC [low] byte
  12 - User 2 ADC [high] (V2 input)
  13 - User 2 ADC [low] byte
  14 - User 3 ADC [high] (V3 input)
  15 - User 3 ADC [low] byte

  16 - Thermocouple 1 ADC [high] (T1 Input)
  17 - Thermocouple 1 ADC [low]
  18 - Thermocouple 2 ADC [high] (T2 Input)
  19 - Thermocouple 2 ADC [low]
  20 - Thermocouple 3 ADC [high] (T3 Input)
  21 - Thermocouple 3 ADC [low]

  22 - Thermistor ADC or Vss count [high]
  23 - Thermistor ADC or Vss count [low]

  24 - RPM count [high] byte
  25 - RPM count [low] bye

  26 - Status/Error [high] byte
  27 - Status/Error [low] byte

  28 - CRC (1's comp. sum of above) 
'''  

class SerialReaderProtocolLine(LineReader):
    TERMINATOR = b'\x5a\xa5' #tech edge

    var_listener = None

    sequence_counter = None

    DAQRawLambda16 = None

    DAQRawUser1 = None
    DAQRawUser2 = None
    DAQRawUser3 = None

    DAQRawThermocouple1 = None
    DAQRawThermocouple2 = None
    DAQRawThermocouple3 = None

    DAQRawOnboardThermistor = None

    DAQRawRPMCount = None

    #def __init__(self):
    #    self.DAQRawThermocouple1 = 0

    def connection_made(self, transport):
        super().connection_made(transport)
        logging.debug("Connected, ready to receive data...")


    def handle_packet(self, line):
        logging.debug(f"data: {line}")
        #check length
        lineLength = len(line)
        if lineLength < 25:
            logging.debug(f"SHORT! lineLength: {lineLength}")
            return
        #check checksum

        #parse the frame
        self.sequence_counter = line[0]
        logging.info(f"sequence_counter: {self.sequence_counter}")

        self.DAQRawLambda16 = (int(line[3]) * 256) + int(line[4])
        logging.info(f"sequence_counter: {self.sequence_counter}")

        self.DAQRawUser1 = (int(line[7]) * 256) + int(line[8])      #boost pressure
        self.DAQRawUser2 = (int(line[9]) * 256) + int(line[10])    #throttle position
        self.DAQRawUser3 = (int(line[11]) * 256) + int(line[12])    #intake temperature
        logging.info(f"DAQRawUser1: {self.DAQRawUser1}")
        logging.info(f"DAQRawUser2: {self.DAQRawUser2}")
        logging.info(f"DAQRawUser3: {self.DAQRawUser3}")

        self.DAQRawThermocouple1 = (int(line[13]) * 256) + int(line[14])  #egt, needs correcting curve to be applied
        self.DAQRawThermocouple2 = (int(line[15]) * 256) + int(line[16])  #oil temp
        self.DAQRawThermocouple3 = (int(line[17]) * 256) + int(line[18])  #turbo temp
        logging.info(f"DAQRawThermocouple1: {self.DAQRawThermocouple1}")
        logging.info(f"DAQRawThermocouple2: {self.DAQRawThermocouple2}")
        logging.info(f"DAQRawThermocouple3: {self.DAQRawThermocouple3}")

        self.DAQRawOnboardThermistor = (int(line[19]) * 256) + int(line[20])
        self.DAQRawRPMCount = (int(line[21]) * 256) + int(line[22])
        logging.info(f"DAQRawOnboardThermistor: {self.DAQRawOnboardThermistor}")
        logging.info(f"DAQRawRPMCount: {self.DAQRawRPMCount}")

        #DAQRawSensorState = byte(line[24]) & byte(0x07);  #wideband pump cell pid state bits
        #DAQRawHeaterState = byte(line[25]) & byte(0x07);  #wideband heater pid state bits


def init(ser):
    serial_port = Serial(ser, 19200, timeout=1)
    reader = ReaderThread(serial_port, SerialReaderProtocolLine)
    reader.start()
    transport, protocol = reader.connect()
    return protocol


def getReadings(protocol):
    return protocol.DAQRawThermocouple2

def readTC(protocol, channel, table): #channel, reference table
    return

def readADC(protocol, channel): #returns zero to five volts as a float
    match channel:
        case 1:
            rawADC = protocol.DAQRawUser1
        case 2:
            rawADC = protocol.DAQRawUser2
        case 3:
            rawADC = protocol.DAQRawUser3
    if rawADC == None:
        rawADC = 0
    scaledADC = rawADC / 1638.4
    return scaledADC

def readLambda():
    return
def readThermistor():
    return
def readRPM():
    return
def readStatus():
    return
def readCounter():
    return

if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.WARNING)
    #logger.setLevel(logging.INFO)
    #logger.setLevel(logging.DEBUG)

    serial_port = Serial('/dev/ttyUSB0', 19200, timeout=1)
    reader = ReaderThread(serial_port, SerialReaderProtocolLine)
    reader.start()
    #Wait until connection is set up and return the transport and protocol instances.
    transport, protocol = reader.connect()

    while True:
        logging.warning("tick")
        print(protocol.DAQRawThermocouple1)
        time.sleep(1)