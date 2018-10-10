# -*- coding: utf-8 -*-
import RPi.GPIO as IO    #calling header file which helps us use GPIO’s of PI
import time                #calling time to provide delays in program
import threading
import curses

lock = threading.Lock()
pinPi = {'servoMotor': 19, 'mainMotor': 26}

IO.setwarnings(False)           #do not show any warnings
IO.setmode (IO.BCM)         #we are programming the GPIO by BCM pin numbers. (PIN35 as ‘GPIO19’)
IO.setup(pinPi['servoMotor'],IO.OUT)           # initialize GPIO19 as an output.
IO.setup(pinPi['mainMotor'],IO.OUT)

pinDirection = IO.PWM(19,50)          #GPIO19 as PWM output, with 50Hz frequency
pinDirection.start(7.5)                 #generate PWM signal with 7.5%(1.5ms) duty cycle

direction = 'center'

def changeDirection():
    # 90: 10%, 2ms
    # 0: 7.5%, 1.5ms
    # -90: 5%, 1ms
    while 1:
    	global direction
    	speedVar = {'left': 8, 'center':7.5, 'right': 7}
    	pinDirection.ChangeDutyCycle(speedVar[direction])

def sendStatus():
	while 1:
		print("Main Motor:", mainMotor)
		print("Direction: ", direction)
		time.sleep(1)

#while 1:                               #execute loop forever
mainMotor = True
IO.output(pinPi['mainMotor'], mainMotor)
tChangeDirection = threading.Thread(target=changeDirection)
tSendStatus = threading.Thread(target=sendStatus)

tChangeDirection.start()
tSendStatus.start()

time.sleep(5)

direction = 'left'
time.sleep(5)

direction = 'right'
time.sleep(5)

direction = 'center'
time.sleep(5)

mainMotor = False
IO.output(pinPi['mainMotor'], mainMotor)

