import tkinter as tk

from serial import Serial
from serial.threaded import ReaderThread, Protocol, LineReader

import csv
from time import gmtime, strftime

class SerialReaderProtocolLine(LineReader):
    global csv_name
    tk_listener = None
    #TERMINATOR = b'\x5a\xa5' #tech edge
    TERMINATOR = b'$GPRMC'  #gps dummy
    csv_name = "./datalog_" + strftime("%d%b%Y%H%M%S") + ".csv"

    def connection_made(self, transport):
        """Called when reader thread is started"""
        if self.tk_listener is None:
            raise Exception("tk_listener must be set before connecting to the socket!")
        super().connection_made(transport)
        print("Connected, ready to receive data...")

    def handle_packet(self, line):
        global csv_name
        """New line waiting to be processed"""
        # Execute our callback in tk
        print(line)
        print(line[3:4])
        line_ascii = line.decode("ascii")
        line_list = line_ascii.split("\n")
        with open(csv_name, 'a') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(line_list)
        self.tk_listener.after(0, self.tk_listener.on_data, line)


class MainFrame(tk.Frame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.listbox = tk.Listbox(self)
        self.listbox.pack()
        self.pack()

    def on_data(self, data):
        #print("Called from tk Thread:", data)
        self.listbox.insert(tk.END, bytes(data))


if __name__ == '__main__':
    app = tk.Tk()

    main_frame = MainFrame()
    # Set listener to our reader
    SerialReaderProtocolLine.tk_listener = main_frame
    # Initiate serial port
    serial_port = Serial('/dev/ttyACM0', 19200, timeout=1)
    # Initiate ReaderThread
    reader = ReaderThread(serial_port, SerialReaderProtocolLine)
    # Start reader
    reader.start()

    app.mainloop()