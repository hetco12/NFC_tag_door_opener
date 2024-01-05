#!/usr/bin/env python3
import os
import serial
import time
import RPi.GPIO as GPIO
import board
import neopixel
import toml
from adafruit_pn532.uart import PN532_UART
from google.oauth2 import service_account
from googleapiclient.discovery import build
import smtplib
import sys
import traceback


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
    pn532.reset()
    pn532.SAM_configuration()

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
    send_email('Error in Door Opener AI', f'The Door Opener AI encountered an unhandled exception:\n\n{error_message}')

# Send email notification on program start and Raspberry Pi reboot
send_email('Door Opener AI Started', 'The Door Opener AI program has started running.')

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
        uid = None
        try:
            uid = pn532.read_passive_target(timeout=0.5)
            time.sleep(0.1)  # Add a 0.1-second delay between readings
        except RuntimeError as e:
            if 'Did not receive expected ACK from PN532!' in str(e):
                print('Did not receive expected ACK from NFC tag. Retrying...')
                continue
            else:
                raise

        # Handle NFC tag detection
        if uid is not None:
            if not nfc_tag_detected:
                print('Tag detected')
                nfc_tag_detected = True
                set_neopixel_color(BLUE)  # Set strip to blue on tag detection

            uid = ''.join(format(x, '02x') for x in uid)
            print(f'Tag with UID {uid} detected')

            # Check if tag is enrolled using local verification sheet
            with open(LOCAL_VERIFICATION_SHEET, 'r') as f:
                local_verification_data = f.readlines()
            local_verification_data = [line.strip().split(',') for line in local_verification_data]
            uids, enrolled = zip(*local_verification_data)
            if uid not in uids:
                print('This tag is not enrolled')
                set_neopixel_color(RED)
                time.sleep(2)
                set_neopixel_color(BLUE)
            else:
                index = uids.index(uid)
                if enrolled[index] == 'Y':
                    print('Access granted')
                    set_neopixel_color(GREEN)  # Set strip to green when access is granted

                    # Open relay
                    GPIO.output(RELAY_PIN, GPIO.HIGH)
                    time.sleep(5)
                    # Close relay
                    GPIO.output(RELAY_PIN, GPIO.LOW)

                    set_neopixel_color(BLUE)  # Set strip back to blue after relay operation
                else:
                    print('Access denied')
                    set_neopixel_color(RED)
                    time.sleep(2)
                    set_neopixel_color(BLUE)
        else:
            # No NFC tag detected
            nfc_tag_detected = False
            set_neopixel_color(BLUE)  # Set strip back to blue

    except RuntimeError as e:
        if 'did not receive expected ACK from PN532' in str(e):
            print('Did not receive expected ACK from NFC tag. Please try again.')
            set_neopixel

