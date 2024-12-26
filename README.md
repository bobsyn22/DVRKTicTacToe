#Tic-Tac-Toe Robotic Arm using Davinci Robot

Project Video - https://www.youtube.com/watch?v=_DaB3bCAaQI

We developed a Python controls program to control the Da Vinci Research Kit Robot to play a game of Tic-Tac-Toe autonomously against a human player.

We use the onboard dual-cameras to get XYZ coordinate values of X & O pieces and the current board phase. We can get X & Y values from simple camera vision analysis, and use a camera pinhole model analysis to extract Z-depth information from the dual-camera setup.

Using these coordinate values received from our created camera vision system, we determine the robot's next move and generate movement XYZ trajectory commands using a trapezoidal feedrate profile. 

After completing its own move, the system will wait until another change in the board state to move again. Using this feedback system, we programed the DVRK to play tic-tac-toe automatically!
