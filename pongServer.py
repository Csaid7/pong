# =================================================================================================
# Contributing Authors:	    Caleb Mpungu, Naman Rao, Nathan Garrison
# Email Addresses:          smp222@uky.edu, naman.rao@uky.edu, nathan.garrison@uky.edu
# Date:                     11/23/2025
# Purpose:                 Server that manages multiplayer pong game between two clients
# =================================================================================================

# Synchronization 
import socket
import threading
import time 

import json
import os

from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class LeaderboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        lb = load_leaderboard()

        html = "<html><body style='font-family: monospace; background: black; color: white;'>"
        html += "<h1>Pong Leaderboard</h1><pre>"

        if not lb:
            html += "No wins recorded yet."
        else:
            for name, wins in lb.items():
                html += f"{name}: {wins} wins\n"

        html += "</pre></body></html>"

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

def start_leaderboard_server():
    server = HTTPServer(("0.0.0.0", 80), LeaderboardHandler)
    print("Leaderboard HTTP server running on port 80...")
    server.serve_forever()

# Start leaderboard server in background thread
threading.Thread(target=start_leaderboard_server, daemon=True).start()

LEADERBOARD_FILE = "leaderboard.json"

def load_leaderboard():
    if not os.path.exists(LEADERBOARD_FILE):
        return {}
    try:
        with open(LEADERBOARD_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_leaderboard(lb):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(lb, f, indent=4)

# Use this file to write your server logic
# You will need to support at least two clients
# You will need to keep track of where on the screen (x,y coordinates) each paddle is, the score 
# for each player and where the ball is, and relay that to each client
# I suggest you use the sync variable in pongClient.py to determine how out of sync your two
# clients are and take actions to resync the games

# Global Game State
screenWidth = 640
screenHeight = 480

winner_recorded = False

player_initials = {
    "left": "",
    "right": ""
}

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

game_finished = False


# Store paddle positions
paddles = {}

leaderboard = {}          # initials -> wins
leaderboard_lock = threading.Lock()

def record_win(initials: str) -> None:
    with leaderboard_lock:
        leaderboard[initials] = leaderboard.get(initials, 0) + 1
    print(f"Leaderboard: {initials} now has {leaderboard[initials]} wins")



# Broadcast updates to all clients
def broadcast_state() -> None:
    
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

    global paddles, ballX, ballY, lScore, rScore, sync, game_running, winner_recorded, player_initials

    with stateLock:
        player_initials[player_side] = ""

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
            
            if data.startswith("INITIALS:"):
                initials = data.split(":", 1)[1].strip().strip(";")
                with leaderboard_lock:
                    player_initials[player_side] = initials
                print(f"Player on side {player_side} set initials to {initials}")

                continue  # don't try to parse as game update
            
            if data.startswith("REPLAY"):
                print(f"Replay requested by {player_side}")

                with stateLock:
                    lScore = 0
                    rScore = 0
                    ballX = screenWidth // 2
                    ballY = screenHeight // 2
                    sync = 0
                    winner_recorded = False

                # Tell both clients to START the new round
                for c, _ in clients:
                    c.sendall("START;".encode())

                continue    # skip rest of loop for this message

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
                        
                        if not winner_recorded:
                            winner_recorded = True

                            winner_side = "left" if lScore > rScore else "right"
                            winner_initials = player_initials.get(winner_side, winner_side)

                            lb = load_leaderboard()
                            lb[winner_initials] = lb.get(winner_initials, 0) + 1
                            save_leaderboard(lb)



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



# Reset game state for new round
def reset_game() -> None:

    global ballX, ballY, sync

    # Reset ball position and sync for new round
    ballX = screenWidth // 2
    ballY = screenHeight // 2
    sync = 0
    print("Game reset for next round.")

# Run server code listening on all IPs and port 5555 on startup
if __name__ == "__main__":

    start_server(host = '', port = 5555)
