#!/bin/bash

#path to the python script
SCRIPT_PATH="/home/hunter/NFC_tag_door_opener/Door_Opener_V2/Door_Opener_V7.py"
LOG_FILE="/home/hunter/door_opener.log"

#open a new terminal window and run the python script
/usr/bin/lxterminal -e "sudo /usr/bin/python3 $SCRIPT_PATH" >> $LOG_FILE 2>&1

