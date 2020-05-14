#simple apoximation to nbody problem
from random import randint
import time
import math
import json

#__CLOUDBOOK:GLOBAL__
body_list = [(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0),(10, 12, 76, -10, -7), (10, -71, -57, -4, 5), (10, 81, -52, 6, -10), (10, 30, 32, -9, 4), (10, -94, 20, -10, 0)]
body_new = []

#__CLOUDBOOK:CONST__
CONST_N = 100

#__CLOUDBOOK:PARALLEL__
def compute_body(single_body, iteration):
	global body_list
	global body_new
	
	fx=0.0
	fy=0.0
	for i in body_list:
		#print("i",i)
		delta_f = compute_contribution_force(single_body,i)
		fx = fx+delta_f[0]
		fy = fy+delta_f[1]
	ax = fx/float(single_body[0])
	ay = fy/float(single_body[0])
	vx = float(single_body[3])+ax
	vy = float(single_body[4])+ay
	x = float(single_body[1])+vx
	y = float(single_body[2])+vy	
	
	new_single_body = (single_body[0],x,y,vx,vy)
	#body_new[a].append(new_single_body)
	#body_new[0].append(new_single_body)
	#body_new.insert(0,new_single_body)
	#body_new[0].insert(0,new_single_body)
	body_new.append(new_single_body)
	#print("Exit from computebody")

#__CLOUDBOOK:LOCAL__
def compute_contribution_force(bodyA, bodyB):
	m1 = bodyA[0]
	x1 = bodyA[1]
	y1 = bodyA[2]
	vx1 = bodyA[3]
	vy1 = bodyA[4]
	m2 = bodyB[0]
	x2 = bodyB[1]
	y2 = bodyB[2]
	vx2 = bodyB[3]
	vy2 = bodyB[4]
	dx = math.sqrt((x1-x2)**2)
	if dx != 0:
		fx = (m1*m2)/(dx**2)
	else:
		fx=0
	if x2<x1:
		fx = -fx
	dy = math.sqrt((y1-y2)**2)
	if dy!=0:
		fy = (m1*m2)/(dy**2)
	else:
		fy=0
	if y2<y1:
		fy = -fy
	return (fx,fy)

#__CLOUDBOOK:MAIN__
def main():
	global body_list
	MAX_ITERATIONS = 3
	start = time.time()
	
	for j in range(MAX_ITERATIONS):
		print(j,"==>",body_list)
		print("starting iteration", j)
		for i in body_list:
			compute_body(i,j)
		#__CLOUDBOOK:SYNC:4__
		global body_new
		body_list = body_new
		body_new = []
		print("iteration ", j, " executed")
	end = time.time()
	print("duration: ", end-start)
	return body_list

main()
