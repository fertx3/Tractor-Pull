# -*- coding: utf-8 -*-
import RPi.GPIO as IO    #calling header file which helps us use GPIO’s of PI
from RPIO import PWM
import time                #calling time to provide delays in program
import threading
import curses
import smbus 
import math
import os

#I2C Setup
channel = 1
device_reg_mode = 0x00
i2cAddress = {'compass' : 0x1E}
sensorBus = smbus.SMBus(channel)
pi = 3.14159265359

lock = threading.Lock()

process = True

#Infrared Sensors Ports are needed to modify
pinPi = {'servoMotor': 13, 'mainMotor1': 19, 'mainMotor2': 26, 'hall':16, 'ultraTrigger' : 21, 'ultraEcho' : 20, 'infraL': 22, 'infraC': 23, 'infraR': 24}

#Max Value - Left: 1000 Center: 1500 Right: 2000
directionVar = {'left': 1250, 'center':1520, 'right': 1770}

#IO.setwarnings(False)           #do not show any warnings
IO.setmode (IO.BCM)         #we are programming the GPIO by BCM pin numbers. (PIN35 as ‘GPIO19’)
IO.setup(pinPi['servoMotor'],IO.OUT)           # initialize GPIO19 as an output.
IO.setup(pinPi['mainMotor1'],IO.OUT)
IO.setup(pinPi['mainMotor2'],IO.OUT)
IO.setup(pinPi['ultraTrigger'],IO.OUT)
IO.setup(pinPi['ultraEcho'],IO.IN)
IO.setup(pinPi['hall'],IO.IN)

IO.setup(pinPi['infraL'], IO.IN)
IO.setup(pinPi['infraR'], IO.IN)
IO.setup(pinPi['infraC'], IO.IN)

pinDirection = PWM.Servo()         #GPIO13 as PWM output, with 20ms period
pinDirection.set_servo(pinPi['servoMotor'], directionVar['center']  )

compass = ''
direction = 'center'

speed = 0
tractorConnected = False
distance = 0
isObstacle = False

def changeSpeed():
	global speed
	currentSpeed = 0;
	global process
	while process == True:
		time.sleep(0.2)
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

def changeDirection():
	global direction
	currentDirection = 'center'
	
	global process
	while process == True:
		time.sleep(0.2)
		lock.acquire()
		if currentDirection == direction:
			lock.release()
			continue

		currentDirection = direction
		pinDirection.set_servo(pinPi['servoMotor'], directionVar[direction])
		time.sleep(0.5)
		lock.release()
		print("change Direction\n")

def ultraDistance():
	global speed
	global distance
	global isObstacle

	global process
	while process == True:
		time.sleep(0.2)
		lock.acquire()

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
		if distance < 60.0:
			speed = 0
			#isObstacle = True
			
		elif isObstacle == False:
			speed = 1
		#
		lock.release()


def compass():
	global compass

	sensorBus.write_byte_data(i2cAddress['compass'], 0x00, 0x70)
	sensorBus.write_byte_data(i2cAddress['compass'], 0x01, 0xA0)
	sensorBus.write_byte_data(i2cAddress['compass'], 0x02, 0x00)
	
	time.sleep(0.5)

	global process
	while process == True:
		time.sleep(0.2)
		lock.acquire()

		rawCompass = sensorBus.read_i2c_block_data(i2cAddress['compass'], 0x03, 6)
		xCompass = rawCompass[0] * 256 + rawCompass[1]
		yCompass = rawCompass[2] * 256 + rawCompass[3]
		zCompass = rawCompass[4] * 256 + rawCompass[5]

		if xCompass > 32767:
			xCompass = xCompass - 65536

		if yCompass > 32767:
			yCompass = yCompass - 65536

		if zCompass > 32767:
			zCompass = zCompass - 65536
		
		heading = math.atan2(yCompass, xCompass)

		if(heading > 2*pi):
			heading = heading - 2*pi

		if(heading < 0):
			heading = heading + 2*pi

		headingAngle = int(heading * 180/pi)
		
		print("Heading Angle: %d" %headingAngle)
		#print("X: %d, Y: %d, Z: %d" %(xCompass,yCompass,zCompass))
		lock.release()


def hall():
	global tractorConnected

	global process
	while process == True:
		time.sleep(0.2)
		lock.acquire()

		if IO.input(pinPi['hall']) == True:
			tractorConnected = True
			print("Tractor Connected")
		else:
			tractorConnected = False
			print("Tractor Not Connected")
		lock.release()
		
def infrared():
	while process == True:
		time.sleep(0.1)
		
		lock.acquire()

		isLeftSensored = 1 if IO.input(pinPi['infraL']) == True else 0
		isCenterSensored = 2 if IO.input(pinPi['infraC']) == True else 0
		isRightSensored = 4 if IO.input(pinPi['infraR']) == True else 0

		sensored = isLeftSensored + isCenterSensored + isRightSensored
		
		if sensored == 1 and direction != 'right':
			direction = 'right'
			print("Change to Right")
		elif sensored == 2 and direction != 'center':
			direction = 'center'
			print("Change to Center")
		elif sensored == 4 and direction != 'left':
			direction = 'left'
			print("Change to Left")
		else:
			print("Infrared Sensor Error!!!")
			time.sleep(1)
		
		lock.release()

def sendStatus():
	global process
	global mainMotor1
	global mainMotor2
	global speed
	global direction
	global isObstacle
	global distance
	global compass

	lock.acquire()
	time.sleep(0.2)
	print("Main Motor1:", mainMotor1)
	print("Main Motor2:", mainMotor2)
	print("Direction: ", direction)
	lock.release()

os.system('clear')
print("Project [Tractor Pull] Start!!!")
time.sleep(0.5)

print("Creating Threads")

tChangeSpeed = threading.Thread(target=changeSpeed)
tChangeSpeed.start()
print("Created Threads[tChangeSpeed]")

tChangeDirection = threading.Thread(target=changeDirection)
tChangeDirection.start()
print("Created Threads[tChangeDirection]")

tDistance = threading.Thread(target=ultraDistance)
tDistance.start()
print("Created Threads[tDistance]")

tCompass = threading.Thread(target=compass)
tCompass.start()
print("Created Threads[tCompass]")

tHall = threading.Thread(target=hall)
tHall.start()
print("Created Threads[tHall]")

tInfrared = threading.Thread(target=infrared)
tInfrared.start()
print("Created Threads[tInfrared]")

print ("Creating Threads Done!!")


while 1:
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


tDistance.join()
print("Joined Tread [tDistance]");
tChangeSpeed.join()
print("Joined Tread [tChangeSpeed]");
tChangeDirection.join()
print("Joined Tread [tChangeDirection]");
tInfrared.join()
print("Joined Tread [tInfrared]");
tCompass.join()
print("Joined Tread [tCompass]");
tHall.join()
print("Joined Tread [tJoin]");

print ("DONE")

