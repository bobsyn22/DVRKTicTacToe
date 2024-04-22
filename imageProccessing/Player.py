
import os
import sys
import cv2
import argparse
import numpy as np

#from keras.models import load_model

import imageProccessing.imutils as imutils
import imageProccessing.detections as detections
from imageProccessing.alphabeta import Tic, get_enemy, determine

def find_circles(frame, dp=1.2, min_dist=100, param1=100, param2=30, min_radius=1, max_radius=100):
    # Convert to grayscale and apply Gaussian blur
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (9, 9), 2, 2)
    
    # Apply Hough Circle Transform
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp, min_dist,
                               param1=param1, param2=param2, minRadius=min_radius, maxRadius=max_radius)
    
    # If no circles were found, return an empty list
    if circles is None:
        return []

    # Convert the circle parameters (x, y, radius) to integers
    circles = np.round(circles).astype("int")
    #print("circle numbers", circles)
    #first_circle_coords = circles[0:2]
    #cv2.circle(frame, first_circle_coords, 10, (0, 0, 0), 2)
    #cv2.imshow('original', frame)
    #cv2.waitKey(0)
    return circles

def find_triangles(frame, canny_threshold1=50, canny_threshold2=150):
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Apply Gaussian blur
    gray = cv2.GaussianBlur(gray, (5, 5), 1.5)
    
    # Detect edges using the Canny edge detector
    edges = cv2.Canny(gray, canny_threshold1, canny_threshold2)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    triangle_centers = []
    for cnt in contours:
        # Approximate the contour to a polygon
        epsilon = 0.02 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        
        # Check if the polygon has 3 vertices (triangle)
        if len(approx) == 3:
            # Calculate the centroid of the triangle
            centroid_x = sum(point[0][0] for point in approx) // 3
            centroid_y = sum(point[0][1] for point in approx) // 3
            triangle_centers=[centroid_x, centroid_y]
    
    # Return the list of triangle center coordinates
    return triangle_centers

def find_board(frame, add_margin=True):
    """Detect the coords of the sheet of board the game will be played on"""
    thresh=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    stats = detections.find_corners(thresh)
    # First point is center of coordinate system, so ignore it
    # We only want board's corners
    corners = stats[1:, :2]
    corners = imutils.order_points(corners)
    # Get bird view of game board
    board = imutils.four_point_transform(frame, corners)
    if add_margin:
        board = board[10:-10, 10:-10]
    return board, corners

def find_grid(frame):
    gray=contrast_image(frame)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    #cv2.imshow("image",gray)
    #cv2.waitKey(0)
    #cv2.destroyAllWindows()
    corners = cv2.goodFeaturesToTrack(gray, 20, 0.01, 65) #N best corners from image, minimum quality from 0-1, min euc distance between corners
    for corner in corners:
        # corner is array with x,y vals inside another array.
        x, y = corner.ravel()  # removes interior arrays.
        #cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)  # -1 fills the circle
    return corners

def find_color(cell):
    # Convert to HSV
    hsv = cv2.cvtColor(cell, cv2.COLOR_BGR2HSV)

    # Define color ranges for detection
    lower_blue = np.array([110, 50, 50])
    upper_blue = np.array([130, 255, 255])
    lower_purple = np.array([130, 50, 50])
    upper_purple = np.array([160, 255, 255])

    # Threshold the HSV image to get only blue and purple colors
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
    purple_mask = cv2.inRange(hsv, lower_purple, upper_purple)

    # Check the presence of colors
    if np.any(blue_mask):
        return 'O'  # Blue for 'O'
    elif np.any(purple_mask):
        return 'X'  # Purple for 'X'
    else:
        return None

