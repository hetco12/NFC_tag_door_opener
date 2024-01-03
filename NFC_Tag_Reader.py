import toml
from google.oauth2 import service_account
from googleapiclient.discovery import build
import time
import serial
from adafruit_pn532.uart import PN532_UART

# Load settings from TOML file
config = toml.load('settings.toml')
SERVICE_ACCOUNT_FILE = config['google_api']['SERVICE_ACCOUNT_FILE']
SHEET_ID = config['google_api']['SHEET_ID']

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)

# Set up NFC reader for UART connection
# Replace '/dev/ttyUSB0' with the correct serial port if different
uart = serial.Serial('/dev/ttyUSB0', baudrate=115200, timeout=0.1)
pn532 = PN532_UART(uart, debug=False)

# Configure PN532 to communicate with MiFare cards
pn532.SAM_configuration()

# Retry parameters
MAX_RETRIES = 3
RETRY_DELAY = 0.1

def read_nfc_tag():
    retries = 0
    while retries < MAX_RETRIES:
        try:
            uid = pn532.read_passive_target(timeout=0.5)
            if uid is not None:
                return uid
        except RuntimeError as e:
            if 'did not receive expected ACK from PN532' in str(e):
                print('Did not receive expected ACK from NFC tag. Retrying...')
            else:
                raise e
        retries += 1
        time.sleep(RETRY_DELAY)
    return None

# Wait for NFC tag to be presented
print('Waiting for NFC tag...')
while True:
    uid = read_nfc_tag()
    if uid is None:
        print('Failed to read NFC tag after multiple attempts')
        continue

    uid = ''.join(format(x, '02x') for x in uid)
    print(f'Tag with UID {uid} detected')

    # Check if tag has been scanned before
    range_name = 'Sheet1!A:B'
    result = service.spreadsheets().values().get(spreadsheetId=SHEET_ID, range=range_name).execute()
    values = result.get('values', [])
    enrolled = ['Y' if row[1] == 'Y' else 'N' for row in values]
    uids = [row[0] for row in values]
    if uid in uids:
        print('I have scanned this tag already')
    else:
        # Update Google Sheets with new record
        values = [[uid, 'Y']]
        body = {
            'values': values
        }
        result = service.spreadsheets().values().append(spreadsheetId=SHEET_ID, range=range_name, valueInputOption='USER_ENTERED', insertDataOption='INSERT_ROWS', body=body).execute()
        print('Record added to Google Sheets')

    # Wait a bit before looking for another NFC tag
    time.sleep(1)

