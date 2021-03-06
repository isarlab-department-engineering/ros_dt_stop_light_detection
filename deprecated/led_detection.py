#!/usr/bin/env python

# this node will be deprecated in favour of a detection that use services and not topic
# the new version will use geometry/twist message and not String 
# the new version will communicate directly with master node

from __future__ import print_function
import sys,rospy,cv2, numpy, roslib
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError

# change threshold purple -> blue

# init cvbridge
bridge = CvBridge()

''' 
HERE GOES ALL PARAMETERS 
'''
# stop light = purple
# front light = green
# purple hsv treshold boundaries
purpleLower = numpy.array([125,180,50],dtype = "uint8")
purpleUpper = numpy.array([145,255,155],dtype = "uint8")
# green hsv treshold boundaries
greenLower = numpy.array([60,200,60],dtype = "uint8")
greenUpper = numpy.array([70,255,155],dtype = "uint8")
# treshold detection of mean value
tresholdPurpleDetection = 100
tresholdGreenDetection = 100
purpleSectors = 20
greenSectors = 20
count = 0
# suppose you will always find lights in the low part of image
# image have 160*128 resolution
# treshold for crop image
ymin = 88
ymax = 118
xmin = 30
xmax = 130
# variables for sectors
# NOTE. xmax-xmin must be divisibile for xsector, same for ymax-ymin with ysector
xsectors = 20
ysectors = 10
# dimension of sectors
xsectordim = (xmax-xmin)/xsectors
ysectordim = (ymax-ymin)/ysectors
# ros variables
ledControlPublish = rospy.Publisher("led_control_topic",String,queue_size=10)
# debbuging topic
croppedPublish = rospy.Publisher("cropped_image",Image,queue_size=10)
notTassellatedPurplePublish = rospy.Publisher("led_detector_purple_not_tassellated",Image,queue_size=10)
notTassellatedGreenPublish = rospy.Publisher("led_detector_green_not_tassellated",Image,queue_size=10)
tassellatedPurplePublish = rospy.Publisher("led_detector_purple_tassellated",Image,queue_size=10)
tassellatedGreenPublish = rospy.Publisher("led_detector_green_tassellated",Image,queue_size=10)
''' 
END PARAMETERS
'''

def detector():
	rospy.init_node('led_detector',anonymous=True)
	rospy.Subscriber("slow_image_topic",Image,callback)
	try:
		rospy.spin()
	except KeyboardInterrupt:
		print("Shutting down")

def callback(data):
   try:
	global count
	rospy.loginfo(rospy.get_caller_id()+"Received an image")
	# import cv image
	cvImage = bridge.imgmsg_to_cv2(data)
	# crop image 
	croppedImage = cvImage[ymin:ymax,xmin:xmax]
	croppedPublish.publish(bridge.cv2_to_imgmsg(croppedImage))
	# convert in hsv format
	hsvImage = cv2.cvtColor(croppedImage,cv2.COLOR_BGR2HSV)
	# generate red mask to test detection
	purpleMask = cv2.bitwise_and(hsvImage,hsvImage,mask=cv2.inRange(hsvImage,purpleLower,purpleUpper))
	greenMask = cv2.bitwise_and(hsvImage,hsvImage,mask=cv2.inRange(hsvImage,greenLower,greenUpper))
	notTassellatedPurplePublish.publish(bridge.cv2_to_imgmsg(purpleMask))
	notTassellatedGreenPublish.publish(bridge.cv2_to_imgmsg(greenMask))
	# tassellation of calculated purplemask 	
	for y in range(ysectors):
		for x in range(xsectors):
			mean = numpy.mean(purpleMask[y*ysectordim:(y+1)*ysectordim,x*xsectordim:(x+1)*xsectordim])
			for i in range(y*ysectordim,(y+1)*ysectordim):
				for j in range(x*xsectordim,(x+1)*xsectordim):
					purpleMask[i][j] = mean
	# tassellation of calculated greenmask 	
	for y in range(ysectors):
		for x in range(xsectors):
			mean = numpy.mean(greenMask[y*ysectordim:(y+1)*ysectordim,x*xsectordim:(x+1)*xsectordim])
			for i in range(y*ysectordim,(y+1)*ysectordim):
				for j in range(x*xsectordim,(x+1)*xsectordim):
					greenMask[i][j] = mean
	count = 0
	# search purple led in calulcated sectors
	for y in range(ysectordim/2,ymax-ymin,ysectordim):
		for x in range(xsectordim,xmax-xmin,xsectordim):
			 if(purpleMask[y][x][0] > tresholdPurpleDetection):
				count = count + 1
				if count > purpleSectors:
					rospy.loginfo("FOUND PURPLE")
					ledControlPublish.publish("stop")
					break
		else:
			continue
		break
	count = 0 
	# search green led in calulcated sectors
	for y in range(ysectordim/2,ymax-ymin,ysectordim):
		for x in range(xsectordim,xmax-xmin,xsectordim):
			 if(greenMask[y][x][0] > tresholdGreenDetection):
				count = count + 1
				if count > greenSectors:
					rospy.loginfo("FOUND GREEN")
					ledControlPublish.publish("front")
					break
		else:
			continue
		break
	tassellatedPurplePublish.publish(bridge.cv2_to_imgmsg(purpleMask))
	tassellatedGreenPublish.publish(bridge.cv2_to_imgmsg(greenMask))
   except CvBridgeError as e:
	print(e)
	
if __name__ == '__main__':
	try:
		detector()
	except rospy.ROSInterruptException:
		pass