def find_centers(image, lower_blue, upper_blue, lower_purple, upper_purple):
    # Convert the image to RGB color space
    image_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Create masks for blue and purple colors
    blue_mask = cv2.inRange(image_hsv, lower_blue, upper_blue)
    purple_mask = cv2.inRange(image_hsv, lower_purple, upper_purple)

    # Find contours for the blue blocks
    blue_contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Find contours for the purple blocks
    purple_contours, _ = cv2.findContours(purple_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Calculate the center of each blue contour
    blue_centers = []
    for cnt in blue_contours:
        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            blue_centers.append((cX, cY))

    # Calculate the center of each purple contour
    purple_centers = []
    for cnt in purple_contours:
        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            purple_centers.append((cX, cY))

    return blue_centers, purple_centers
'''
def get_board_template(frame):
    """Returns 3 x 3 grid, a.k.a the board"""
    # Find grid's center cell, and based on it fetch
    # the other eight cells
    thresh=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    #middle_center = detections.contoured_bbox(thresh) #This is messing up.
    #center_x, center_y, width, height = middle_center
    #print("middle center= ", middle_center)
    center_x,center_y=find_circles(frame)
    width=100
    height=100
    middle_center = center_x,center_y,width,height
    #cv2.circle(frame, (center_x, center_y), 5, (0, 255, 0), -1)  # -1 fills the circle

    # Useful coords
    left = center_x - width
    right = center_x + width
    top = center_y - height
    bottom = center_y + height

    # Middle row
    middle_left = (left, center_y, width, height)
    middle_right = (right, center_y, width, height)
    # Top row
    top_left = (left, top, width, height)
    top_center = (center_x, top, width, height)
    top_right = (right, top, width, height)
    # Bottom row
    bottom_left = (left, bottom, width, height)
    bottom_center = (center_x, bottom, width, height)
    bottom_right = (right, bottom, width, height)
    # Grid's coordinates

    corners = find_grid(frame)#works!

    for corner in corners:
        x,y = corner.ravel()
        #print(x,y) #works!

    return [top_left, top_center, top_right,
            middle_left, middle_center, middle_right,
            bottom_left, bottom_center, bottom_right]
'''

def get_board_template(frame):
    thresh=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    circle_coords=find_circles(frame)
    circle_coords=circle_coords.reshape(-1,3)
    sorted_groups = []
    circle_coords = circle_coords[np.argsort(circle_coords[:, 0])]
    # Since we know we're dealing with groups of 3, iterate through the sorted array in steps of 3
    for i in range(0, len(circle_coords), 3):
        # Extract the current group of 3
        group = circle_coords[i:i+3]
        
        # Sort this group by the y-value
        sorted_group = group[np.argsort(group[:, 1])]
        
        # Append the sorted group to our list of sorted groups
        sorted_groups.append(sorted_group)
    sorted_groups=np.vstack(sorted_groups)
    sorted_groups=sorted_groups[:,:-1]
    print("sorted",sorted_groups)

    bottom_left = sorted_groups[0]
    bottom_center = sorted_groups[1]
    bottom_right = sorted_groups[2]
    middle_left = sorted_groups[3]
    middle_center=sorted_groups[4]
    middle_right = sorted_groups[5]
    top_left = sorted_groups[6]
    top_center = sorted_groups[7]
    top_right = sorted_groups[8]
    return [top_left, top_center, top_right,
            middle_left, middle_center, middle_right,
            bottom_left, bottom_center, bottom_right]
    #print(circle_coords)
    

def contrast_image(img):
	# converting to LAB color space
	lab= cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
	l_channel, a, b = cv2.split(lab)

	# Applying CLAHE to L-channel
	# feel free to try different values for the limit and grid size:
	clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
	cl = clahe.apply(l_channel)

	# merge the CLAHE enhanced L-channel with the a and b channel
	limg = cv2.merge((cl,a,b))

	# Converting image from LAB Color model to BGR color spcae
	enhanced_img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

	# Stacking the original image with the enhanced image
	result = np.hstack((img, enhanced_img))
	#cv2.imshow('Result', result)
	return result


#########################################################
    #Read image
if __name__ == '__main__':
    img = cv2.imread('/Users/ben/Downloads/Test.jpeg')

    #define HSV value ranges
    lower_blue = np.array([50, 200, 200])
    upper_blue = np.array([107, 255, 255])
    lower_purple = np.array([100, 200, 190])
    upper_purple = np.array([150, 255, 200])

    blue_centers, purple_centers = find_centers(img, lower_blue, upper_blue, lower_purple, upper_purple)#works!

    for center in blue_centers:
        cv2.circle(img, center, radius = 5, color = (0,255,0), thickness = -1)#works!

    for center in purple_centers:
        cv2.circle(img, center, radius = 5, color = (0,255,0), thickness = -1)#works!

    corners = find_grid(img)#works!

    for corner in corners:
        x,y = corner.ravel()
        print(x,y) #works!


    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, board_thresh = cv2.threshold(gray, 170, 255, cv2.THRESH_BINARY_INV)
    state = get_board_template(board_thresh)
    print(state)


    #now test find_color
    # Example coordinates for a cell, replace with actual coordinates of interest
    x, y, w, h = (526, 628, 520, 502)
    cell_roi = img[y:y+h, x:x+w]  # Extract the cell from the image
    result = find_color(cell_roi)
    print(f"The cell contains: {result}")


    '''cv2.imshow('frame',img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()'''

                #board = draw_shape(board, shape, (x, y, w, h))
                #this function draws an X or O on TEMPLATE, which is the gamestate array. Find_color gets what
                # cell is X or O (purple or blue) eventually, instead of drawing a shape, we want it to place
                # a block. Now it already assigns its next move, so we want
        # Top row
    
