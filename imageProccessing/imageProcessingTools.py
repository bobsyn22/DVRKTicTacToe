#!/usr/bin/env python

# Author: Team3
# Date: 2024-03-08

'''
This file initiates node for image processing. 
Subscribes to both cameras, processes images. 
Based on image processing, code either waits for player to move, moves ECM so board is in frame,
	or doesn't move.
Image processing determines tictactoe matrix of play, coordinates of board, coordinates of 1 of remaining pieces
3D Coordinates for piece-to-pick-up and spot-to-put-down are published to "coordinates_3d" topic

#TODO
	- all the image processing stuff (Ben)
	- camera calibration matrix
	- verification (all!)
	
	- instead of while-looping for player to make move, maybe this should be another node?
		- this-node gets images and sends them to some player-done task
		- when player has moved, player-done task publishes something (like a locking mechanism)
		- this-node subscribes to topic and finishes function when it receives topic

'''

#Neccessary libraries
import rospy
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image
from sensor_msgs.msg import JointState
from cv_bridge import CvBridge, CvBridgeError
from geometry_msgs.msg import TransformStamped
import std_msgs
import cv2 #Vision toolbox
import numpy as np #Matrix toolbox
import imageProccessing.Player as Player #Bens vision code
import dvrk #DVRK toolbox
import sys
from scipy.spatial.transform import Rotation as R
import os
#import imageProccessing.camera as camera # DVRK camera code Comment bottom and uncomment this
import imageProccessing.camera as camera
import imageProccessing.tictactoe as tictactoe


#Constants for MoveECM function & status variable
leftBoundary	= 150
rightBoundary 	= -150
upperBoundary 	= 150
lowerBoundary 	= -150

#keeps track of coordinates and value (X,O,blank)
class boardsquare:
	def __init__(self,x_coord,y_coord,tile):
		self.x_coord=x_coord
		self.y_coord=y_coord
		self.tile=tile #X,O,blank

	def isFull(self):
		return not (self.tile is None)
		

#Function is used to turn 2d coordinates into 3d coordinates
def findDepth(ur,vr,ul,vl):

	#Calibration from lab (do not edit):
	#ur = 144, vr =0, ul=89. vl=200
	#Assume its in pixel coords
	#is camera calibrations matrices in different coords?
	
	calib_matrixR = np.array([[1996.53569, 0, 936.08872, -11.36134],
				 [0, 1996.53569, 459.10171, 0],
				 [0, 0, 1, 0,]])
	
	calib_matrixL = np.array([[1996.53569, 0, 936.08872, 0],
				[0, 1996.53569, 459.10171, 0],
				[0, 0, 1, 0,]])
	
	#^^ the ros code for these outputs = [ fx' 0 cx' Tx
	#									0 fy' cy' Ty
	#									0 0 1 0]
	# (see sensor_msgs/CameraInfro Message)
	# So we don't need to decompose anything (red comments below) as we usually would need to
	#instead:
	fx = calib_matrixL[0][0]
	fy = calib_matrixL[1][1]
	ox = calib_matrixL[0][2]
	oy = calib_matrixL[1][2]
	b = -(calib_matrixR[0][3]/fx) #Tx = -fx' * B according to documentation
	
	'''
	#use qr factorization to get intrinsic and extrinsic matrices
	#(returns Q,R which are 3x3 matrixes. R is upper-triangular meaning its the intrinsic matrix)
	#A (matrix) is decomposed into QR, where Q is orthogonal matrix and R is upper triangle matrix.

	ext_matrix_left, int_matrix_left = np.linalg.qr(calib_matrixL[0:3,0:3], mode='reduced')
	ext_matrix_right, int_matrix_right = np.linalg.qr(calib_matrixR[0:3,0:3], mode='reduced')
	
	fx = int_matrix_right[0][0]
	fy = int_matrix_right[1][1]
	ox = int_matrix_right[0][2]
	oy = int_matrix_right[1][2]

	t_matrix = np.linalg.inv(int_matrix_right)*calib_matrixR[:,3]
amera.
	#if right camera is the main camera
	#then difference btw them is tx of left camera
	b = t_matrix[0]
	'''

	#image processing give (u,v) of both cameras
	#(ur,vr) for right camera; (ul,vl) for left;
	x = (b*(ul-ox)/(ul-ur))
	y = (b*fx*(vl-oy)/(fy*(ul-ur)))
	z = (b*fx/(ul-ur))

	#shift x so its between the two cameras
	x -= (b/2)

	coords_3d = np.array([x, y, z], dtype=np.float32)

	return(coords_3d)

