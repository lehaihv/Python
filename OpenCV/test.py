import cv2 
import numpy as np 

cap = cv2.VideoCapture(0) 

while 1: 
	ret,frame =cap.read() 
	# ret will return a true value if the frame exists otherwise False 
	into_hsv =cv2.cvtColor(frame,cv2.COLOR_BGR2HSV) 
	# changing the color format from BGr to HSV 
	# This will be used to create the mask 
	L_limit=np.array([98,50,50]) # setting the blue lower limit 
	U_limit=np.array([139,255,255]) # setting the blue upper limit 
		

	b_mask=cv2.inRange(into_hsv,L_limit,U_limit) 
	# creating the mask using inRange() function 
	# this will produce an image where the color of the objects 
	# falling in the range will turn white and rest will be black 
	blue=cv2.bitwise_and(frame,frame,mask=b_mask) 
	
    ###
	#green color
	h_limit = np.array([98,50,50])
	#green color
	green_lower = np.array([25,52,72], np.uint8)
	green_upper = np.array([102,255, 255], np.uint8)
	green_mask = cv2.inRange(into_hsv, green_lower, green_upper)
	green = cv2.bitwise_and(frame,frame,mask=green_mask)
	
    #red color
	red_lower = np.array([136,87,111], np.uint8)
	red_upper = np.array([180,255, 255], np.uint8)
	red_mask = cv2.inRange(into_hsv, red_lower, red_upper)
	red = cv2.bitwise_and(frame,frame,mask=red_mask)


    ###
	# this will give the color to mask. 
	cv2.imshow('Original',frame) # to display the original frame 
	#cv2.imshow('Blue Detector',blue) # to display the blue object output 
	cv2.imshow('Blue Detector',red) # to display the blue object output 
	

	if cv2.waitKey(1)==27: 
		break
	# this function will be triggered when the ESC key is pressed 
	# and the while loop will terminate and so will the program 
cap.release() 

cv2.destroyAllWindows() 
