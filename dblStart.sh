#!/bin/sh
export PATH="/home/arthur/.local/bin:$PATH"

. ./env/bin/activate

python3 /home/arthur/vanagauge/soundplot.py

sleep 1
