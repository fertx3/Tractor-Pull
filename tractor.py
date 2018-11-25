# -*- coding: utf-8 -*-
import RPi.GPIO as IO    #calling header file which helps us use GPIO’s of PI
from RPIO import PWM
import Adafruit_ADS1x15
import smbus

import math
import os
import sys
import time                #calling time to provide delays in program
import threading

import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

if len(sys.argv) != 2:
	print("Usage:", sys.argv[0], "<Controller IP Address>")
	sys.exit()

#mqtt configuration
#ip = "172.22.20.29"
ip = sys.argv[1]

#I2C Setup
channel = 1
device_reg_mode = 0x00
i2cAddress = {'compass' : 0x1E, 'infrared' : 0x48}
sensorBus = smbus.SMBus(channel)
pi = 3.14159265359
delay = 1

lock = threading.Lock()

process = True

#pin19 may be damaged
pinPi = {'servoMotor': 13, 'mainMotor1': 5, 'mainMotor2': 26, 'hall':16, 'ultraTrigger' : 21, 'ultraEcho' : 20, }

#Max Value - Left: 1000 Center: 1500 Right: 2000
directionVar = {'left': 1050, 'center':1550, 'right': 1950}

IO.setwarnings(False)           #do not show any warnings
IO.setmode (IO.BCM)         #we are programming the GPIO by BCM pin numbers.
IO.setup(pinPi['servoMotor'],IO.OUT)           # initialize GPIO19 as an output.
IO.setup(pinPi['mainMotor1'],IO.OUT)
IO.setup(pinPi['mainMotor2'],IO.OUT)
IO.setup(pinPi['ultraTrigger'],IO.OUT)
IO.setup(pinPi['ultraEcho'],IO.IN)
IO.setup(pinPi['hall'],IO.IN)

pinDirection = PWM.Servo()         #GPIO13 as PWM output, with 20ms period
pinDirection.set_servo(pinPi['servoMotor'], directionVar['center']  )

direction = 'center'

compass = "N"
speed = 0
isTractorConnected = False
distance = 0
isObstacle = False
isOnLine = True
isEndLine = False
start = False
isOnceConnected = False

def changeSpeed():
	global speed
	global start
	currentSpeed = 0;
	global process
	while process == True:
		while start == True:
			time.sleep(delay)
			lock.acquire()
			if currentSpeed == speed:
				lock.release()
				continue

			currentSpeed = speed;
			print("speed: ",speed)
			if speed == 0:
				print("speed0!!")
				IO.output(pinPi['mainMotor1'], False)
				IO.output(pinPi['mainMotor2'], False)
			elif speed == 1 and isOnLine and not isEndLine:
				print("speed1!")
				IO.output(pinPi['mainMotor1'], False)
				IO.output(pinPi['mainMotor2'], True)
			elif speed == 2 and isOnline and not isEndLine:
				print("speed2")
				IO.output(pinPi['mainMotor1'], True)
				IO.output(pinPi['mainMotor2'], False)
			print("change speed\n")
			lock.release()

def changeDirection():
	global direction
	currentDirection = 'center'

	global process
	while process == True:
		time.sleep(delay)
		lock.acquire()
		if currentDirection == direction or not isOnLine or isEndLine:
			lock.release()
			continue

		currentDirection = direction
		pinDirection.set_servo(pinPi['servoMotor'], directionVar[direction])
		lock.release()
		print("change Direction\n")

def ultraDistance():
	global speed
	global distance
	global isObstacle
	global isEndLine
	global isOnLine

	global process
	StartTime = 0;
	StopTime = 0;

	while process == True:
		time.sleep(delay)
		lock.acquire()
		time.sleep(0.0001)
		IO.output(pinPi['ultraTrigger'], True)
		time.sleep(0.00001)
		IO.output(pinPi['ultraTrigger'], False)

		initTime = time.time()

		while IO.input(pinPi['ultraEcho']) == False:
			StartTime = time.time()
			if StartTime-initTime > 1.5:
				print("Error(StartTime > 1.5 sec)")
				break
		while IO.input(pinPi['ultraEcho']) == True:
			StopTime = time.time()
			if StopTime-initTime > 1.5:
				print("Error(StopTime > 1.5 sec")
				break
		TimeElapsed = StopTime - StartTime
		distance = round((TimeElapsed * 17150),2)

		if distance < 1.0:
			print("Distance Less than 1.0")
			lock.release()
			continue #less than 1cm is error
		print("%.1f cm" %distance)
		#test code
		if distance < 60.0 and speed == 1:
			speed = 0
			isObstacle = True
		elif distance > 70.0 and isObstacle == False and not isEndLine and isOnLine:
			speed = 1

		lock.release()


