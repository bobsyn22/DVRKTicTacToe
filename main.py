#!/usr/bin/env python
import sys
import os
import dvrk
import math
import sys
import rospy
import numpy as np
import PyKDL
import argparse
import time

# Get the absolute paths of the folders
image_processing_path = os.path.abspath("imageProcessing")
trajectory_planning_path = os.path.abspath("trajecPlanning")

# Append the paths to sys.path (modify these paths if your folders are located differently)
sys.path.append(image_processing_path)
sys.path.append(trajectory_planning_path)

import imageProccessing.camera as camera # DVRK camera code
import trajecPlanning.Trajectory_PSM as trajecTools
import imageProccessing.imageProcessingTools as imTools 
import imageProccessing.AnalysisOpenCV as AnalysisOpenCV
import imageProccessing.tictactoe as tictactoe
if __name__ == '__main__':
	
	# ----- ROS Setup ---------
	rospy.init_node('mainNode')
	r = rospy.Rate(1000) #per second

	#Camera initiation
	left_cam = camera.camera('left')
	right_cam = camera.camera('right')
	ecm = dvrk.arm('ECM')
 
	#Gets coords of board. Uses circle detection. Board is game state.
	boardR = imTools.findBoardCoords(right_cam.get_image())
	boardL = imTools.findBoardCoords(left_cam.get_image())
	status = 9
	player = 'X' 

	def TrajecPlanningTest(): 
		TrajctoryMain = trajecTools.TrajctoryNode(homeLocation = (-.04,.09))
		TrajctoryMain.defualtZLayer = -.04
		time.sleep(1)
		TrajctoryMain.returnHomeFree()
		time.sleep(1)
		TrajctoryMain.pickAndPlace2(pickLocation=(-.08,.026), placeLocation=(-.001,.007))
	
	TrajecPlanningTest()


	while not rospy.is_shutdown():

		#the first few calls happen before an image is sent by dvrk
		#so the image variable (from *_cam.get_image) will be empty lists
		#sleep until an image is sent and the image variable is no longer a list (should be CV image)
		while isinstance(right_cam.get_image(), list):
			r.sleep()
			#print('sleeping')
		#else:
			#print('cv file recieved')


		#-------------Get 2D coordinates from image
		
		if status%2==1: #When status is odd, it waits for input, gets new board state, then u[]
			input("Player Turn - Tell me when you placed your object")
			boardR = imTools.getNewBoardState(boardR,status,right_cam.get_image()) #Changes game state and decrements status
		elif status%2==0:
			print('Computer Turn')
			PickupCoordsR=imTools.findPickUpCoords(right_cam.get_image())
			
			#Get board index and putdown coords from cell
			if tictactoe.check_winner(boardR,player):
				print("Player Wins")
			PutdownCoordsR=boardR[tictactoe.play(boardR,player)]
			#3Dpickup, 3Dputdown = findDepth(pickup,putdown)
			#Trajectory Planning
			boardR=imTools.getNewBoardState(boardR,status,right_cam.get_image())

			if tictactoe.check_winner(boardR,'O'):
				print("computer wins")
			if tictactoe.check_draw(boardR):
				print("draw")
			
		r.sleep()
