import socket
import threading
import time

# Configuration
# HOST = '127.0.0.1'
HOST = '192.168.2.1'
PORT_TCP = 5001
TEST_DURATION = 5  # Seconds
BUFFER_SIZE = 60 * 1024  # 32 KB
print(f"Buffer size is: {BUFFER_SIZE}")


"""TCP speed test client."""
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
    client.connect((HOST, PORT_TCP))
    data = b'X' * BUFFER_SIZE
    start_time = time.time()
    bytes_sent = 0
    while time.time() - start_time < TEST_DURATION:
        client.sendall(data)
        client.recv(3)  # Wait for ACK
        bytes_sent += len(data)
    speed = (bytes_sent / 1e6) / TEST_DURATION  # MB/s
    print(f"***   TCP Speed: {speed:.2f} MB/s")
    print(f"***   TCP Speed: {speed*8:.2f} Mb/s")