def measureCompass():
	global compass

	sensorBus.write_byte_data(i2cAddress['compass'], 0x00, 0x70)
	sensorBus.write_byte_data(i2cAddress['compass'], 0x01, 0xA0)
	sensorBus.write_byte_data(i2cAddress['compass'], 0x02, 0x00)

	time.sleep(0.5)
	heading = 0.0
	#London Declination Angle: 8.58
	declination = ((8.0 + (58.0 / 60.0)) / (180/pi))
	global process
	while process == True:
		time.sleep(delay)
		lock.acquire()

		rawCompass = sensorBus.read_i2c_block_data(i2cAddress['compass'], 0x03, 6)
		xCompass = rawCompass[0] * 256 + rawCompass[1]
		zCompass = rawCompass[2] * 256 + rawCompass[3]
		yCompass = rawCompass[4] * 256 + rawCompass[5]

		if xCompass > 32768:
			xCompass = xCompass - 65536

		if yCompass > 32768:
			yCompass = yCompass - 65536

		if zCompass > 32768:
			zCompass = zCompass - 65536

		heading = math.atan2(yCompass, xCompass)
		heading = heading + declination

		if(heading < 0):
			heading = heading + 2.0*pi

		if(heading > 2*pi):
			heading = heading - 2.0*pi

		headingAngle = int(heading * 180/pi)

		print("Heading Angle: %d" %headingAngle)
		print("X: %d, Y: %d, Z: %d" %(xCompass,yCompass,zCompass))

		if (headingAngle < 23 or headingAngle > 338):
			compass = "N"
		elif (headingAngle < 68):
			compass = "NE"
		elif (headingAngle < 113):
			compass = "E"
		elif (headingAngle < 158):
			compass = "SE"
		elif (headingAngle < 203):
			compass = "S"
		elif (headingAngle < 248):
			compass = "SW"
		elif (headingAngle < 293):
			compass = "W"
		elif (headingAngle < 338):
			compass = "NW"
		else:
			compass = "Huh???"

		print("Compass:",compass)

		lock.release()


def hall():
	global isTractorConnected

	global process
	while process == True:
		time.sleep(delay)
		lock.acquire()

		if IO.input(pinPi['hall']) == True:
			isTractorConnected = True
			isOnceConnected = True
			print("Tractor Connected")
		else:
			isTractorConnected = False
			print("Tractor Not Connected")

		if isOnceConnected == True and isTractorConnected == False
			speed = 0

		lock.release()

def infrared():
	adc = Adafruit_ADS1x15.ADS1115()
	#adc = Adafruit_ADS1x15.ADS1115(address=0x49, busnum=1)
	#12bit: 65536
	global direction
	global speed
	global isOnLine
	global isEndLine

	detect = 20000

	while process == True:
		time.sleep(delay)
		lock.acquire()

		adcValues = [0]*4

		for i in range(4):
			#GAIN
			#1 = +-4.096V
			#2 = +-2.048V
			adcValues[i] = adc.read_adc(i, gain=1)

		print("ADC.A0: ", adcValues[0])
		print("ADC.A1: ", adcValues[1])
		print("ADC.A2: ", adcValues[2])
		print("ADC.A3: ", adcValues[3])

		isLeftSensored = 1 if adcValues[0] >= detect else 0
		isCenterSensored = 2 if adcValues[1] >= detect else 0
		isRightSensored = 4 if adcValues[2] >= detect else 0

		sensored = isLeftSensored + isCenterSensored + isRightSensored
		print("Current.Derection = %s, Line Detection: %d" %(direction, sensored))
		if (sensored == 1 or sensored == 3) and direction != 'left':
			direction = 'left'
			isOnline = True
			print("Change to left")
		elif sensored == 2 and direction != 'center':
			direction = 'center'
			isOnline = True
			print("Change to Center")
		elif (sensored == 4 or sensored == 6) and direction != 'right':
			direction = 'right'
			isOnline = True
			print("Change to right")
		elif sensored == 7:
			print("Detect Horizontal Line")
			speed = 0:
			isEndLine = True
		else:
			isOnline = False
			speed = 0;
		#os.system('clear')
		lock.release()

