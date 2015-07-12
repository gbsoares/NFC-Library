#!/usr/bin/python
__author__ = 'GabrielSoares'

import RPi.GPIO as GPIO
import MySQLdb
import sys
import subprocess
import re
import time
import datetime
import httplib, urllib

'''
******************************************************************
FUNCTION DEFINITIONS:
******************************************************************
'''
        
def pushStatisticsToServer(nfc_id, check_in_or_out):
    '''
    @summary: Function gathers statistics about the library and pushes the data to data.sparkfun.com/deteamlibrary
    @param nfc_id: the nfc_id of the book we just processed
    @param check_in_or_out: 1 = checked out; 0 = checked in
    '''
    server = "data.sparkfun.com"
    publicKey = "PUBLIC_KEY_VALUE"
    fields = ["last_in","last_out","most_read","num_in","num_out"]
    data = {} #data fields which will be populated to send to the data stream site
    
    #connect to the database
    try:
        db = MySQLdb.connect('localhost', 'USERNAME', 'PASSWORD', 'DATABASE_NAME')
        cursor = db.cursor()
    except:
        db.close()
        return
    
    #last book checked in
    cursor.execute("SELECT last_in FROM statistics WHERE row='1';")
    last_in_nfcid = [(item[0]) for item in cursor.fetchall()]
    cursor.execute("SELECT book_title, book_author FROM booklist WHERE nfc_id=%s;", (str(last_in_nfcid[0])))
    last_in = [(item[0], item[1]) for item in cursor.fetchall()]
    data[fields[0]] = last_in[0][0] + " - " + last_in[0][1]
    
    #last book checked out
    cursor.execute("SELECT last_out FROM statistics WHERE row='1';")
    last_out_nfcid = [(item[0]) for item in cursor.fetchall()]
    cursor.execute("SELECT book_title, book_author FROM booklist WHERE nfc_id=%s;", (str(last_out_nfcid[0])))
    last_out = [(item[0], item[1]) for item in cursor.fetchall()]
    data[fields[1]] = last_out[0][0] + " - " + last_out[0][1]
    
    #most read book
    cursor.execute("SELECT MAX(num_check_out) as num_check_out, book_title, book_author, nfc_id FROM booklist GROUP BY book_title, book_author ORDER BY num_check_out DESC;")
    rows = [(item[0], item[1], item[2], item[3]) for item in cursor.fetchall()]
    most_read_nfcid = rows[0][3]
    most_read_book = rows[0][1] + " - " + rows[0][2]
    data[fields[2]] = most_read_book
    
    #number of books checked out
    cursor.execute("SELECT SUM(status) FROM booklist;")
    rows = [(item[0]) for item in cursor.fetchall()]
    num_books_checked_out = rows[0]
    data[fields[4]] = str(num_books_checked_out)
    
    #number of books checked in
    cursor.execute("SELECT COUNT(*) FROM booklist;")
    rows = [(item[0]) for item in cursor.fetchall()]
    num_books_checked_in = rows[0]-num_books_checked_out
    data[fields[3]] = str(num_books_checked_in)
    
    # Next, we need to encode that data into a url format:
    params = urllib.urlencode(data)
    
    # Now we need to set up our headers:
    headers = {} # start with an empty set
    # These are static, should be there every time:
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    headers["Connection"] = "close"
    headers["Content-Length"] = len(params) # length of data
    headers["Phant-Private-Key"] = privateKey # private key header
    
    # Now we initiate a connection, and post the data
    c = httplib.HTTPConnection(server)
    # Here's the magic, our reqeust format is POST, we want
    # to send the data to data.sparkfun.com/input/PUBLIC_KEY.txt
    # and include both our data (params) and headers
    c.request("POST", "/input/" + publicKey + ".txt", params, headers)

    #update remaining fields in statistics table
    cursor.execute("UPDATE statistics SET num_in=%s, num_out=%s, most_read=%s WHERE row='1';",
                   (str(num_books_checked_in), str(num_books_checked_out), str(most_read_nfcid)))
    db.commit()
    cursor.close()
    db.close()
    
    
