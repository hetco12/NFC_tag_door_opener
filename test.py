"""
This example shows connecting to the PN532 using a UART connection with an FTDI cable.
After initialization, try waving various 13.56MHz RFID cards over it!
"""

import serial
from adafruit_pn532.uart import PN532_UART

# Create a serial connection over the FTDI cable
# Replace '/dev/ttyUSB0' with the correct serial port if different
uart = serial.Serial('/dev/ttyUSB0', baudrate=115200, timeout=0.1)

# Initialize the PN532 using the UART connection
pn532 = PN532_UART(uart, debug=False)

# Get the firmware version to check if the PN532 is connected
ic, ver, rev, support = pn532.firmware_version
print("Found PN532 with firmware version: {0}.{1}".format(ver, rev))

# Configure PN532 to communicate with MiFare cards
pn532.SAM_configuration()

print("Waiting for RFID/NFC card...")
while True:
    # Check if a card is available to read
    uid = pn532.read_passive_target(timeout=0.5)
    print(".", end="")
    
    # Try again if no card is available
    if uid is None:
        continue

    # Print the UID of the detected card
    print("\nFound card with UID:", [hex(i) for i in uid])
