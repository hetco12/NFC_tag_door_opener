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

# Load settings from TOML file
config = toml.load(os.path.join(os.path.dirname(__file__), 'settings.toml'))
SERVICE_ACCOUNT_FILE = config['google_api']['SERVICE_ACCOUNT_FILE']
SHEET_ID = config['google_api']['SHEET_ID']

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

service = build('sheets', 'v4', credentials=creds)

# Define the Google Sheets document ID for the document you want to work with
RANGE_NAME = 'Sheet1!A:B'
LOCAL_VERIFICATION_SHEET = 'local_verification_sheet.csv'

# Download the Google Sheets document as a local verification sheet
try:
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values')
    if values is not None:
        with open(LOCAL_VERIFICATION_SHEET, 'w') as f:
            for row in values:
                f.write(','.join(row) + '\n')
    print("Loading Done. New Google Sheets Document Acquired.")
except Exception as e:
    print(f'Error downloading Google Sheets: {e}')