def check_book(check_status):
    '''
    @summary: Function scans for NFC tags for 10 seconds. If it finds a tag, it connects to database and updates the required fields.
    @param check_status: 1 = check out; 0 = check in
    '''
    acquiredNFC = False
    numLoops = 0
    nfc_list = nfc_ids = ""
    regex = re.compile('NFCID1\):\s*([^\n\r]*)')
    
    #scan for NFC tags by calling nfc-list subprocess...
    while acquiredNFC == False and numLoops < 10:
        #call cmd that scans NFC reader
        nfc_list = subprocess.check_output("nfc-list")
    
        #check if string "NFCID1" is present in the subprocess output
        if "NFCID1" in nfc_list:
            #use regular expression on nfc_list
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
    NFCID = int(hexId[0] << 24 | hexId[1] << 16 | hexId[2] << 8 | hexId[3])

    #connect to the database
    try:
        db = MySQLdb.connect('localhost', 'USERNAME', 'PASSWORD', 'DATABASE_NAME')
        cursor = db.cursor()
    except:
        db.close()
        return -1

    #make sure that the NFC id exists in the database
    ret = cursor.execute("SELECT * FROM booklist WHERE nfc_id=%s;", (str(NFCID)))
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
    #there is a single row element in table with this NFC id - proceed
    else:      
        #get the status, date, and num_check_out fields for this book
        ret = cursor.execute("SELECT status, date, num_check_out FROM booklist WHERE nfc_id=%s;", (str(NFCID)))
        rows = [(item[0], item[1], item[2]) for item in cursor.fetchall()]
        db_status = rows[0][0]
        db_date = rows[0][1]
        num_check_out = rows[0][2]
        
        #check that the db_status of the book is not already the same as check_status
        if db_status == check_status:
            cursor.close()
            db.close()
            return -1
        #db_status field is not equal to check_status -> we can change it to check_status and set the other fields
        else:
            try:
                #check if the book checked out more than 1 day ago... If user is checking in a book that was checked out
                #more than 1 day ago, I want to increment the field that keeps track the number of times the book was checked out...
                delta_days = (datetime.date.today() - db_date).days
                if db_status == 1 and check_status == 0 and delta_days > 0: #book is checked out (more than 1 day) and we are checking back in...
                        num_check_out += 1
                
                ret = cursor.execute("UPDATE booklist SET status=%s, date=%s, num_check_out=%s WHERE nfc_id=%s;",
                                    (str(check_status), time.strftime('%Y-%m-%d'), str(num_check_out), str(NFCID)))
            except:
                cursor.close()
                db.close()
                return -1
            
        if check_status == 1:
            ret = cursor.execute("UPDATE statistics SET last_out=%s, timestamp=%s WHERE row='1';",
                                    (str(NFCID), time.strftime('%Y-%m-%d %H:%M:%S')))
        else:
            ret = cursor.execute("UPDATE statistics SET last_in=%s, timestamp=%s WHERE row='1';",
                                    (str(NFCID), time.strftime('%Y-%m-%d %H:%M:%S')))
        
        #SUCCESS! Commit changes to the database
        db.commit()
        cursor.close()
        db.close()
        pushStatisticsToServer(NFCID, check_status)
        return 1

        
def getIP():
    '''
    @summary: runs "ifconfig eth0" command and parses output to retrieve the Raspberry Pi's IP address.
    The IP address is converted to decimal representation to make it easier to display using LEDs.
    '''
    ifconfig_output = subprocess.check_output(["ifconfig","eth0"])
    ret = re.search('inet addr:([0-9]{1,3}\.){3}[0-9]{1,3}', ifconfig_output)
    if(ret):
        ip = ret.group(0).strip("inet addr:")
        #convert IP to decimal
        digits = ip.split(".")
        dec_ip = int(digits[0]) * (256**3) + int(digits[1]) * (256**2) + int(digits[2]) * (256**1) + int(digits[3]) * (256**0) 
        return dec_ip
    
    
def blinkLED(LED):
    '''
    @summary: Function toggles LED on and off (1sec total duration; 50% duty cycle)
    @param LED: GPIO BCM number 
    '''
    GPIO.output(LED, True)
    time.sleep(0.5)
    GPIO.output(LED, False)
    time.sleep(0.5)

    
