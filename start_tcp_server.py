import socket
import struct
import time


HOST      = '0.0.0.0'
PORT_TCP  = 5001
file_path = "Please_work.bin"

total = 0
receive_length = 0
calculated_length = 0
transmit_packet = 0
counter = 0
counter_bytes = 0

"""TCP echo server that saves received data to a file."""
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    #server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 16*1024*1024)  # 16MB buffer
    server.bind((HOST, PORT_TCP))
    server.listen(1)
    conn, _ = server.accept()
    
    print("Server started -> waiting for packets")
    with conn:
        print("Connected")
        while True:
            start_cycle_time     = time.time()  ################
            length_data = conn.recv(4)
            received_length_time = time.time()  ################
            if not length_data:
                break  # Connection closed
            
            length = struct.unpack("!I", length_data)[0]
            calculated_length_time    = time.time()  ################
            data = b""
            while len(data) < length:
                packet = conn.recv(length - len(data),  socket.MSG_WAITALL)
                
                if not packet:
                    print("Connection closed unexpectedly")
                    break 
                data += packet
            end_packet_time = time.time()  ################

            total += end_packet_time-start_cycle_time
            receive_length += received_length_time-start_cycle_time
            calculated_length += calculated_length_time-received_length_time
            transmit_packet += end_packet_time-calculated_length_time
            counter += 1
            counter_bytes += length

            #print(f"Received up to now: {len(data)}")
            #print(f"Transfer speed    : {8*len(data)/(end - start)/1e6} Mbps")
            #print(f"Cycle speed       : {8*len(data)/(end - start0)/1e6} Mbps | {len(data)/(end - start0)/1e6} MBps")
            # Save data to file
            #with open(file_path, 'ab') as file:
            #    file.write(data)
            
            #conn.sendall(b'ACK')  # Acknowledge receipt
print("END ")
print(f"received packets  : {counter}")
print(f"receive_length    : {(receive_length/counter)*1000:.3f} ms | {100*(receive_length/total):.2f} %")
print(f"calculated_length : {(calculated_length/counter)*1000:.3f} ms | {100*(calculated_length/total):.2f} %")
print(f"transmit_packet   : {(transmit_packet/counter)*1000:.3f} ms | {100*(transmit_packet/total):.2f} % | {counter_bytes/transmit_packet/1e6:.3f} MBps")
print(f"total             : {(total/counter)*1000:.3f} ms | {100*(total/total):.2f} % | {counter_bytes/total/1e6:.3f} MBps")
