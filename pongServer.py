# =================================================================================================
# Contributing Authors:	    Caleb Mpungu
# Email Addresses:          smp222@uky.edu
# Date:                     11/19/2025
# Purpose:                 Server that manages multiplayer pong game between two clients
# Misc:                     <Not Required.  Anything else you might want to include>
# =================================================================================================

import socket
import threading

# Use this file to write your server logic
# You will need to support at least two clients
# You will need to keep track of where on the screen (x,y coordinates) each paddle is, the score 
# for each player and where the ball is, and relay that to each client
# I suggest you use the sync variable in pongClient.py to determine how out of sync your two
# clients are and take actions to resync the games

# These variables store the current state of the game that needs to be synchronized between clients
leftPaddleY = 215    # Y position of left player's paddle (Player 1)
rightPaddleY = 215   # Y position of right player's paddle (Player 2)


# : Add ball position (ballX, ballY) and scores (leftScore, rightScore) here
#-----------------------------------------------------------------------------------------------------------

#Handles communcation witht he left player
#updates leftpaddle based on the data and sends to rightpaddle

def handleLeftClient(client_socket):
    global leftPaddleY, rightPaddleY
    while True:
        try:
            #receives position from left player
            data = client_socket.recv(1024).decode()
            #disconnect if not recieved
            if not data:
                break
                #update the left paddle's position
            leftPaddleY = int(data)
                #send to right paddle position
                #conver to string 
            client_socket.send(str(rightPaddleY).encode())
        except:
            break
        #close when done 
    client_socket.close()

def handleRightClient(client_socket):
    global leftPaddleY, rightPaddleY
    while True:
        try:
            data= client_socket.recv(1024).decode()
            if not data:
                break
            rightPaddleY = int(data)

            client_socket.send(str(leftPaddleY).encode())
        except:
            break
    client_socket.close()

# Server set up
# Create a TCP/IP socket
# AF_INET = IPv4, SOCK_STREAM = TCP (reliable, connection-oriented)
server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
# Bind the socket to port 12345 on all available network interfaces
# '' means listen on all interfaces (localhost, network IP, etc.)
server.bind(("",12345))
# start listening for connection
# 2 == alow up to connection 
server.listen(2)
print("Waiting for players...")
#accpt first client connection (P1 - Left Paddle)
client1,addr1 = server.accept()
print(f"Player 1 connected from {addr1}")
#accpt first client connection (P2 - Right Paddle)

client2, addr2 = server.accept()
print(f"Player 2 connected from {addr2}")

# Create a thread to handle Player 1
# target = function to run
# .start() begins running the thread (doesn't wait for it to finish)
threading.Thread(target=handleLeftClient,args=(client1,)).start()

# Create a thread to handle Player 2
# Both threads now run simultaneously, each handling their own client
threading.Thread(target=handleRightClient,args=(client2,)).start()


