#!/usr/bin/python
__author__ = 'GabrielSoares'

import MySQLdb
import subprocess
import time
import sys
import re
from prettytable import PrettyTable


print "******************************************************************"
print "This script is going to take you through the steps to add a new"
print "\tbook to the DE_library database."
print "******************************************************************"

#prompt user for book title...
acquiredTitle = False
while not acquiredTitle:
    title = raw_input("Enter Book Title:\n>> ")

    if not title:
        print "ERR: empty field...\n"
        continue

    confirm = raw_input("Is this correct? [y/n] '" + title + "'\n>> ")
    if confirm in ['y', 'Y', 'yes']:
        acquiredTitle = True

print "--------------"

#prompt user for book author...
acquiredAuthor = False
while not acquiredAuthor:
    author = raw_input("Enter author (comma separate if multiple authors):\n>> ")

    if not author:
        print "ERR: empty fields...\n"
        continue

    confirm = raw_input("Is this correct? [y/n] '" + author + "'\n>> ")
    if confirm in ['y', 'Y', 'yes']:
        acquiredAuthor = True


#prompt user for NFC tag
flag = False
regex = re.compile('NFCID1\):\s*([^\n\r]*)')
nfc_list = nfc_ids = ""

while not flag:
    acquiredNFC = False
    numLoops = 0

    print "--------------"
    print "Present book tag to NFC reader (timeout = 10 sec)..."
    raw_input("Press Enter to start scanning...")

    while not acquiredNFC and numLoops < 10:
        print str(10 - numLoops) + ", ",
        sys.stdout.flush()

        #call cmd that scans NFC reader
        nfc_list = subprocess.check_output("nfc-list")

        if "NFCID1" in nfc_list:
            #run regular expression on nfc_list
            nfc_ids = regex.findall(nfc_list)

            if len(nfc_ids) == 0:
                print "\nCould not find a valid NFC id... quiting..."
                sys.exit()

            elif len(nfc_ids) > 1:
                print "\nDetected multiple NFC ids... please try scanning a single one..."
                acquiredNFC = True  #exit inner loop
                flag = False        #stay on outer loop

            else:
                print "\nFound a tag!"
                acquiredNFC = True  #exit inner loop
                flag = True         #exit outer loop

        #didn't find tag on NFC reader, sleep before we try again
        else:
            time.sleep(1)
            numLoops += 1

    #ask for confirmation before running outer loop again
    if not flag:
        confirm = raw_input("\nWould you like to try scanning the RFID again? [y/n]\n>> ")
        if confirm not in ['y', 'Y', 'yes']:
            sys.exit()

#convert NFC Id string to hex array
hexId = bytearray.fromhex(nfc_ids[0].replace(" ", ""))
#convert hex array to a 4-byte number
RFID = int(hexId[0] << 24 | hexId[1] << 16 | hexId[2] << 8 | hexId[3])

#check if RFID already exists in the database
try:
    db = MySQLdb.connect('localhost', '<username>', '<password>', '<database_name>')
    cursor = db.cursor()
except:
    print "Unable to connect to database... exiting"
    cursor.close()
    db.close()
    sys.exit()

#check if there is already an entry with this NFC id
ret = cursor.execute("SELECT * FROM booklist WHERE nfc_id=%s;", (str(RFID)))
if ret:
    print "ERR: this NFC tag already exists in the database (" + "0x{:08X}".format(RFID) + ")"
    sys.exit()

print "--------------"
print "Let's review the information before adding to the database..."
print "Book Title: '" + title + "'"
print "Book Author: '" + author + "'"
print "NFC Id: " + "0x{:08X}".format(RFID)

#Add information into MySQL database (but don't commit yet)
'''
Table Structure:
************************
column #	|	Field Name	|	Type
-----------------------------------------
	0		|	row			|	AUTO_INCREMENT
	1		|	nfc_id		|	INT
	2		|	book_title	|	TEXT
	3		|	book_author	|	TEXT
	4		|	status		|	BOOLEAN
	5		|	date		|	DATE
	6		|	employee	|	TEXT
'''
try:
    cursor.execute("INSERT INTO booklist VALUES(null, %s, %s, %s, '0', %s, null);",
                   (str(RFID), title, author, time.strftime('%Y-%m-%d')))
except:
    print "Unable to add to database... exiting"
    cursor.close()
    db.close()
    sys.exit()

#get the entire booklist and display it
cursor.execute("SELECT * from booklist;")
rows = cursor.fetchall()
table = PrettyTable(["row", "NFC Id", "Book Title", "Book Author", "Status", "Date", "Employee"])
table.align["Book Title"] = "l"     #left align
table.align["Book Author"] = "l"    #left align
for i in rows:
    table.add_row(i)
print table

confirm = raw_input("Is this information correct? [y/n]\n>> ")
if confirm not in ['y', 'Y', 'yes']:
    sys.exit()

print "Information was successfully added to database"

db.commit()
cursor.close()
db.close()
sys.exit()


