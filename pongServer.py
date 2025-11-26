# =================================================================================================
# Contributing Authors:	    Caleb Mpungu, Naman Rao, Nathan Garrison
# Email Addresses:          smp222@uky.edu, naman.rao@uky.edu, nathan.garrison@uky.edu
# Date:                     11/25/2025
# Purpose:                 Server that manages multiplayer pong game between two clients
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
screenWidth = 640
screenHeight = 480

# These variables store the current state of the game that needs to be synchronized between clients
leftPaddleY = 215    # Y position of left player's paddle (Player 1)
rightPaddleY = 215   # Y position of right player's paddle (Player 2)

# Ball state (starts in middle of screen)
ballX = screenWidth // 2 
ballY = screenHeight // 2

# Scores
lScore = 0
rScore = 0

# Sync variable to track game state updates
sync = 0

# Store all connected client sockets (2 players + any spectators)
clients = []
client_sides = {}

# Prevent threads writing at same time on a global variable
stateLock = threading.Lock()

# Game running flag
game_running = False

# Store paddle positions
paddles = {}



# Broadcast updates to all clients
def broadcast_state() -> None:
    # Author: Nathan Garrison, Naman Rao, Caleb Mpungu
    # Purpose: Send the current game state to all connected clients
    # Pre: Global game state variables (paddles, ball, scores, sync) are initialized
    # Post: Each client receives opponent paddle position, ball position, scores, and sync value

    global ballX, ballY, lScore, rScore, sync, paddles

    # Send each client the opponent paddle position, ball position, scores, and sync value
    with stateLock:

        # Iterate through all connected clients
        for client_socket, side in clients:

            try:

                # Determine opponent paddle position for each player
                if side == 'left':
                    oppPaddleY = paddles.get('right', screenHeight // 2 - 25)
                    message = f'{oppPaddleY},{ballX},{ballY},{lScore},{rScore},{sync};'

                elif side == 'right':
                    oppPaddleY = paddles.get('left', screenHeight // 2 - 25)
                    message = f'{oppPaddleY},{ballX},{ballY},{lScore},{rScore},{sync};'

                # Spectators get both paddle positions but can't control either,
                # sends a special message to spectator clients
                elif side == 'spectator':
                    leftY = paddles.get('left', screenHeight // 2 - 25)
                    rightY = paddles.get('right', screenHeight // 2 - 25)
                    message = f'{leftY},{rightY},{ballX},{ballY},{lScore},{rScore},{sync};'

                # Send message to client
                client_socket.send(message.encode())

            # If sending fails, skip this client
            except:
                continue



# Handle individual client connection
def handle_client(client_socket: socket.socket, player_side: str) -> None:
    # Author: Nathan Garrison, Naman Rao, Caleb Mpungu
    # Purpose: Handles communication with a single client, updates game state, and broadcasts it
    # Pre: Client socket is connected, player_side is assigned a side: ('left', 'right', or 'spectator')
    # Post: Updates global paddle positions, ball position, scores, and sync. Removes client and paddle on disconnect

    global paddles, ballX, ballY, lScore, rScore, sync, game_running

    # Initialize paddle position for this player
    paddles[player_side] = screenHeight // 2 - 25

    try:
        # Start game when both players are connected
        while True:

            # Wait for data from client
            data = client_socket.recv(1024).decode()

            # If no data, client has disconnected
            if not data:
                break

            # Parse received data
            paddleY, clientBallX, clientBallY, clientLScore, clientRScore, clientSync = data.split(',')
            paddleY = int(paddleY)
            clientBallX = int(clientBallX)
            clientBallY = int(clientBallY)
            clientLScore = int(clientLScore)
            clientRScore = int(clientRScore)
            clientSync = int(clientSync)

            # Update game state
            with stateLock:

                # Update this player's paddle position
                paddles[player_side] = paddleY

                # Issues with desync if right client has higher sync, so only
                # left client updates ball position and scores and right side just follows
                if player_side == 'left':
                    if clientSync >= sync:
                        ballX = clientBallX
                        ballY = clientBallY
                        lScore = clientLScore
                        rScore = clientRScore
                        sync = clientSync

                    # Check for game over condition
                    if lScore > 4 or rScore > 4:
                        game_running = False

            # Broadcast updated state to all clients
            broadcast_state()

    except Exception as e:
        print(f"Error handling client {player_side}: {e}")

    finally:

        # Clean up on disconnect
        client_socket.close()

        with stateLock:

            # Remove client from list
            clients[:] = [
                (c, s) for c, s, in clients if c != client_socket
            ]

            # Remove paddle state
            paddles.pop(player_side, None)



# Server set up
def start_server(host: str, port: int) -> None:
    # Author: Nathan Garrison, Naman Rao, Caleb Mpungu
    # Purpose: Initialize server, accept clients, assign sides, start game, and spawn threads
    # Pre: Host and port are valid; server can bind to socket
    # Post: Server listens indefinitely, clients are handled in threads, game state updates continuously

    global clients, game_running

    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f'Server listening on IP: {host} and Port: {port}')

    while True:

        # Accept new client connection
        client_socket, addr = server_socket.accept()
        if len(clients) == 0:
            side = 'left' 
        elif len(clients) == 1:
            side = 'right'
        else:
            side = 'spectator'

        # Send initial game state to client
        client_socket.sendall(f'{screenWidth},{screenHeight},{side};'.encode())
        clients.append((client_socket, side))
        print(f"Client connected from {addr} as {side}")
        
        # Check if we can start the game
        if not game_running:

            # Check if both players are connected
            player_sides = [s for _, s in clients]
            if 'left' in player_sides and 'right' in player_sides:

                # Both players connected, start the game
                print("Two players connected. Game can start.")
                game_running = True
                for c, _ in clients:
                    c.sendall("START;\n".encode())

        # Start thread to handle this client
        threading.Thread(
            target = handle_client, 
            args = (client_socket, side), 
            daemon = True
        ).start()



# Run server code listening on all IPs and port 5555 on startup
if __name__ == "__main__":
    start_server(host = '', port = 5555)
