#!/usr/bin/python
__author__ = 'GabrielSoares'

import RPi.GPIO as GPIO
import MySQLdb
import sys
import subprocess
import re
import time
from prettytable import PrettyTable

'''
Program execution start:
- need to set up GPIOs
- need to get into while(1) loop which will poll the state of the push-button
- when pushbutton is detected (and debounced) determine whether we need to call function to check in or checkout book
- 
'''

def check_book(check_status):
    acquiredNFC = False
    numLoops = 0
    nfc_list = nfc_ids = ""
    regex = re.compile('NFCID1\):\s*([^\n\r]*)')
    
    while acquiredNFC == False and numLoops < 10:
        #call cmd that scans NFC reader
        nfc_list = subprocess.check_output("nfc-list")
    
        if "NFCID1" in nfc_list:
            #run regular expression on nfc_list
            nfc_ids = regex.findall(nfc_list)
    
            #make sure we detect a single valid NFC id
            if len(nfc_ids) == 0:
                return -1
            elif len(nfc_ids) > 1:
                return -1
            else:
                acquiredNFC = True  #exit inner loop
    
        #didn't find tag on NFC reader, sleep before we try again
        else:
            time.sleep(1)
            numLoops += 1

    #exit while loop because it timed out
    if acquiredNFC == False and numLoops == 10:
        return -1
    
    #convert NFC Id string to hex array
    hexId = bytearray.fromhex(nfc_ids[0].replace(" ", ""))
    #convert hex array to a 4-byte number
    RFID = int(hexId[0] << 24 | hexId[1] << 16 | hexId[2] << 8 | hexId[3])

    #connect to the database
    host = global DB_host
    user = global DB_user
    passwd = global DB_passwd
    name = global DB_name
    table = global DB_table

    try:
        db = MySQLdb.connect(host, user, passwd, name)
        cursor = db.cursor()
    except:
        db.close()
        return -1

    #make sure that the NFC id exists in the database
    ret = cursor.execute("SELECT * FROM %s WHERE nfc_id=%s;", (table, str(RFID)))
    if not ret:
        cursor.close()
        db.close()
        return -1

    rows = cursor.fetchall()

    #check that there aren't multiple entries with the same NFC id (shouldn't happen)
    if len(rows) > 1:
        cursor.close()
        db.close()
        return -1
    #there is a single row element in table with this NFC id (proceed)
    else:
#         #display the row for the book to user and prompt for confirmation
#         table = PrettyTable(["row", "NFC Id", "Book Title", "Book Author", "Status", "Date", "Employee"])
#         table.align["Book Title"] = "l"     #left align
#         table.align["Book Author"] = "l"    #left align
#         for i in rows:
#             table.add_row(i)
#         print table
        
        #get the status field for this book
        ret = cursor.execute("SELECT status FROM %s WHERE nfc_id=%s;", (table, str(RFID)))
        rows = [item[0] for item in cursor.fetchall()]

        #check that the status of the field is not already the same as check_status
        if rows[0] == check_status:
            cursor.close()
            db.close()
            return -1
        #status field is !check_status -> we can change it to check_status and set the date field
        else:
            try:
                ret = cursor.execute("UPDATE %s SET status=%s, date=%s WHERE nfc_id=%s;",
                                    (table, str(check_status), time.strftime('%Y-%m-%d'), str(RFID)))
            except:
                cursor.close()
                db.close()
                return -1
        #SUCCESS!
        db.commit()
        return 1


print "******************************************************************"
print "Starting the DE library management system"
print "Press <Ctrl+C> to exit"
print "******************************************************************"

#GPIO defines (use BCM numbers)
GPIO_pushbutton_checkout = 18   #pushbutton to check out a book
GPIO_pushbutton_checkin = 23    #pushbutton to check in a book
GPIO_led_error = 4              #red LED
GPIO_led_waiting = 25           #yellow LED
GPIO_led_success = 22           #green LED

#DATABASE defines (SET THESE ACCORDING TO HOW YOU SET UP YOUR DATABASE)
DB_host = "localhost"
DB_user = "user"
DB_passwd = "password"
DB_name = "database_name"
DB_table = "booklist"

'''
Start by setting up the GPIOs
'''
#set to BCM naming scheme
GPIO.setmode(GPIO.BCM)

#set up PUSHBUTTONS
GPIO.setup(GPIO_pushbutton_checkout, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(GPIO_pushbutton_checkin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#set up LEDs
GPIO.setup(GPIO_led_error, GPIO.OUT)
GPIO.setup(GPIO_led_waiting, GPIO.OUT)
GPIO.setup(GPIO_led_success, GPIO.OUT)

'''
Enter infinite loop which polls the buttons and looks for keypresses.
One button used to check in books, another used to check out books.
'''
try:
    start_time = 0  #keeps track of the time when a button is pressed (used to turn off LEDs)
    
    #enter infinite loop
    while True:
        
        #check if 30s. have passed since last button press and turn off LEDs
        if start_time != 0 and ((time.time() - start_time) > 30):
            start_time = 0
            GPIO.output(GPIO_led_waiting, False)
            GPIO.output(GPIO_led_error, False)
            GPIO.output(GPIO_led_success, False)
        
        #get the state of the buttons
        input_state_check_out = GPIO.input(GPIO_pushbutton_checkout)
        input_state_check_in = GPIO.input(GPIO_pushbutton_checkin)
        
        #check if any of the buttons were pressed
        if input_state_check_out == False or input_state_check_in == False:
            #start a counter which after a while will turn off LEDs (30s)
            start_time = time.time()
            
            #turn on yellow LED and turn off all others
            GPIO.output(GPIO_led_waiting, True)
            GPIO.output(GPIO_led_error, False)
            GPIO.output(GPIO_led_success, False)
            
            #make sure both buttons weren't pressed at the same time
            if input_state_check_out == False and input_state_check_in == False:
                continue
            
            #check out button was pressed
            elif input_state_check_out == False:
#                 print "Checking Out..."
                ret = check_book(1) #call CHECK OUT function
                
            #check in button was pressed
            elif input_state_check_in == False:
#                 print "Checking In..."
                ret = check_book(0) #call CHECK IN function
                
            #turn off yellow LED
            GPIO.output(GPIO_led_waiting, False)
            if(ret < 0):
#                 print "Error"
                #turn on red LED
                GPIO.output(GPIO_led_error, True)
            else:
#                 print "Success!"
                #turn on green LED
                GPIO.output(GPIO_led_success, True)
                
            time.sleep(0.2)
            
            
except:
    GPIO.output(GPIO_led_waiting, False)
    GPIO.output(GPIO_led_error, False)
    GPIO.output(GPIO_led_success, False)
    GPIO.cleanup()
    sys.exit()
