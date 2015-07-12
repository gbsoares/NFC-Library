## NFC-Library
This is the project description for an NFC book management system that I built for my office.
It uses a Raspberry Pi connected to an NFC reader (PN532) to read Mifare NFC tags on the books that we have in our Engineering Library.

The motivation for this project came about when I purchased a large number of books for the Device Engineering team at Alarm.com and wanted to have a way to be able to track the state of the books. I decided that an easy way to do so would be to use and NFC tag reader which would allow me to scan the books each time they were either checked in or checked out from the library.

A high-level description of the project can be found on my [website](http://gabrielsoares.com/projects/electronics/nfc_library.html).

## Hardware & Software Components
I wanted the whole system to be self-contained and small enough to be able to mount to the bookshelves so I decided to use a Raspberry Pi and an Adafruit PN532 NFC/RFID controller board. 

The Raspberry Pi is running a Raspian Wheezy distribution onto which I have installed MySQL and the Python binding library.

I have also built an enclosure for the system out of wood and acrylic using a laser cutter (drawings included in .dwg file).

The physical connections between the Raspberry Pi, NFC reader, buttons, and LEDs are summarized in the following table:

RPi Pin # | RPi Pin Name | Connected To:
--------- | ------------ | -------------
2 | 5V | 5.0V on NFC
6 | GND | GND on NFC
8 | TX | TXD on NFC
10 | RX | RXD on NFC
12 | BCM GPIO18 | Check-Out Button
16 | BCM GPIO23 | Check-In Button
7 | BCM GPIO04 | Red LED
22 | BCM GPIO25 | Yellow LED
15 | BCM GPIO22 | Green LED
25 | GND | LEDs (cathode)

[RPi GPIO Descriptions](https://github.com/gbsoares/NFC-Library/blob/master/gpio-descriptions.png)


## Installation

### libnfc
The first step in connecting the Raspberry Pi to the PN532 board is to install the [libnfc library](http://nfc-tools.org/index.php?title=Main_Page). I have copied the instructions from [Adafruit](https://learn.adafruit.com/adafruit-nfc-rfid-on-raspberry-pi/overview) in case they change their page in the future. Their explanation is more detailed so I would recommend following their installation process.
* Free up UART on the RPi by going into `$ sudo raspi-config`, selecting **option 7** (Serial), and checking option to **No**. Reboot RPi.
* Go to [this link](https://bintray.com/nfc-tools/sources/libnfc) and download the latest stable release of libnfc tar file. You then want to extract uncompress and extract the contents of the .tar file (in the commands listed below, replace `libnfc-libnfc-1.7.0` with the appropriate file name from your download.
* Once you have extracted the files you need to setup libnfc for the Raspberry Pi by moving the uart config file for RPi into the correct folder `/etc/nfc/device.d/`.
```
$ cd libnfc-libnfc-1.7.0
$ sudo mkdir /etc/nfc
$ sudo mkdir /etc/nfc/devices.d
$ sudo cp contrib/libnfc/pn532_uart_on_rpi.conf.sample /etc/nfc/devices.d/pn532_uart_on_rpi.conf
```
* On the file we just moved you want to make a small edit by opening the file on the nano editor:
```
sudo nano /etc/nfc/devices.d/pn532_uart_on_rpi.conf
```
And including the line `allow_instrusive_scan = true` at the end. Save and exit.
* We now need to configure and build the project by running the following commands (note: these can take a while to complete):
```
$ sudo apt-get install autoconf
$ sudo apt-get install libtool
$ sudo apt-get install libpcsclite-dev libusb-dev
$ autoreconf -vis
$ ./configure --with-drivers=pn532_uart --sysconfdir=/etc --prefix=/usr
```
```
$ sudo make clean
$ sudo make install all
```
You can test that the installation was done successfully by running `$ nfc-list`. You should see some text that says: "Connected to NFC Reader: ...".

### MySQL
The next step is to install MySQL on the Raspberry Pi along with the Python bindings so that we can modify our database from the Python scripts. I mostly followed the steps outlined [here](http://raspberrywebserver.com/sql-databases/using-mysql-on-a-raspberry-pi.html) to do so.
* To install MySQL and the Python bindings run:
```
sudo apt-get install mysql-server python-mysqldb
```
* You then want to create a database that will hold the library items. I created a database containing three tables following the format below:
```
BOOKLIST TABLE:
+---------------+------------+------+-----+---------+----------------+
| Field         | Type       | Null | Key | Default | Extra          |
+---------------+------------+------+-----+---------+----------------+
| row           | int(11)    | NO   | PRI | NULL    | auto_increment |
| nfc_id        | bigint(20) | YES  |     | NULL    |                |
| book_title    | text       | YES  |     | NULL    |                |
| book_author   | text       | YES  |     | NULL    |                |
| status        | tinyint(1) | YES  |     | NULL    |                |
| date          | date       | YES  |     | NULL    |                |
| user          | int(11)    | YES  |     | NULL    |                |
| num_check_out | int(11)    | YES  |     | 0       |                |
+---------------+------------+------+-----+---------+----------------+

USERS TABLE: 
+-----------------------+------------+------+-----+---------+----------------+
| Field                 | Type       | Null | Key | Default | Extra          |
+-----------------------+------------+------+-----+---------+----------------+
| row                   | int(11)    | NO   | PRI | NULL    | auto_increment |
| first_name            | text       | YES  |     | NULL    |                |
| last_name             | text       | YES  |     | NULL    |                |
| nfc_id                | bigint(20) | YES  |     | NULL    |                |
| num_books_checked_out | int(11)    | YES  |     | NULL    |                |
+-----------------------+------------+------+-----+---------+----------------+

STATISTICS:
+-----------+------------+------+-----+---------+----------------+
| Field     | Type       | Null | Key | Default | Extra          |
+-----------+------------+------+-----+---------+----------------+
| row       | int(11)    | NO   | PRI | NULL    | auto_increment |
| last_in   | bigint(20) | YES  |     | NULL    |                |
| last_out  | bigint(20) | YES  |     | NULL    |                |
| num_in    | int(11)    | YES  |     | NULL    |                |
| num_out   | int(11)    | YES  |     | NULL    |                |
| most_read | bigint(20) | YES  |     | NULL    |                |
| timestamp | datetime   | YES  |     | NULL    |                |
+-----------+------------+------+-----+---------+----------------+
```

### Python Scripts
I have added two Python scripts to this project **add_book.py** and **library.py**.
Run **add_book.py** whenever you want to add a book to the database. This script will prompt you to enter the title of the book, the author(s), and scan the NFC tag. In between each step it prompts you to make sure the correct information was enterred. There are certain variables you will want to edit in your copy depending on how you set up your database.
In the block:
```
db = MySQLdb.connect('localhost', '<username>', '<password>', '<database>')
cursor = db.cursor()
```
you will want to replace `username` and `password` with the credentials you used to set up MySQL , and `database` with the name of the database you created.

**library.py** is a script that I leave running all the time. I set a cron job that starts the script after bootup and another script that reboots the RPi every night (just in case the system gets into an undesired state and there is a way to recover from it). This script performs a couple of tasks:
* it polls the state of both the check-out and check-in buttons
* it scans for NFC tags if the buttons are pressed
* it toggles the LEDs to provide visual feedback
* updates the databases
* sends statistics to data.sparkfun.com which I can then use to display basic information about the system on my website

Both files are small and straight-forward and you should be able to easily make changes to them for your application.
