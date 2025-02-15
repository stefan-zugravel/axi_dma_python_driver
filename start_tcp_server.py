import socket
import struct
import time


HOST      = '0.0.0.0'
PORT_TCP  = 5001
file_path = "Please_work.bin"

"""TCP echo server that saves received data to a file."""
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    #server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 16*1024*1024)  # 16MB buffer
    server.bind((HOST, PORT_TCP))
    server.listen(1)
    conn, _ = server.accept()
    
    print("Server started -> waiting for packets")
    with conn:
        while True:
            
            length_data = conn.recv(4)
            start0 = time.time()
            if not length_data:
                break  # Connection closed
            start = time.time()
            length = struct.unpack("!I", length_data)[0]
            print(f"----> Packet length: {length}")
            
            # Ensure we receive all 'length' bytes
            data = b""
            while len(data) < length:
                packet = conn.recv(length - len(data),  socket.MSG_WAITALL)
                
                if not packet:
                    print("Connection closed unexpectedly")
                    break  # Connection closed unexpectedly
                data += packet
            end = time.time()
            #print(f"Received up to now: {len(data)}")
            #print(f"Transfer speed    : {8*len(data)/(end - start)/1e6} Mbps")
            print(f"Cycle speed       : {8*len(data)/(end - start0)/1e6} Mbps | {len(data)/(end - start0)/1e6} MBps")
            # Save data to file
            #with open(file_path, 'ab') as file:
            #    file.write(data)
            
            #conn.sendall(b'ACK')  # Acknowledge receipt