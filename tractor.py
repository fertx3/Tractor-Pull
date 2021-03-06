# -*- coding: utf-8 -*-
##############################################################################################
#	Project Name:	Tractor Pull
#	Author:			Sangman Choi
#	Date:			Nov 25, 2018
#	Modified:		None
#	Copyright Sangman Choi, 2018
#
#	Desc: Control the truck pulling a trailer. Using sensors for Motor Control and relay a trailer
#
##############################################################################################

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

###########################################################################
# global Variables
###########################################################################

#I2C Setup
channel = 1
device_reg_mode = 0x00
i2cAddress = {'compass' : 0x1E, 'infrared' : 0x48}
sensorBus = smbus.SMBus(channel)
pi = 3.14159265359

delay = 0.1

#Initialize Global Variables
process = True

direction = 'center'
compass = "N"
speed = 0
start = False
distance = 0
current = 0

isTractorConnected = False
isObstacle = False
isOnLine = True
isEndLine = False
isDisconnected = False
isShutdown = False
isOnceConnected = False

lock = threading.Lock()

#pin19 may be damaged
pinPi = {'servoMotor': 12, 'mainMotor1': 7, 'mainMotor2': 8, 'hall':16, 'ultraTrigger' : 21, 'ultraEcho' : 20, }

#Max Value - Left: 1000 Center: 1500 Right: 2000
directionVar = {'left': 1050, 'center':1550, 'right': 1950}
##############################################################################

IO.setwarnings(False)          			#do not show any warnings
IO.setmode (IO.BCM)     			    #Programming the GPIO by BCM pin numbers.

#IO Initialize
IO.setup(pinPi['servoMotor'],IO.OUT)
IO.setup(pinPi['mainMotor1'],IO.OUT)
IO.setup(pinPi['mainMotor2'],IO.OUT)
IO.setup(pinPi['ultraTrigger'],IO.OUT)
IO.setup(pinPi['ultraEcho'],IO.IN)
IO.setup(pinPi['hall'],IO.IN)
#turn off main motor
IO.output(pinPi['mainMotor1'], False)
IO.output(pinPi['mainMotor2'], False)

#Initialize PWM signal for Servomotor
pinDirection = PWM.Servo()         #GPIO13 as PWM output, with 20ms period
pinDirection.set_servo(pinPi['servoMotor'], directionVar['center']  )

##changeSpeed###################################################################################
#	Author:		Sangman Choi
#	Date:		Nov 25, 2018
#	Modified:	None
#	Desc: Change Speed of main motor
#	Input: Start, Process, isEndLine, isOnLine
#	Output: Speed from 0(Stop) to 2(Maximum)
##############################################################################################
def changeSpeed():
	global speed
	global start
	global process
	global isEndLine
	global isOnLine
	global isDisconnected
	global isObstacle
	global isShutdown

	currentSpeed = 0;

	while process == True:
		while start == True:
			time.sleep(delay)
			lock.acquire()

			if (not isShutdown) and (not isEndLine) and (isOnLine) and (not isDisconnected) and (not isObstacle):
				speed = 1
			else:
				speed = 0

			if isShutdown:
				isShutdown = False

			if currentSpeed == speed:
				lock.release()
				continue

			currentSpeed = speed;
			print("speed: ",speed)
			if speed == 0:
				print("speed0!!")
				IO.output(pinPi['mainMotor1'], False)
				IO.output(pinPi['mainMotor2'], False)
			elif speed == 1:
				print("speed1!")
				IO.output(pinPi['mainMotor1'], False)
				IO.output(pinPi['mainMotor2'], True)
			elif speed == 2:
				print("speed2")
				IO.output(pinPi['mainMotor1'], True)
				IO.output(pinPi['mainMotor2'], False)
			print("change speed\n")
			lock.release()
		speed = 0
		IO.output(pinPi['mainMotor1'], False)
		IO.output(pinPi['mainMotor2'], False)

##EO:changeSpeed################################################################################

##changeDirection###################################################################################
#	Author:		Sangman Choi
#	Date:		Nov 25, 2018
#	Modified:	None
#	Desc: Change Direction of Servo motor
#	Input: Direction, isEndLine, isOnLine, isDisconnected
#	Output: PWM Signal for Servo Motor
##############################################################################################