def on_connect(client, userdata, flags, rc):

    # Subscribing in on_connect() - if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("Compass")
    client.subscribe("Current")
    client.subscribe("Obsticle")
    client.subscribe("Trailer")
    client.subscribe("Start")
    client.subscribe("Power")
    client.subscribe("Error")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
	global start
	#print ()
	#print (msg.topic)
	#print (msg.payload.decode() )

	if msg.topic == "Start":
		#payload either 0, 1, or 2
		start = True if msg.payload.decode() == "True" else False
		print(start)

def transferStatus():
	global process
	global speed
	global direction
	global isObstacle
	global isEndLine
	global compass
	global isTractorConnected

	errorMsg = ""

	client = mqtt.Client()
	client.on_connect = on_connect
	client.on_message = on_message

	client.connect(ip, 1883, 60)

	while True:
		lock.acquire()
		client.loop_start()
		print("pubslish")
		publish.single("Compass", compass, hostname=ip)
		publish.single("Current","0", hostname=ip)
		publish.single("Obsticle",isObstacle, hostname=ip)
		publish.single("Trailer",isTractorConnected, hostname=ip)
		if isObstacle:
			publish.single("Error", "Obstacle Found", hostname=ip)
		elif isEndLine:
			publish.single("Error", "Finished", hostname=ip)
		elif isOnceConnected and isTractorConnected == False:
			publish.single("Error", "Tractor Disconnected", hostname=ip)
		elif isOnLine == False:
			publish.single("Error", "Tractor is not on the lines", hostname=ip)

		print("published")
		client.loop_stop()
		lock.release()
		time.sleep(1)

os.system('clear')
print("Project [Tractor-Pull] Start!!!")
time.sleep(1)

print("Creating Threads")

tStatus = threading.Thread(target=transferStatus)
tStatus.start()
print("Created Threads[tStatus]")

#tChangeSpeed = threading.Thread(target=changeSpeed)
#tChangeSpeed.start()
#print("Created Threads[tChangeSpeed]")
#
#tChangeDirection = threading.Thread(target=changeDirection)
#tChangeDirection.start()
#print("Created Threads[tChangeDirection]")
#
#tDistance = threading.Thread(target=ultraDistance)
#tDistance.start()
#print("Created Threads[tDistance]")
#
#tCompass = threading.Thread(target=measureCompass)
#tCompass.start()
#print("Created Threads[tCompass]")

#tHall = threading.Thread(target=hall)
#tHall.start()
#print("Created Threads[tHall]")

#tInfrared = threading.Thread(target=infrared)
#tInfrared.start()
#print("Created Threads[tInfrared]")

print ("Creating Threads Done!!")


while 1:

	print("Start", start)
#	lock.acquire()

#	print("main\n")
#	temp = input("dirction: ")
#	if temp == 'l':
#		direction = 'left'
#	elif temp == 'c':
#		direction = 'center'
#	elif temp == 'r':
#		direction = 'right'
#	else:
#		print("Wrong input")
#	speed = int(input("speed [0-2]:"))
#	lock.release()
	time.sleep(1)

tStatus.join()
#tDistance.join()
#print("Joined Tread [tDistance]");
#tChangeSpeed.join()
#print("Joined Tread [tInfrared]");
#tCompass.join()
#print("Joined Tread [tCompass]");
#tHall.join()
#print("Joined Tread [tJoin]");

#print("Joined Tread [tChangeSpeed]");
#tChangeDirection.join()

#print("Joined Tread [tChangeDirection]");
#tInfrared.join()



print ("Project [Tractor-Pull] DONE!!!")
