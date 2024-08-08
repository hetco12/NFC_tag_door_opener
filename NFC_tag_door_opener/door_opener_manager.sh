#!/usr/bin/env python3

import os
import time
import subprocess
from adafruit_macropad import MacroPad
import pyudev

DOOR_OPENER_PROGRAM = "/path/to/door_opener.py"
NFC_TAG_READER_PROGRAM = "/path/to/nfc_tag_reader.py"
GOOGLE_SHEETS_URL = "YOUR_GOOGLE_SHEETS_CSV_URL"
LOCAL_CSV_FILE = "/path/to/local_verification_sheet.csv"
LOG_FILE = "/path/to/door_opener_manager.log"
USB_VENDOR_ID = "1d6b"  # Replace with your USB device's vendor ID
USB_PRODUCT_ID = "0002"  # Replace with your USB device's product ID

def log_message(message):
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: {message}\n")

def reset_door_opener():
    log_message("Resetting door opener program...")
    subprocess.run(["pkill", "-f", DOOR_OPENER_PROGRAM])
    subprocess.Popen(["nohup", "python3", DOOR_OPENER_PROGRAM], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def reset_raspberry_pi():
    log_message("Resetting Raspberry Pi...")
    subprocess.run(["sudo", "reboot"])

def quit_door_opener():
    log_message("Quitting door opener program...")
    subprocess.run(["pkill", "-f", DOOR_OPENER_PROGRAM])

def open_nfc_tag_reader():
    log_message("Opening NFC tag reader program...")
    subprocess.Popen(["nohup", "python3", NFC_TAG_READER_PROGRAM], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def update_local_csv():
    log_message("Updating local CSV file...")
    subprocess.run(["wget", "-O", LOCAL_CSV_FILE, GOOGLE_SHEETS_URL])

def reset_usb_device(vendor_id, product_id):
    context = pyudev.Context()
    for device in context.list_devices(subsystem='usb', ID_VENDOR_ID=vendor_id, ID_MODEL_ID=product_id):
        if device.device_node:
            log_message(f'Resetting USB device: {device.device_node}')
            os.system(f'echo -n "{device.device_node}" > /sys/bus/usb/drivers/usb/unbind')
            time.sleep(1)
            os.system(f'echo -n "{device.device_node}" > /sys/bus/usb/drivers/usb/bind')
            log_message('Reset successful')
            return
    log_message('USB device not found')

def handle_keypad_press(key):
    if key == 0:
        reset_raspberry_pi()
        reset_door_opener()
    elif key == 1:
        quit_door_opener()
        open_nfc_tag_reader()
    elif key == 2:
        update_local_csv()
    elif key == 3:
        reset_door_opener()
    else:
        log_message(f"Unknown key pressed: {key}")

def monitor_door_opener():
    while True:
        result = subprocess.run(["pgrep", "-f", DOOR_OPENER_PROGRAM], capture_output=True, text=True)
        if not result.stdout.strip():
            log_message("Door opener program not running. Starting...")
            reset_door_opener()
        time.sleep(5)

def monitor_keypad():
    macropad = MacroPad()
    while True:
        key_event = macropad.keys.events.get()
        if key_event and key_event.pressed:
            key_number = key_event.key_number
            if key_number < 4:  # Only use the first 4 buttons
                handle_keypad_press(key_number)
        time.sleep(0.1)

if __name__ == "__main__":
    log_message("Starting door opener manager...")
    try:
        import threading
        threading.Thread(target=monitor_door_opener).start()
        threading.Thread(target=monitor_keypad).start()
    except KeyboardInterrupt:
        log_message("Door opener manager stopped.")