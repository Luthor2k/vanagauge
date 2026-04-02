Dash gauge for visualizing data from a Tech Edge wideband DAQ.

![desktop test photo](https://github.com/Luthor2k/vanagauge/blob/master/benchtest.jpg)
![rendering](https://github.com/Luthor2k/vanagauge/blob/master/render.png)

Setup:
create a venv and install requirements.txt
```
cd vanagauge && python -m venv env && source env/bin/activate && pip install -r requirements.txt
```
Raspbian has moved to Wayfire from X, add to ~/.config/wayfire.ini:
```
[autostart]
dashtaskid = $HOME/vanagauge/dashServiceStart.sh
```
Graceful shutdown on pin toggle:
```
sudo cp shutdownPin17.service /etc/systemd/system/shutdownPin17.service
sudo systemctl enable shutdownPin17.service && sudo systemctl daemon-reload && sudo systemctl start shutdownPin17.service
```

The lastest version of Raspbian is using Wayland instead of X. To hide the cursor:

https://raspberrypi.stackexchange.com/questions/145382/remove-hide-mouse-cursor-when-idle-on-rasbperry-pi-os-bookworm

Custom spash screens:

sudo cp splash.png /usr/share/plymouth/themes/pix/splash.png

sudo plymouth-set-default-theme --rebuild-initrd pix


BOM:

Tech Edge 2Y2 Wideband O2 and DAC module
https://wbo2.com/2y/default.htm

The OE Pi LCD
https://www.raspberrypi.com/products/raspberry-pi-touch-display/

A Minibox DCDC supply - overkill at 200W but graceful power down is a desirable feature
https://www.mini-box.com/M2-ATX-160w-Intelligent-Automotive-DC-DC-Power-Supply?sc=8&category=1544

Sensors:

3x type K thermocouples; manifold, pre-cat, post-cat

1x 10k linear potentiomater at the fuel pump throttle pivot

1x 30PSI Pressure Transducer at the intake manifold

1x Hella air temperature sensor (HELLA 358058151) aka Bosch Temperature Sensor NTC M12-L, Order number 0280.130.039
