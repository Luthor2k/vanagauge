#!/bin/sh
export PATH="/home/arthur/.local/bin:$PATH"

. ./env/bin/activate

python3 /home/arthur/vanagauge/vanplot.py

sleep 1
