# =================================================================================================
# Contributing Authors:	    Caleb Mpungu
# Email Addresses:          smp222@uky.edu
# Date:                     11/19/2025
# Purpose:                 Server that manages multiplayer pong game between two clients
# Misc:                     <Not Required.  Anything else you might want to include>
# =================================================================================================

# Synchronization 
import socket
import threading
import time 

# Use this file to write your server logic
# You will need to support at least two clients
# You will need to keep track of where on the screen (x,y coordinates) each paddle is, the score 
# for each player and where the ball is, and relay that to each client
# I suggest you use the sync variable in pongClient.py to determine how out of sync your two
# clients are and take actions to resync the games

# Global Game State

WIN_SCORE = 5 # points needed to win one game

game_over = False # true when someone reaches WIN_SCORE
winner = None # assign whoever reachs WIN_SCORE

leftWantsReplay = False
rightWantsReplay = False

screenWidth = 640
screenHeight = 480

# These variables store the current state of the game that needs to be synchronized between clients
leftPaddleY = 215    # Y position of left player's paddle (Player 1)
rightPaddleY = 215   # Y position of right player's paddle (Player 2)

# Ball state (starts in middle of screen)
ballX = screenWidth // 2 
ballY = screenWidth // 2

# Velocity in X and Y direction
ballVX = 5 
ballVY = 3 

# Scores
leftScore = 0
rightScore = 0

# Paddle movement flags from clients (up, down, stop)
leftMove = "stop"
rightMove = "stop"

# Store client sockets
leftClient = None
rightClient = None
# All connected client sockets (2 players + any spectators)
clients = []

# Prevent threads writing at same time on a global variable
stateLock = threading.Lock()

game_running = True # Used to accept extra clients

# Update ball position (ballX, ballY) and scores (leftScore, rightScore), velocities, and paddle position
# Execute client commands 
def game_loop():
    global leftPaddleY, rightPaddleY
    global leftMove, rightMove
    global ballX, ballY, ballVX, ballVY
    global leftScore, rightScore

    FPS = 60 # frames per second
    frame_delay = 1.0 / FPS

    while game_running:

        # Game over when someones reaches win score
        # Send game over message to all clients 
        if game_over:
            state_msg = f"GAME_OVER Winner={winner}"
        
        # Both players want to play again
        if leftWantsReplay and rightWantsReplay:
            # Reset game state
            leftScore = 0
            rightScore = 0

            # Reset paddles
            leftPaddleY = screenHeight // 2
            rightPaddleY = screenHeight // 2

            # Reset ball
            ballX = screenWidth // 2
            ballY = screenHeight // 2
            ballVX = 5
            ballVY = 3

            # Reset replay flags
            leftWantsReplay = False
            rightWantsReplay = False

            # Clear game over flag and reset winner
            game_over = False
            winner = None

            print("Restarting game...")

            # Slight transition
            time.sleep(0.5)

        
        try:
            # send to all connected clients
            with stateLock:
                current_clients = list(clients)
            
            # remove dead sockets
            for c in current_clients:
                # if send successful, then connection is alive
                try:
                    c.sendall(state_msg.encode())
                except Exception:
                    # remove dead client
                    with stateLock:
                        if c in clients:
                            clients.remove(c)

                    c.close()
        
        except Exception as e:
            print("Error sending GAME_OVER: ", e)
            game_running = False
            break

        time.sleep(frame_delay)

        # Update paddle movement
        # Y coordinate STARTS at top, so going up will decrease coords, and vice versa
        with stateLock:
            paddle_speed = 5 # pixels per frame

            # left paddle
            if leftMove == "up":
                leftPaddleY -= paddle_speed
            elif leftMove == "down":
                leftPaddleY += paddle_speed
            
            # right paddle
            if rightMove == "up":
                rightPaddleY -= paddle_speed
            elif rightMove == "down":
                rightPaddleY += paddle_speed
            
            # Keep paddles in screen bounds
            # Can't go above 0 (top bounds), can't go below screenheight including paddle pixels of 50
            # Worse case scenario paddle position at y is top or bottom bound (including paddle)
            leftPaddleY = max(0, min(screenHeight - 50, leftPaddleY))
            rightPaddleY = max(0, min(screenHeight - 50, rightPaddleY))

            # Update ball position
            ballX += ballVX
            ballY += ballVY

            # Wall colisions
            # Reverse direction off top or bottom bound
            if ballY <= 0 or ballY >= screenHeight:
                ballVY *= -1
            
            # Left / Right Scoring
            if ballX < 0:
                rightScore += 1 # right scored
                ballX, ballY = screenWidth // 2, screenHeight // 2 # reset to middle of screen
                ballVX = abs(ballVX) # serve to right 

                # Check win condition
                if rightScore >= WIN_SCORE: # Case: score quickly after WIN_SCORE (>=)
                    game_over = True
                    winner = "Right"

            if ballX > screenWidth:
                leftScore += 1 # left scored
                ballX, ballY = screenWidth // 2, screenHeight // 2 # reset to middle of screen
                ballVX = -abs(ballVX) # serve to left

                if leftScore >= WIN_SCORE:
                    game_over = True
                    winner = "Left"
            
            # Paddle collisions
            paddle_width = 10
            paddle_height = 50

            leftPaddleX = 20 # left edge of paddle 
            rightPaddleX = screenWidth - 20 - paddle_width # not totally against wall 

            # Is ball touching at the paddle x coordinate including its width and is it within the screen bounds
            # collision with left paddle
            if (ballX <= leftPaddleX + paddle_width and 
                leftPaddleY <= ballY <= leftPaddleY + paddle_height):
                ballVX = abs(ballVX) # bounce ball back in opposite direction
            
            # collision with right paddle
            if (ballX >= rightPaddleX - paddle_width and
                rightPaddleY <= ballY <= rightPaddleY + paddle_height):
                ballVX = -abs(ballVX) # bounce ball back in opposite direction
            
            # make a string of the current game state
            state_msg = (
                f"LPad={leftPaddleY} RPad={rightPaddleY}"
                f"BallX={ballX} BallY={ballY} VX={ballVX} VY={ballVY}"
                f"LScore={leftScore} RScore={rightScore}"
            )

            # update both clients on encoded game state, if clients exist
            try:
                # make copy of all sockets, used to remove dead sockets
                with stateLock:
                    current_clients = list(clients)
                
                # remove dead sockets
                for c in current_clients:
                    # if send successful, then connection is alive
                    try:
                        c.sendall(state_msg.encode())
                    except Exception:
                        # remove dead client
                        with stateLock:
                            if c in clients:
                                clients.remove(c)
                        c.close()
                        print("Removed a disconnected client")
            except Exception as e:
                print("Error broadcasting state: ", e)
                game_running = False
                break
                                           