def findBoardCoords(image):
	cells = Player.get_board_template(image)
	board = [None] * 9 
	for i in range(9):
		xcoord=cells[i][0]
		ycoord=cells[i][1]
		shape=None
		board[i]=boardsquare(xcoord,ycoord,shape)
	return board

def compare(board, image, tolerance=20):
    current_circles = Player.findcurrentboardcoords(image)  # Get current state from the image
    current_positions = [(c[0], c[1]) for c in current_circles]  # List of current (x, y) positions

    # Initialize a match found flag for each board square
    matched = [False] * len(board)

    # Loop through each board square and determine the closest current circle
    for i, square in enumerate(board):
        closest_dist = float('inf')
        for (cx, cy) in current_positions:
            dist = np.sqrt((square.x_coord - cx) ** 2 + (square.y_coord - cy) ** 2)
            if dist < closest_dist:
                closest_dist = dist

        # If the closest circle is within the tolerance and the square is not yet covered, it's considered unchanged
        if closest_dist <= tolerance:
            matched[i] = True

    # Update board squares where no close circle was found
    for i, square in enumerate(board):
        if not matched[i] and square.tile is None:
            square.tile = 'X'  # Mark the square as covered with an 'X' or 'O'

    return board


def procImage(image):
	board, coords_2d = findBoardCoords(image)

	#For now, lets assume player is always 'x'
	#if player is None: #player=readboardforplayer
	player = 'X' 
	

	#coordinates of one of the pieces (off to the side) to pick up
	#coord_pickup=commented out becuase no circle
 
	#coords_pickup = Player.find_circles(topdownimage)
	coords_pickup=[0,0]
	#Chatgpt function to turn 1d array into 2d numpy array for later usage.
	coords_2d= np.array([[(board[row * 3 + col].x_coord, board[row * 3 + col].y_coord) for col in range(3)] for row in range(3)])
	return board, coords_2d, coords_pickup, player


def end_game (winner):
	i=0
	#Move ecm to home position
	if winner is 1:
		print("Player Won")
	elif winner is 2:
		print("DVRK Won")
	elif winner is 3:
		print("Draw Game")
	else:
		("Unknown Value inputed")


if __name__ == "__main__":

	#create node
	rospy.init_node('imageProc')

	#initiate camera objects - these are subscribed to raw_images from dvrk cameras
	left_cam = camera.camera('left')
	right_cam = camera.camera('right')

	#initiate ecm object
	ecm = dvrk.arm('ECM')

	r = rospy.Rate(100)

	print("started node")

	while not rospy.is_shutdown():

		while isinstance(right_cam.get_image(), list):
			r.sleep()
			#print('sleeping')
		print('complete')
		'''	
		#image processing function takes OpenCV image
		status, board, coords_2dR, coords_pickupR, player = procImage(right_cam.get_image())

		#if image is not in frame, move ECM
		while(status is not 0):
			moveECM(status,ecm, r)
			#look again
			status, board, coords_2dR, coords_pickupR, player = procImage(right_cam.get_image())

		#status is 0, get left image now
		_, _, coords_2dL, coords_pickupL, _ = procImage(left_cam.get_image())

		#play tictactoe
		ind_to_play, winner = tictactoe.play(board, player)

		#someone has won game or draw. end game sequence
		if(winner is not 0):
			end_game()

		#identify piece to play (x,y) in both cameras
		coords_3d_pickup = findDepth(coords_pickupR[0], coords_pickupR[1],
								coords_pickupL[0], yl = coords_pickupL[1])

		#identify location to play (x,y) in both cameras
		xr, yr = coords_2dR[ind_to_play]
		xl, yl = coords_2dL[ind_to_play]
		coords_3d_putdown = findDepth(xr,yr,xl,yl)


		#combine into 1x6 array [pickup_coords, putdown_coords]
		coords_3d = np.concatenate((coords_3d_pickup, coords_3d_putdown), axis=None)
		#self.pub.publish(coords_3d)
		'''
		r.sleep()