# MQTT Client demo from Core-Electrons
# Modified by Jennifer McNeil
# Continuously monitor two different MQTT topics for data,
# check if the received data matches two predefined 'commands'

import tractor

import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

import threading
import sys

import time

ip = "172.22.20.29"
lock = tractor.lock()

def on_connect(client, userdata, flags, rc):
     
    # Subscribing in on_connect() - if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("Compass")
    client.subscribe("Current")
    client.subscribe("Obsticle")
    client.subscribe("Trailer")
    client.subscribe("Start")
    client.subscribe("Power")
# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
	
    print ()
    print (msg.topic)
    print (msg.payload.decode() )
    
    if msg.topic == "Start":
        #payload either 0, 1, or 2
        tractor.start = True if msg.payload.decode() == "True" else False
        print(SPEED)

def mqttMain():

	client = mqtt.Client()
	client.on_connect = on_connect
	client.on_message = on_message
	 
	client.connect(ip, 1883, 60)

	while True:
		lock.acquire()
		client.loop_start()
		publish.single("Compass",tractor.compass, hostname=ip)
		publish.single("Current",0, hostname=ip)
		publish.single("Obsticle",tractor.isObstacle, hostname=ip)
		publish.single("Trailer",tractor.isTractorConnected, hostname=ip)
			
		client.loop_stop()
		lock.release()
		time.sleep(1)
		a = a+1

tmqqt = threading.Thread(target=mqqtMain)
tmqqt.start()

	
