## NFC-Library
This is the project description for an NFC book management system that I built for my office.
It uses a Raspberry Pi connected to an NFC reader (PN532) to read Mifare NFC tags on the books that we have in our Engineering Library.

The motivation for this project came about when I purchased a large number of books for the Device Engineering team at Alarm.com and wanted to have a way to be able to track where the books were going. I decided that an easy way to do so would be to use and NFC tag reader which would allow me to scan the books each time they were either checked in or checked out from the library.


## Hardware & Software Components
I wanted the whole system to be self-contained and small enough to be able to mount to the bookshelves so I decided to use a Raspberry Pi and an Adafruit PN532 NFC/RFID controller board. Since I am still in the process of building the whole system I haven't created an enclosure for it.
The Raspberry Pi is running a Raspian Wheezy distribution onto which I have installed MySQL and the Python binding library.


## Installation

### libnfc
The first step in connecting the Raspberry Pi to the PN532 board is to install the [libnfc library](http://nfc-tools.org/index.php?title=Main_Page). I have copied the instructions from [Adafruit](https://learn.adafruit.com/adafruit-nfc-rfid-on-raspberry-pi/building-libnfc) in case they change their page in the future.
* Go to [this link](https://code.google.com/p/libnfc/source/browse/?name=libnfc-1.7.0) and download the libnfc tar file. You then want to run the following command to extract the files:
```
$ cd /home/pi
$ mkdir libnfc
$ cd libnfc
$ wget https://libnfc.googlecode.com/archive/libnfc-1.7.0.tar.gz
$ tar -xvzf libnfc-1.7.0.tar.gz
```
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



