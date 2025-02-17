import socket
import struct
import time

HOST = '0.0.0.0'
PORT_UDP = 5002
BUFFER_SIZE = 64 * 1024  # 64KB buffer
file_path = "Please_work.bin"

total = 0
receive_length = 0
calculated_length = 0
transmit_packet = 0
counter = 0
counter_bytes = 0

# UDP Server
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
    server.bind((HOST, PORT_UDP))
    print("UDP Server started -> waiting for packets")
    
    while True:
        start_cycle_time = time.time()
        
        length_data, client_addr = server.recvfrom(4)  # Receive length first
        received_length_time = time.time()
        
        if not length_data:
            break
        
        length = struct.unpack("!I", length_data)[0]
        calculated_length_time = time.time()
        
        data = b""
        while len(data) < length:
            packet, _ = server.recvfrom(min(BUFFER_SIZE, length - len(data)))
            if not packet:
                print("Connection closed unexpectedly")
                break
            data += packet
        
        end_packet_time = time.time()
        
        total += end_packet_time - start_cycle_time
        receive_length += received_length_time - start_cycle_time
        calculated_length += calculated_length_time - received_length_time
        transmit_packet += end_packet_time - calculated_length_time
        counter += 1
        counter_bytes += length
        
        # Save data to file
        # with open(file_path, 'ab') as file:
        #     file.write(data)
        
        # Send acknowledgment
        #server.sendto(b'ACK', client_addr)
    
print("END")
print(f"received packets  : {counter}")
print(f"receive_length    : {(receive_length/counter)*1000:.3f} ms | {100*(receive_length/total):.2f} %")
print(f"calculated_length : {(calculated_length/counter)*1000:.3f} ms | {100*(calculated_length/total):.2f} %")
print(f"transmit_packet   : {(transmit_packet/counter)*1000:.3f} ms | {100*(transmit_packet/total):.2f} % | {counter_bytes/transmit_packet/1e6:.3f} MBps")
print(f"total             : {(total/counter)*1000:.3f} ms | {100*(total/total):.2f} % | {counter_bytes/total/1e6:.3f} MBps")
