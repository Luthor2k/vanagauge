#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
export DISPLAY=:0

. $HOME/vanagauge/env/bin/activate

python3 $HOME/vanagauge/tkvanplot2.py
