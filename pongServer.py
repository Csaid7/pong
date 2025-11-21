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
screenWidth = 640
screenHeight = 480

# These variables store the current state of the game that needs to be synchronized between clients
leftPaddleY = 215    # Y position of left player's paddle (Player 1)
rightPaddleY = 215   # Y position of right player's paddle (Player 2)

# Ball state (starts in middle of screen)
ballX = screenWidth // 2 
ballY = screenWidth // 2

# Scores
leftScore = 0
rightScore = 0

# Sync variable to track game state updates
sync = 0

# Store all connected client sockets (2 players + any spectators)
clients = []

# Prevent threads writing at same time on a global variable
stateLock = threading.Lock()

game_running = False

paddles = {}

# Broadcast updates to all clients
def broadcast_state() -> None:
    
    global ballX, ballY, lScore, rScore, sync, paddles

    # Send each client the opponent paddle position, ball position, scores, and sync value
    with stateLock:

        # Iterate through all connected clients
        for client_socket, side in clients:

            # Determine opponent paddle position for each player
            if side == 'left':
                oppPaddleY = paddles.get('right', screenHeight // 2 - 25)

            elif side == 'right':
                oppPaddleY = paddles.get('left', screenHeight // 2 - 25)

            else:
                oppPaddleY = -1  # Spectators don't have paddles or opponent paddles

            # Create message to send    
            message = f'{oppPaddleY},{ballX},{ballY},{lScore},{rScore},{sync};'

            # Send message to client
            try:
                client_socket.send(message.encode())

            # If sending fails, skip this client
            except:
                continue

# Handle individual client connection
def handle_client(client_socket: socket.socket, player_side: str) -> None:

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
                paddles[player_side] = paddleY

                # Update ball and scores if client is more in sync
                if clientSync >= sync:
                    ballX = clientBallX
                    ballY = clientBallY
                    lScore = clientLScore
                    rScore = clientRScore
                    sync = clientSync

                if lScore > 4 or rScore > 4:
                    reset_game()

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

    global clients, game_running

    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f'Server listening on IP: {host} and Port: {port}')

    # Accept clients
    player_counter = 0

    while True:

        # Accept new client connection
        client_socket, addr = server_socket.accept()
        player_side = 'left' if player_counter == 0 else 'right' if player_counter == 1 else 'spectator'
        print(f"Client connected from {addr} as {player_side}")

        # Store client socket and side
        clients.append((client_socket, player_side))
        player_counter += 1
        
        # Notify when two players are connected
        if not game_running and len(clients) >= 2:
            print("Two players connected. Game can start.")
            game_running = True
            for client_socket, side in clients:
                client_socket.sendall("START;\n".encode())
        
        # Send initial game settings to client
        client_socket.send(f'{screenWidth},{screenHeight},{player_side};'.encode())

        # Start thread to handle this client
        threading.Thread(
            target = handle_client, 
            args = (client_socket, player_side), 
            daemon = True
        ).start()

def reset_game() -> None:
    global ballX, ballY, lScore, rScore, sync
    ballX = screenWidth // 2
    ballY = screenHeight // 2
    lScore = 0
    rScore = 0
    sync = 0
    print("Game reset.")


if __name__ == "__main__":
    start_server(host = '', port = 5555)