def changeDirection():
	global direction
	global isOnLine
	global isEndLine
	global isDisconnected

	currentDirection = 'center'

	global process
	while process == True:
		time.sleep(delay)
		lock.acquire()
		if currentDirection == direction or not isOnLine or isEndLine or isDisconnected:
			lock.release()
			continue

		currentDirection = direction
		pinDirection.set_servo(pinPi['servoMotor'], directionVar[direction])
		lock.release()
		print("change Direction\n")
##EO:changeDirection################################################################################

##ultraDistance###################################################################################
#	Author:		Sangman Choi
#	Date:		Nov 25, 2018
#	Modified:	None
#	Desc: Measure the distace from front (60cm)
#	Input: Ultrasonic Sensor(Trig, Echo)
#	Output: Distance, Speed, Exist of Obstacle
##############################################################################################

def ultraDistance():
	global speed
	global distance
	global isObstacle

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
		if distance < 30.0:
			speed = 0
			isObstacle = True
		elif distance > 35.0 or not isOnLine:
			isObstacle =False
			speed = 1

		lock.release()
##EO:ultraDistance################################################################################

##measureCompass###################################################################################
#	Author:		Sangman Choi
#	Date:		Nov 25, 2018
#	Modified:	None
#	Desc: Measure Direction of Truck
#	Input: Compass Sensor(I2C)
#	Output: Direction of Truck
##############################################################################################

def measureCompass():
	global compass

	sensorBus.write_byte_data(i2cAddress['compass'], 0x00, 0x70)
	sensorBus.write_byte_data(i2cAddress['compass'], 0x01, 0xA0)
	sensorBus.write_byte_data(i2cAddress['compass'], 0x02, 0x00)

	time.sleep(delay)
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

		if (headingAngle < 23 or headingAngle >= 338):
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
##EO:measureCompass################################################################################

##hall###################################################################################
#	Author:		Sangman Choi
#	Date:		Nov 25, 2018
#	Modified:	None
#	Desc: Check Tractor is connected or not
#	Input: Hall Effect Sensor
#	return: isTractorConnected, isDisconnected
##############################################################################################

def hall():
	global isTractorConnected
	global isDisconnected
	global isOnceConnected

	global process
	while process == True:
		time.sleep(delay)
		lock.acquire()

		if IO.input(pinPi['hall']) == False:
			isTractorConnected = True
			isOnceConnected = True

			print("Tractor Connected")
		else:
			isTractorConnected = False
			print("Tractor Not Connected")

		if (isOnceConnected == True) and (isTractorConnected == False):
			isDisconnected = True

		lock.release()
##EO:hall################################################################################

##infrared###################################################################################
#	Author:		Sangman Choi
#	Date:		Nov 25, 2018
#	Modified:	None
#	Desc: Change Speed of main motor
#	Input: Infrared Sensors(I2C)
#	return: Direction to change
##############################################################################################

def infrared():
	adc = Adafruit_ADS1x15.ADS1115()
	#adc = Adafruit_ADS1x15.ADS1115(address=0x49, busnum=1)
	#12bit: 65536
	global direction
	global speed
	global isOnLine
	global isEndLine
	global current

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
	#	if (sensored > 0 and sensored <7):
	#		isOnLine = True
	#		isEndLine = False
		print("Current.Derection = %s, Line Detection: %d" %(direction, sensored))
		if (sensored == 1 or sensored == 3) and direction != 'left':
			direction = 'left'
			print("Change to left")
		elif sensored == 2 and direction != 'center':
			direction = 'center'
			print("Change to Center")
		elif (sensored == 4 or sensored == 6) and direction != 'right':
			direction = 'right'
			print("Change to right")
		elif sensored == 7:
			print("Detect Horizontal Line")
			isEndLine = True
		elif sensored == 0:
			print("Not detect Line")
			isOnLine = False
		current = 489.29 * 0.000001 * adcValues[3] - 11.025
		print("Current : ", format(current, '.3f'))
		#os.system('clear')
		lock.release()
##EO:infrared################################################################################

##on_connect###################################################################################
#	Author:		Jennifer McNeil
#	Date:		Nov 25, 2018
#	Modified:	Sangman Choi
#	Desc: subscribe Topic via MQTT Protocal
##############################################################################################

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
    client.subscribe("Reset")
    client.subscribe("Shutdown")
##EO:on_connect################################################################################

