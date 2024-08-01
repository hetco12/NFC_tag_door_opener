#!/bin/bash

DOOR_OPENER_PROGRAM="/path/to/door_opener.py"
NFC_TAG_READER_PROGRAM="/path/to/nfc_tag_reader.py"
GOOGLE_SHEETS_URL="YOUR_GOOGLE_SHEETS_CSV_URL"
LOCAL_CSV_FILE="/path/to/local_verification_sheet.csv"
LOG_FILE="/path/to/door_opener_manager.log"
KEYPAD_SCRIPT="/path/to/keypad_listener.py"

function reset_door_opener {
    echo "$(date): Resetting door opener program..." >> $LOG_FILE
    pkill -f $DOOR_OPENER_PROGRAM
    nohup python3 $DOOR_OPENER_PROGRAM >> $LOG_FILE 2>&1 &
}

function reset_raspberry_pi {
    echo "$(date): Resetting Raspberry Pi..." >> $LOG_FILE
    sudo reboot
}

function quit_door_opener {
    echo "$(date): Quitting door opener program..." >> $LOG_FILE
    pkill -f $DOOR_OPENER_PROGRAM
}

function open_nfc_tag_reader {
    echo "$(date): Opening NFC tag reader program..." >> $LOG_FILE
    nohup python3 $NFC_TAG_READER_PROGRAM >> $LOG_FILE 2>&1 &
}

function update_local_csv {
    echo "$(date): Updating local CSV file..." >> $LOG_FILE
    wget -O $LOCAL_CSV_FILE $GOOGLE_SHEETS_URL
}

function handle_keypad_press {
    KEY=$1
    case $KEY in
        1)
            reset_raspberry_pi
            ;;
        2)
            reset_door_opener
            ;;
        3)
            quit_door_opener
            ;;
        4)
            open_nfc_tag_reader
            ;;
        5)
            update_local_csv
            ;;
        *)
            echo "$(date): Unknown key pressed: $KEY" >> $LOG_FILE
            ;;
    esac
}

# Monitor door opener program and restart if it crashes
while true; do
    if ! pgrep -f $DOOR_OPENER_PROGRAM > /dev/null; then
        echo "$(date): Door opener program not running. Starting..." >> $LOG_FILE
        reset_door_opener
    fi
    sleep 5
done &
DOOR_OPENER_PID=$!

# Monitor keypad presses
python3 $KEYPAD_SCRIPT | while read -r KEY; do
    handle_keypad_press $KEY
done &

wait $DOOR_OPENER_PID