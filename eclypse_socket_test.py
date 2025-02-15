import socket
import threading
import time

# Configuration
HOST = '127.0.0.1'
PORT_TCP = 5001
TEST_DURATION = 5  # Seconds
BUFFER_SIZE = 32 * 1024  # 32 KB


def tcp_server():
    """TCP echo server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT_TCP))
        server.listen(1)
        conn, _ = server.accept()
        with conn:
            while conn.recv(BUFFER_SIZE):
                conn.sendall(b'ACK')  # Acknowledge receipt


def tcp_client():
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


# Run tests
if __name__ == "__main__":
    BUFFER_SIZE = 8 * 1024  # 32 KB
    print("-->> Buffer size 8 KB")
    # Start TCP test
    tcp_thread = threading.Thread(target=tcp_server, daemon=True)
    tcp_thread.start()
    time.sleep(1)  # Ensure server starts first
    tcp_client()

    time.sleep(1)

    BUFFER_SIZE = 16 * 1024  # 32 KB
    print("-->> Buffer size 16 KB")
    # Start TCP test
    tcp_thread = threading.Thread(target=tcp_server, daemon=True)
    tcp_thread.start()
    time.sleep(1)  # Ensure server starts first
    tcp_client()

    time.sleep(1)

    BUFFER_SIZE = 32 * 1024  # 32 KB
    print("-->> Buffer size 32 KB")
    # Start TCP test
    tcp_thread = threading.Thread(target=tcp_server, daemon=True)
    tcp_thread.start()
    time.sleep(1)  # Ensure server starts first
    tcp_client()

    time.sleep(1)

    BUFFER_SIZE = 64 * 1024  # 32 KB
    print("-->> Buffer size 64 KB")
    # Start TCP test
    tcp_thread = threading.Thread(target=tcp_server, daemon=True)
    tcp_thread.start()
    time.sleep(1)  # Ensure server starts first
    tcp_client()

    time.sleep(1)

    BUFFER_SIZE = 128 * 1024  # 32 KB
    print("-->> Buffer size 128 KB")
    # Start TCP test
    tcp_thread = threading.Thread(target=tcp_server, daemon=True)
    tcp_thread.start()
    time.sleep(1)  # Ensure server starts first
    tcp_client()

