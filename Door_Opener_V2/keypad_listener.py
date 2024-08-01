#!/usr/bin/env python3

from adafruit_macropad import MacroPad
import time

# Initialize MacroPad
macropad = MacroPad()

while True:
    key_event = macropad.keys.events.get()
    if key_event and key_event.pressed:
        key_number = key_event.key_number
        if key_number < 4:  # Only use the first 4 buttons
            print(key_number + 1, flush=True)
    time.sleep(0.1)