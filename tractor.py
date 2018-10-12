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
i2cAddress = {'ultrawave' : 0x00, 'infrared' : 0x00}
sensorBus = smbus.SMBus(channel)

#Instruction
#read_byte_data(int addr, char cmd)
#read_byte(int addr)

lock = threading.Lock()
pinPi = {'servoMotor': 13, 'mainMotor1': 19, 'mainMotor2': 26, 'hall':14}

#Max Value - Left: 1000 Center: 1500 Right: 2000
directionVar = {'left': 1250, 'center':1520, 'right': 1770}

#IO.setwarnings(False)           #do not show any warnings
IO.setmode (IO.BCM)         #we are programming the GPIO by BCM pin numbers. (PIN35 as ‘GPIO19’)
IO.setup(pinPi['servoMotor'],IO.OUT)           # initialize GPIO19 as an output.
IO.setup(pinPi['mainMotor1'],IO.OUT)
IO.setup(pinPi['mainMotor2'],IO.OUT)
IO.setup(pinPi['hall'],IO.IN)

pinDirection = PWM.Servo()         #GPIO13 as PWM output, with 20ms period
pinDirection.set_servo(pinPi['servoMotor'], directionVar['center']  )

direction = 'center'
speed = 0

def changeDirection():
	global direction
	pinDirection.set_servo(pinPi['servoMotor'], directionVar[direction])

def sendStatus():
	global mainMotor1
	global mainMotor2
	global direction
	print("Main Motor1:", mainMotor1)
	print("Main Motor2:", mainMotor2)
	print("Direction: ", direction)

def motorSpeed():
	global speed

	if speed == 0:
		IO.output(pinPi['mainMotor1'], 0)
		IO.output(pinPi['mainMotor2'], 0)
	if speed == 1:
		IO.output(pinPi['mainMotor1'], 0)
		IO.output(pinPi['mainMotor2'], 1)
	if speed == 2:
		IO.output(pinPi['mainMotor1'], 1)
		IO.output(pinPi['mainMotor2'], 0)

#tSendStatus = threading.Thread(target=sendStatus)
#tSendStatus.start()

while 1:
	temp = input("dirction: ")
	if temp == 'l':
		direction = 'left'
	elif temp == 'c':
		direction = 'center'
	elif temp == 'r':
		direction = 'right'
	else:
		print("Wrong input")
	changeDirection()
	
	speed = int(input("speed [0-2]:"))
	motorSpeed()

print ("DONE")
