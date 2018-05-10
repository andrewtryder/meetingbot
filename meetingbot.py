#!/usr/bin/env python

from ics import Calendar, Event
from urllib2 import urlopen
import pkg_resources  # need to peg a version until we figure out .between in 2.0
pkg_resources.require("pendulum==1.5.1")
import pendulum 
import pytz
import RPi.GPIO as GPIO
from i2c_lcd import i2c_lcd

# credits
# RPi_I2C_driver -  https://i2c-lcd.readthedocs.io
# pendulum - https://pendulum.eustace.io/ 
# ics - https://pypi.org/project/ics/

# user defined variables. Could be a config file later on.
icsurl = "https://calendar.google.com/calendar/ical/6il0cofdijql00h48d1furgans%40group.calendar.google.com/public/basic.ics"

# configure these to the GPIO pins for the traffic light
redLedPin = 19
yellowLedPin = 13
greenLedPin = 26

# now some globals.
red = False
yellow = False
green = False

# we will need the time .now()
timenow = pendulum.now()

# first, we'll try to fetch the url.
# quick dump if it does not work, which could be due to no internet, etc.
# this should be improved to be more robust but will come when integrated.
try:
    c = Calendar(urlopen(icsurl).read().decode('iso-8859-1'))
except Exception, e:
    exit("For some reason, we could not open the iCal URL :: {0}".format(e))

mylcd = i2c_lcd.lcd()

# setup our function to talk with the LCD.
def lcdDisplay(one, two, three, four):
	# turn backlight on (incase off)
	mylcd.backlight_on(True)
        mylcd.lcd_display_string(one[0:19], 1)
        mylcd.lcd_display_string(two, 2)
        mylcd.lcd_display_string(three, 3)
        mylcd.lcd_display_string(four[0:19], 4)

# c is now an ics object with everything in it.
# method of ics events into events list
events = c.events
print "Total length {0}".format(len(events))
# iterate through all. 
for i in events:
    uid = i.uid
    name = i.name
    begin = i.begin
    end = i.end
    duration = i.duration
    all_day = i.all_day
    desc = i.description
    # sanity check. we don't control the data feed, so lets just do a simple "don't break"
    # commented out until we know more about the quality of the data feed.
    #if not uid or not name or not begin or not end or not duration or not desc:
    #    continue 

    # now, we have to use try/except because ICS/iCal has known to be "loose" in
    # their formatting.
    try:
        begindt = pendulum.parse(str(begin))
        enddt = pendulum.parse(str(end))
    except Exception, e:  # uncomment below to debug when testing.
        #print "For some reason, I could not parse begin/end :: {0}".format(e)
        continue

    # now comes the fun part.. doing datecalc math. 
    # thankfully, we should have no worries about timezones because we control the cal.
    # first, check if something is going on but is 120 seconds or under until ends.
    # next, check if we're before this but in a booked period (red) 
    # otherwise, we're green (open)
    if timenow.between(begindt, enddt):
	# timezone oddities here.. could modularize.
	starttime = str(begindt.astimezone(tz='America/New_York').hour) + ":" + str(begindt.minute)
	endtime =  str(enddt.astimezone(tz='America/New_York').hour) + ":" + str(enddt.minute)
	timebooked = "{0} - {1}".format(starttime, endtime)
	lcdout = [i.name, timebooked, i.description[0:19], i.description[20:39]]
        red = True
	# last, also check if there are under 5 minutes before it ends.
	if enddt.between(timenow.add(seconds=120), timenow):
	    yellow = True
        break
    # but, if anything is coming up within the next 15 minutes, don't break, keep green but go yellow, too.
    if begindt.between(timenow, timenow.add(seconds=1500)):
        starttime = str(begindt.astimezone(tz='America/New_York').hour) + ":" + str(begindt.minute)
        endtime =  str(enddt.astimezone(tz='America/New_York').hour) + ":" + str(enddt.minute)
        timebooked = "{0} - {1}".format(starttime, endtime)
        lcdout = [i.name, timebooked, i.description[0:19], i.description[20:39]]
	yellow = True
	# lets also set the lcd.


# we're out of the for loop processing events but now have to handle the data
# that is received back.

# GPIO.
GPIO.setmode(GPIO.BCM)  # BCM numbering.
GPIO.setwarnings(False)  # don't print warnings.
GPIO.setup(yellowLedPin, GPIO.OUT)  # setup each LED pin to output
GPIO.setup(redLedPin, GPIO.OUT)
GPIO.setup(greenLedPin, GPIO.OUT)

# now check and work with the LEDs and LCD. 
# for output.
if not yellow and not red:  # assume green.
	GPIO.output(greenLedPin, 1)
	mylcd.lcd_clear()
	mylcd.backlight_on(False)
else:
	GPIO.output(greenLedPin, 0)
if yellow:
	lcdDisplay(lcdout[0], lcdout[1], lcdout[2], lcdout[3])
	GPIO.output(yellowLedPin, 1)
else:
	GPIO.output(yellowLedPin, 0)
if red:
	lcdDisplay(lcdout[0], lcdout[1], lcdout[2], lcdout[3])
	GPIO.output(redLedPin, 1)
else:
	GPIO.output(redLedPin, 0)

print "R: {0} Y: {1} G: {2}".format(red, yellow, green)