#Handles communcation witht he left player
#updates leftpaddle based on the data and sends to rightpaddle

def handleLeftClient(client_socket):
    global leftMove, game_running
    try:
        # if something fails, make game stop by setting to false
        while game_running:
            #receives position from left player
            data = client_socket.recv(1024)
            #disconnect if not recieved
            if not data:
                game_running = False
                break
            #update the left paddle's position
            leftMove = data.decode().strip()

            # game has ended, left player wants to play again
            if leftMove == "PLAY_AGAIN":
                leftWantsReplay = True
                print("Left player wants to play again")
                continue
    except:
        game_running = False
    finally:
        client_socket.close()
    
def handleRightClient(client_socket):
    global rightMove, game_running
    try:
        # if something fails, make game stop by setting to false
        while game_running:
            #receives position from left player
            data = client_socket.recv(1024)
            #disconnect if not recieved
            if not data:
                game_running = False
                break
            #update the left paddle's position
            rightMove = data.decode().strip()

            # game has ended, right player wants to play again
            if rightMove == "PLAY_AGAIN":
                rightWantsReplay = True
                print("Right player wants to play again")
                continue
    except:
        game_running = False
    finally:
        client_socket.close()

# Server set up
def start_server():
    global leftClient, rightClient, clients
    # Create a TCP/IP socket
    # AF_INET = IPv4, SOCK_STREAM = TCP (reliable, connection-oriented)
    server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    # Bind the socket to port 12345 on all available network interfaces
    # '' means listen on all interfaces (localhost, network IP, etc.)
    server.bind(("",12345))
    # start listening for connection (any number of connections)
    server.listen()
    print("Waiting for players...")
    #accpt first client connection (P1 - Left Paddle)
    client1,addr1 = server.accept()
    print(f"Player 1 connected from {addr1}")
    clients.append(client1)

    client2, addr2 = server.accept()
    print(f"Player 2 connected from {addr2}")
    clients.append(client2)

    # Create a thread to handle Player 1
    # target = function to run
    # .start() begins running the thread (doesn't wait for it to finish)
    threading.Thread(target=handleLeftClient,args=(client1,)).start()

    # Create a thread to handle Player 2
    # Both threads now run simultaneously, each handling their own client
    threading.Thread(target=handleRightClient,args=(client2,)).start()

    # Start authoritative game loop
    # daemon automatically stops program when threads exit
    threading.Thread(target=game_loop, daemon=True).start() 

    # accept extra clients (spectators) in the background
    threading.Thread(target=accept_extra_clients, args=(server,), daemon=True).start()

    print("Game loop started, accepting extra spectators")

def accept_extra_clients(server_socket):
    global clients, game_running

    while game_running:
        try:
            extra_client, extra_addr = server_socket.accept()
            # lock state so clients aren't manipulated by multiple threads
            with stateLock:
                clients.append(extra_client)
            print("Extra client connected from ", extra_addr)
        
        except Exception as e:
            print(f"Error accepting extra client: {e}")
            break


