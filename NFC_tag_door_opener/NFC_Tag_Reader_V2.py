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

# Google Sheets API setup
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)

# NFC reader setup
uart = serial.Serial('/dev/ttyUSB0', baudrate=115200, timeout=0.5)
pn532 = PN532_UART(uart, debug=False)
pn532.SAM_configuration()

def read_nfc_tag():
    retries = 0
    MAX_RETRIES = 3
    RETRY_DELAY = 0.3
    while retries < MAX_RETRIES:
        try:
            uid = pn532.read_passive_target(timeout=0.5)
            if uid is not None:
                return uid
        except RuntimeError as e:
            print('Error reading NFC tag: ', e)
        retries += 1
        time.sleep(RETRY_DELAY)
    return None

def find_row_by_uid(uid, values):
    for i, row in enumerate(values):
        if row[0] == uid:
            return i + 1  # Spreadsheet rows are 1-indexed
    return None

def update_user_info(sheet_id, uid):
    range_name = 'Sheet1!A:E'
    result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=range_name).execute()
    values = result.get('values', [])
    
    row_number = find_row_by_uid(uid, values)
    if row_number:
        row_data = values[row_number - 1]
        if row_data[1] == 'Y':
            if len(row_data) >= 5 and all(row_data[2:5]):  # Checks if C, D, E columns are filled
                user_decision = input("The information has been filled out, would you like to change it? Y/N: ").strip().upper()
                if user_decision != 'Y':
                    print("Update canceled by the user.")
                    return
            
            last_name = input("Enter Last Name: ")
            first_name = input("Enter First Name: ")
            child = input("Enter Child: ")
            body = {'values': [[uid, 'Y', last_name, first_name, child]]}
            update_range = f'Sheet1!A{row_number}:E{row_number}'
            service.spreadsheets().values().update(
                spreadsheetId=SHEET_ID, range=update_range,
                valueInputOption='USER_ENTERED', body=body).execute()
            print("Information updated successfully.")
        else:
            print("This tag is not enrolled. No update performed.")
    else:
        print("UID not found in Google Sheets.")

print('Waiting for NFC tag...')
while True:
    uid = read_nfc_tag()
    if uid is not None:
        uid_hex = ''.join(format(x, '02x') for x in uid)
        print(f'Tag with UID {uid_hex} detected')
        update_user_info(SHEET_ID, uid_hex)
    else:
        print('Failed to read NFC tag')
    time.sleep(1)
