# -*- coding: utf-8 -*-
import RPi.GPIO as IO    #calling header file which helps us use GPIO’s of PI
from RPIO import PWM
import time                #calling time to provide delays in program
import threading
import curses
import smbus


#I2C Setup
channel = 1
device_reg_mode = 0x00
i2cAddress = {'ultrawave' : 0x00, 'infrared' : 0x00, 'compass' : 0x1E}
sensorBus = smbus.SMBus(channel)

process =1

#Instruction
#read_byte_data(int addr, char cmd)
#read_byte(int addr)

lock = threading.Lock()
pinPi = {'servoMotor': 13, 'mainMotor1': 19, 'mainMotor2': 26, 'hall':14, 'ultraTrigger' : 21, 'ultraEcho' : 20}

#Max Value - Left: 1000 Center: 1500 Right: 2000
directionVar = {'left': 1250, 'center':1520, 'right': 1770}

#IO.setwarnings(False)           #do not show any warnings
IO.setmode (IO.BCM)         #we are programming the GPIO by BCM pin numbers. (PIN35 as ‘GPIO19’)
IO.setup(pinPi['servoMotor'],IO.OUT)           # initialize GPIO19 as an output.
IO.setup(pinPi['mainMotor1'],IO.OUT)
IO.setup(pinPi['mainMotor2'],IO.OUT)
IO.setup(pinPi['ultraTrigger'],IO.OUT)
IO.setup(pinPi['ultraEcho'],IO.IN)
#IO.setup(pinPi['hall'],IO.IN)

pinDirection = PWM.Servo()         #GPIO13 as PWM output, with 20ms period
pinDirection.set_servo(pinPi['servoMotor'], directionVar['center']  )

direction = 'center'
speed = 0
distance = 0

def changeSpeed():
	global speed
	while process==1:
		lock.acquire()
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
		time.sleep(0.2)

def changeDirection():
	global direction
	while process==1:
		lock.acquire()
		pinDirection.set_servo(pinPi['servoMotor'], directionVar[direction])
		time.sleep(0.5)
		lock.release()
		time.sleep(0.2)
		print("change Direction\n")
#		time.sleep(1)

def ultraDistance():
	global distance
	global speed
	while process == 1:
		lock.acquire()
		IO.output(pinPi['ultraTrigger'], True)
		time.sleep(0.00001)
		IO.output(pinPi['ultraTrigger'], False)
		
		
		initTime = time.time()

		while IO.input(pinPi['ultraEcho']) == False:
			StartTime = time.time()
			if StartTime-initTime > 1:
				print("Error")
				break
		while IO.input(pinPi['ultraEcho']) == True:
			StopTime = time.time()
			if StopTime-initTime > 1:
				print("Error")
				break
		TimeElapsed = StopTime - StartTime
		distance = round((TimeElapsed * 17150),2)
		
		if distance < 1.0:
			continue #less than 1cm is error	
		print("%.1f cm" %distance)
		#test code
		if distance < 60.0:
			speed = 0
		else:
			speed = 1
		#
		time.sleep(0.2)
		lock.release()
		time.sleep(0.2)

def sendStatus():
	global mainMotor1
	global mainMotor2
	global direction
	print("Main Motor1:", mainMotor1)
	print("Main Motor2:", mainMotor2)
	print("Direction: ", direction)


tChangeSpeed = threading.Thread(target=changeSpeed)
tChangeSpeed.start()

tChangeDirection = threading.Thread(target=changeDirection)
tChangeDirection.start()

tDistance = threading.Thread(target=ultraDistance)
tDistance.start()

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


tDistance.join()
tChangeSpeed.join()
tChangeDirection.join()

print ("DONE")

