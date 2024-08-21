Dash gauge for visualizing data from a Tech Edge wideband DAQ.

![desktop test photo](https://github.com/Luthor2k/vanagauge/blob/master/dash-desktop.jpg)

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

BOM:

Use the Pi LCD
https://www.raspberrypi.com/products/raspberry-pi-touch-display/

Use a Minibox supply
https://www.mini-box.com/M2-ATX-160w-Intelligent-Automotive-DC-DC-Power-Supply?sc=8&category=1544
