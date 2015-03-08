#!/usr/bin/python
__author__ = 'GabrielSoares'

import MySQLdb
import sys
import subprocess
import re
import time
from prettytable import PrettyTable


print "******************************************************************"
print "This script is going to take you through the steps to check out a"
print "\tbook from the DE library."
print "******************************************************************"

#prompt user to scan the book's NFC tag...
print "Present book tag to NFC reader (timeout = 10 sec)..."
raw_input("Press Enter to start scanning...")

acquiredNFC = False
numLoops = 0
nfc_list = nfc_ids = ""
regex = re.compile('NFCID1\):\s*([^\n\r]*)')

while not acquiredNFC and numLoops < 10:
    print str(10 - numLoops) + ", ",
    sys.stdout.flush()

    #call cmd that scans NFC reader
    nfc_list = subprocess.check_output("nfc-list")

    if "NFCID1" in nfc_list:
        #run regular expression on nfc_list
        nfc_ids = regex.findall(nfc_list)

        #make sure we detect a single valid NFC id
        if len(nfc_ids) == 0:
            print "\nCould not find a valid NFC id... quiting..."
            sys.exit()

        elif len(nfc_ids) > 1:
            print "\nDetected multiple NFC ids... please try scanning a single one..."
            sys.exit()

        else:
            print "\nFound a tag!"
            acquiredNFC = True  #exit inner loop

    #didn't find tag on NFC reader, sleep before we try again
    else:
        time.sleep(1)
        numLoops += 1

#convert NFC Id string to hex array
hexId = bytearray.fromhex(nfc_ids[0].replace(" ", ""))
#convert hex array to a 4-byte number
RFID = int(hexId[0] << 24 | hexId[1] << 16 | hexId[2] << 8 | hexId[3])

#connect to the database
try:
    db = MySQLdb.connect('localhost', '<username>', '<password>', '<database_name>')
    cursor = db.cursor()
except:
    print "Unable to connect to database... exiting"
    cursor.close()
    db.close()
    sys.exit()

#make sure that the NFC id exists in the database
ret = cursor.execute("SELECT * FROM booklist WHERE nfc_id=%s;", (str(RFID)))
if not ret:
    print "ERR: cannot find this NFC Id in the database (" + "0x{:08X}".format(RFID) + ")"
    print "Book needs to be added to the database first..."
    cursor.close()
    db.close()
    sys.exit()


rows = cursor.fetchall()

#check that there aren't multiple entries with the same NFC id (shouldn't happen)
if len(rows) > 1:
    print "ERR: there are multiple books with the same NFC id..."
    print "Contact Gabriel Soares to fix this problem!"
    cursor.close()
    db.close()
    sys.exit()

#there is a single row element in table with this NFC id (proceed)
else:
    #display the row for the book to user and prompt for confirmation
    table = PrettyTable(["row", "NFC Id", "Book Title", "Book Author", "Status", "Date", "Employee"])
    table.align["Book Title"] = "l"     #left align
    table.align["Book Author"] = "l"    #left align
    for i in rows:
        table.add_row(i)
    print table

    #confirm that this is the book user wants to check out
    confirm = raw_input("Is this the book you want to check out? [y/n]\n>> ")
    if confirm not in ['y', 'Y', 'yes']:
        sys.exit()

    #get the status field for this book
    ret = cursor.execute("SELECT status FROM booklist WHERE nfc_id=%s;", (str(RFID)))
    rows = [item[0] for item in cursor.fetchall()]

    #check that the status of the field is not already 1
    if rows[0] == 1:
        print "ERR: this item is currently already checked out!"
        print "Check book in before checking it out..."
        cursor.close()
        db.close()
        sys.exit()
    #status field is 0 -> we can change it to 1 and set the date field
    else:
        try:
            ret = cursor.execute("UPDATE booklist SET status=%s, date=%s WHERE nfc_id=%s;",
                                ('1', time.strftime('%Y-%m-%d'), str(RFID)))
        except:
            print "Unable to modify database element... exiting"
            cursor.close()
            db.close()
            sys.exit()

print "BOOK WAS SUCCESSFULLY CHECKED OUT!"

db.commit()
cursor.close()
db.close()
sys.exit()