##on_message###################################################################################
#	Author:		Jennifer McNeil
#	Date:		Nov 25, 2018
#	Modified:	Sangman Choi
#	Desc: Recieve Message from another Rasp PI for Starting
##############################################################################################

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
	global start
	global isShutdown
	global direction
	global speed
	global isTractorConnected
	global isObstacle
	global isOnLine
	global isEndLine
	global isDisconnected
	global isShutdown
	global isOnceConnected

	if msg.topic == "Start":
		#payload either 0, 1, or 2
		start = True if msg.payload.decode() == "True" else False
		#time.sleep(1)
		print("Trator Started!!")

	if msg.topic == "Reset":
		if msg.payload.decode() == "True":
			print("Reset Signal Detected!!")
			#time.sleep(1)
			speed = 0
			isTractorConnected = False
			isObstacle = False
			isOnLine = True
			isEndLine = False
			isDisconnected = False
			isShutdown = False
			isOnceConnected = False

	if msg.topic == "Shutdown":
		print("Reset Signal Detected!!")
		isShutdown = True if msg.payload.decode() == "True" else False

##EO:on_message################################################################################

##transferStatus###################################################################################
#	Author:		Sangman Choi
#	Date:		Nov 25, 2018
#	Modified:	None
#	Desc: Send Status Message to another Rasp PI
#	Output:  Send Status (speed, direction, isObstacle, isEndLine, isDisconnected, compass
#			 isTractorConnected, and Error Msg)
##############################################################################################

def transferStatus():
	global ip
	global process
	global speed
	global direction
	global isObstacle
	global isEndLine
	global isDisconnected
	global compass
	global isTractorConnected
	global current
	errorMsg = ""

	client = mqtt.Client()
	client.on_connect = on_connect
	client.on_message = on_message

	client.connect(ip, 1883, 60)

	while True:
		lock.acquire()
		client.loop_start()
		print("pubslishing")
		publish.single("Compass", compass, hostname=ip)
		publish.single("Current", format(current, '.2f'), hostname=ip)
		publish.single("Obsticle",isObstacle, hostname=ip)
		publish.single("Trailer",isTractorConnected, hostname=ip)
		if isObstacle:
			publish.single("Error", "Obstacle Found", hostname=ip)
		elif isEndLine:
			publish.single("Error", "Finished", hostname=ip)
		elif isDisconnected:
			publish.single("Error", "Tractor is Disconnected", hostname=ip)
		elif isOnLine == False:
			publish.single("Error", "Tractor is not on the lines", hostname=ip)

		print("published")
		client.loop_stop()
		lock.release()
		time.sleep(delay)
##EO:transferStatus################################################################################

###Main########################################################################################
os.system('clear')
print("Project [Tractor-Pull] Start!!!")
time.sleep(1)

print("Creating Threads")

tStatus = threading.Thread(target=transferStatus)
tStatus.start()
print("Created Threads[tStatus]")

tChangeSpeed = threading.Thread(target=changeSpeed)
tChangeSpeed.start()
print("Created Threads[tChangeSpeed]")

tChangeDirection = threading.Thread(target=changeDirection)
tChangeDirection.start()
print("Created Threads[tChangeDirection]")

tDistance = threading.Thread(target=ultraDistance)
tDistance.start()
print("Created Threads[tDistance]")

tCompass = threading.Thread(target=measureCompass)
tCompass.start()
print("Created Threads[tCompass]")

tHall = threading.Thread(target=hall)
tHall.start()
print("Created Threads[tHall]")

tInfrared = threading.Thread(target=infrared)
tInfrared.start()
print("Created Threads[tInfrared]")

print ("Creating Threads Done!!")

#Test Code########
speed = 0
#start = True
#delay = 1
##################

#while 1:
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
#	time.sleep(1)

tStatus.join()
print("Joined Tread [tStatus]")
tDistance.join()
print("Joined Tread [tDistance]")
tChangeSpeed.join()
print("Joined Tread [tChangeSpeed]");
tCompass.join()
print("Joined Tread [tCompass]")
tHall.join()
print("Joined Tread [tHall]")
print("Joined Tread [tChangeSpeed]");
tChangeDirection.join()
print("Joined Tread [tChangeDirection]")
tInfrared.join()
print("Joined Tread [tInfrared]")

print ("Project [Tractor-Pull] DONE!!!")
