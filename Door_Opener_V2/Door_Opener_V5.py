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
SERVICE_ACCOUNT_FILE = config['google_api']['SERVICE_ACCOUNT_FILE']
SHEET_ID = config['google_api']['SHEET_ID']
SENDER_EMAIL = config['email']['SENDER_EMAIL']
SENDER_PASSWORD = config['email']['SENDER_PASSWORD']
RECEIVER_EMAIL = config['email']['RECEIVER_EMAIL']

# Define colors
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
OFF = (0, 0, 0)  # Off color for NeoPixels

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
    set_neopixel_color(OFF)  # Turn off NeoPixels
    send_email('Error in Door Opener AI', f'The Door Opener AI encountered an unhandled exception:\n\n{error_message}')
    sys.exit(1)  # Exit the program with an error code

# Function to set NeoPixel color and display
def set_neopixel_color(color):
    pixels.fill(color)
    pixels.show()

def setup():
    global pn532, pixels, service

    # Set up Google Sheets API
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    RANGE_NAME = 'Sheet1!A:B'
    LOCAL_VERIFICATION_SHEET = 'local_verification_sheet.csv'

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

    # Send email notification on program start and Raspberry Pi reboot
    send_email('Door Opener AI Started', 'The Door Opener AI program has started running.')

    # Set the global exception handler
    sys.excepthook = handle_exception

    # Download the Google Sheets document as a local verification sheet
    try:
        result = service.spreadsheets().values().get(spreadsheetId=SHEET_ID, range=RANGE_NAME).execute()
        values = result.get('values', [])
        with open(LOCAL_VERIFICATION_SHEET, 'w') as f:
            for row in values:
                f.write(','.join(row) + '\n')
    except Exception as e:
        print(f'Error downloading Google Sheets: {e}')

def main_program():
    # Main program loop
    set_neopixel_color(BLUE)  # Reset NeoPixels to blue
    print('Waiting for NFC tag...')
    nfc_tag_detected = False  # Flag to track if NFC tag was detected
    nfc_issue_detected = False  # Flag to track if there's an NFC issue

    while True:
        try:
            pass
        except RuntimeError as e:
            if 'did not receive expected ACK from PN532' in str(e):
                print('Did not receive expected ACK from PN532. Please try again.')
                set_neopixel_color(RED)
                nfc_issue_detected = True
                pn532_reset()
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
                set_neopixel_color(OFF)  # Turn off NeoPixels
                sys.exit(1)  # Exit the program with an error code

            # Check if there's an NFC issue and reset the strip color after a while
            if nfc_issue_detected:
                pn532_reset()
                time.sleep(0.5)
                set_neopixel_color(BLUE)  # Reset NeoPixels to blue
                nfc_issue_detected = False

    # Add a brief delay before the next loop iteration
    time.sleep(0.1)

if __name__ == "__main__":
    setup()
    while True:
        try:
            main_program()
        except Exception as e:
            # Handle unexpected exceptions
            error_message = ''.join(traceback.format_exception_only(type(e), e))
            detailed_error_message = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            print(f"Unexpected error: {error_message}")
            send_email('Unexpected Error in Door Opener AI', f'An unexpected error occurred:\n\n{detailed_error_message}')
            set_neopixel_color(OFF)  # Turn off NeoPixels
            sys.exit(1)  # Exit the program with an error code
