#!/usr/bin/env python3

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = config['google_api']['SERVICE_ACCOUNT_FILE']
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

service = build('sheets', 'v4', credentials=creds)

# Define the Google Sheets document ID for the document you want to work with
SHEET_ID = '1EEklwyvde3Hh2Sr20asr0FuGxk4z1UmkTtgr_8Ruvjo'
RANGE_NAME = 'NFC-tags!A:B'
LOCAL_VERIFICATION_SHEET = 'local_verification_sheet.csv'

# Download the Google Sheets document as a local verification sheet
try:
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values')
    if values is not None:
        with open(LOCAL_VERIFICATION_SHEET, 'w') as f:
            for row in values:
                f.write(','.join(row) + '\n')
except Exception as e:
    # If there's an error downloading the sheet, continue with the existing local verification sheet if available
    print(f'Error downloading Google Sheets: {e}')