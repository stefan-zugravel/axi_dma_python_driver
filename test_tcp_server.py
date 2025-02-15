import socket
import threading
import time

# Configuration
# HOST = '127.0.0.1'
HOST = '0.0.0.0'
PORT_TCP = 5001
TEST_DURATION = 5  # Seconds
BUFFER_SIZE = 32 * 1024  # 32 KB

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT_TCP))
    server.listen(1)
    conn, _ = server.accept()
    with conn:
        while conn.recv(BUFFER_SIZE):
            conn.sendall(b'ACK')  # Acknowledge receipt