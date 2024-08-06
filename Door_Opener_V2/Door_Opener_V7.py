#!/usr/bin/env python3

import os
import toml
import serial
import time
import RPi.GPIO as GPIO
import board
import neopixel
import smtplib
import sys
import traceback
from adafruit_pn532.uart import PN532_UART
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Disable GPIO warnings
GPIO.setwarnings(False)

# Load settings from TOML file
config = toml.load(os.path.join(os.path.dirname(__file__), 'settings.toml'))
SENDER_EMAIL = config['email']['SENDER_EMAIL']
SENDER_PASSWORD = config['email']['SENDER_PASSWORD']
RECEIVER_EMAIL = config['email']['RECEIVER_EMAIL']

# Set up NFC reader
uart_reader = serial.Serial("/dev/ttyUSB0", baudrate=115200, timeout=0.1)
pn532 = PN532_UART(uart_reader, debug=False)

# PN532 reset function
def pn532_reset():
    try:
        pn532.reset()
        time.sleep(1)  # Wait for the reset to complete
        pn532.SAM_configuration()
    except Exception as e:
        print(f"Error during PN532 reset: {e}")

# Set up relay
RELAY_PIN = 24
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

# Set up NeoPixel strip with brightness
NUM_PIXELS = 7
PIXEL_PIN = board.D18
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=0.15, auto_write=False)

# Define colors
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)

# Function to set NeoPixel color and display
def set_neopixel_color(color):
    pixels.fill(color)
    pixels.show()

# Function to send an email notification
def send_email(subject, body):
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        message = f'Subject: {subject}\n\n{body}'
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, message)
        server.quit()
    except Exception as e:
        print(f'Failed to send email: {e}')

# Function to handle unhandled exceptions and send an email notification
def handle_exception(exc_type, exc_value, exc_traceback):
    error_message = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    send_email(f'Error in {DOOR_LOCATION} Door Opener AI', f'The {DOOR_LOCATION} Door Opener AI encountered an unhandled exception:\n\n{error_message}')

# Send email notification on program start and Raspberry Pi reboot
send_email(f'{DOOR_LOCATION} Door Opener AI Started', f'The {DOOR_LOCATION} Door Opener AI program has started running.')
# Set the global exception handler
sys.excepthook = handle_exception

# Define the local verification sheet file path
LOCAL_VERIFICATION_SHEET = 'local_verification_sheet.csv'

# Main program loop for NFC tag detection and door control
print('Waiting for NFC tag...')
set_neopixel_color(BLUE)
nfc_tag_detected = False  # Flag to track if NFC tag was detected
nfc_issue_detected = False  # Flag to track if there's an NFC issue

while True:
    try:
        for attempt in range(3):  # Try to read the NFC tag up to 3 times
            uid = pn532.read_passive_target(timeout=1)
            if uid is not None:
                break
            time.sleep(0.5)  # Wait a bit before retrying
        else:
            #print("Failed to read NFC tag after several attempts.")
            continue

        # NFC tag detected
        if not nfc_tag_detected:
            print('Tag detected')
            nfc_tag_detected = True
            set_neopixel_color(BLUE)

        uid = ''.join(format(x, '02x') for x in uid)
        print(f'Tag with UID {uid} detected')

        # Check if tag is enrolled
        with open(LOCAL_VERIFICATION_SHEET, 'r') as f:
            local_verification_data = f.readlines()
        local_verification_data = [line.strip().split(',') for line in local_verification_data]
        uids, enrolled = zip(*local_verification_data)

        if uid not in uids:
            print('Tag not enrolled')
            set_neopixel_color(RED)
            time.sleep(2)
            set_neopixel_color(BLUE)
            continue  # Tag not enrolled, continue scanning

        index = uids.index(uid)
        if enrolled[index] == 'Y':
            print('Access granted')
            set_neopixel_color(GREEN)

            # Trigger relay
            GPIO.output(RELAY_PIN, GPIO.HIGH)
            time.sleep(5)  # Relay active for 5 seconds
            GPIO.output(RELAY_PIN, GPIO.LOW)

            set_neopixel_color(BLUE)
        else:
            print('Access denied')
            set_neopixel_color(RED)
            time.sleep(2)
            set_neopixel_color(BLUE)
    # Proceed if uid is not None...
    except IndexError as e:
        # Handle the specific 'index out of range' error gracefully
        print("Encountered an IndexError, possibly due to unexpected NFC data format.")
        # Consider adding a mechanism to log or further examine the erroneous data
        continue  # Skip this loop iteration and try reading the tag again
    except RuntimeError as e:
        if 'did not receive expected ACK from PN532' in str(e):
            print('Did not receive expected ACK from NFC tag. Please try again.')
            set_neopixel_color(RED)
            nfc_issue_detected = True
            pn532_reset()
        elif 'Did not receive expected ACK from PN532!' in str(e):
            print('Did not receive expected ACK from NFC tag. Please try again.')
            set_neopixel_color(RED)
            nfc_issue_detected = True
            pn532_reset()
        elif 'Response checksum did not match expected value' in str(e):
            print('Move the tag closer to the NFC reader and try again.')
            set_neopixel_color(RED)
            nfc_issue_detected = True
            pn532_reset()
        elif 'Response length checksum did not match length!' in str(e):
            print('Checksum error. Resetting NFC reader...')
            set_neopixel_color(RED)
            nfc_issue_detected = True
            pn532_reset()
        else:
            # Send email notification about the error
            error_message = f'An error occurred in the NFC Reader:\n\n{str(e)}'
            send_email('Error in NFC Reader', error_message)
            raise  # Re-raise other RuntimeError exceptions
        print(f'RuntimeError: {e}')
        set_neopixel_color(RED)
        nfc_issue_detected = True
        pn532_reset()  # Attempt to reset the PN532 module
        time.sleep(1)  # Wait a bit before continuing
        set_neopixel_color(BLUE)
        nfc_issue_detected = False
        continue
    # Add a brief delay before next loop iteration
    time.sleep(0.5)

# End of script