def blinkNumTimes(LED, number_of_times):
    '''
    @summary: Function loops number_of_times and blinks LED.
    @param LED: GPIO BCM number
    @param number_of_times: how many times the LED needs to be blinked 
    '''
    for _ in range(number_of_times):
        blinkLED(LED)
        
'''
******************************************************************
MAIN PYTHON SCRIPT
******************************************************************
'''
print "******************************************************************"
print "Starting the DE library management system"
print "Press <Ctrl+C> to exit"
print "******************************************************************"
#First things first.. cleanup GPIOs in case script crashed last time it executed...
try:
    GPIO.cleanup()
except:
    pass
    
#GPIO defines (use BCM numbers)
GPIO_pushbutton_checkout = 18   #pushbutton to check out a book
GPIO_pushbutton_checkin = 23    #pushbutton to check in a book
GPIO_led_error = 4              #red LED
GPIO_led_waiting = 25           #yellow LED
GPIO_led_success = 22           #green LED

#set to BCM naming scheme
GPIO.setmode(GPIO.BCM)

#set up PUSHBUTTONS as inputs
GPIO.setup(GPIO_pushbutton_checkout, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(GPIO_pushbutton_checkin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#set up LEDs as outputs
GPIO.setup(GPIO_led_error, GPIO.OUT)
GPIO.setup(GPIO_led_waiting, GPIO.OUT)
GPIO.setup(GPIO_led_success, GPIO.OUT)

'''
Enter infinite loop which polls the buttons and looks for keypresses.
One button is used to check in books, another used to check out books.
This block is wrapped in try:except: in order to catch <Ctrl+C> and other exceptions
and cleanup the GPIOS correctly before exiting.
'''
try:
    #keeps track of the time when a button is pressed (used to turn off LEDs after a certain amount of time)
    start_time = 0
    
    #enter infinite loop
    while True:
        #add a delay so that we don't hog down all CPU cycles (other background processes can use resources)
        time.sleep(0.1)
        
        #check if 30sec have passed since last button press and turn off LEDs
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
            #wait 200ms to stabilize debounce
            time.sleep(0.2)
            
            #check if both buttons were pushed
            if input_state_check_out == False:
                input_state_check_in = GPIO.input(GPIO_pushbutton_checkin)
                if input_state_check_in == False:
                    decimalIP = getIP()
            elif input_state_check_in == False:
                input_state_check_out = GPIO.input(GPIO_pushbutton_checkout)
                if input_state_check_out == False:
                    decimalIP = getIP()
                    
            #if buttons were pushed at the same time we need to display the IP using LEDs
            if input_state_check_out == False and input_state_check_in == False:
                time.sleep(1) #wait 1 second
                #loop through each digit in decimalIP and blink the green LED 'digit' number of times; blink red LED between each digit
                list_of_digits = [int(i) for i in str(decimalIP)]
                for digit in list_of_digits:
                    blinkNumTimes(GPIO_led_success, digit)
                    blinkLED(GPIO_led_error)
                #continue to next iteration through while loop
                continue
            
            #start a counter which after 30s will turn off LEDs
            start_time = time.time()
            
            #turn on yellow LED and turn off all others
            GPIO.output(GPIO_led_waiting, True)
            GPIO.output(GPIO_led_error, False)
            GPIO.output(GPIO_led_success, False)
            
            #CHECK OUT button was pressed
            if input_state_check_out == False:
                ret = check_book(1)
                
            #CHECK IN button was pressed
            elif input_state_check_in == False:
                ret = check_book(0)
                
            #turn off yellow LED and turn on red (error) or green (success) LED
            GPIO.output(GPIO_led_waiting, False)
            if(ret < 0):
                #turn on red LED
                GPIO.output(GPIO_led_error, True)
            else:
                #turn on green LED
                GPIO.output(GPIO_led_success, True)
            
except:
    #Hit an exception... clean up GPIOs and exit script
    GPIO.output(GPIO_led_waiting, False)
    GPIO.output(GPIO_led_error, False)
    GPIO.output(GPIO_led_success, False)
    GPIO.cleanup()
    sys.exit()
    
