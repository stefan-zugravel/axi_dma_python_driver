import os
import mmap
import struct
import argparse
import time
import socket

#from multiprocessing import Process, Array, Value, Manager, Queue
#from queue import Empty

from multiprocessing import Process, Array, Value, RawArray

# Register Offsets
MM2S_CONTROL_REGISTER       = 0x00
MM2S_STATUS_REGISTER        = 0x04
MM2S_SRC_ADDRESS_REGISTER   = 0x18
MM2S_TRNSFR_LENGTH_REGISTER = 0x28

S2MM_CONTROL_REGISTER     = 0x30
S2MM_STATUS_REGISTER      = 0x34
S2MM_DST_ADDRESS_REGISTER = 0x48
S2MM_BUFF_LENGTH_REGISTER = 0x58

# Status Flags
IOC_IRQ_FLAG = 1 << 12
IDLE_FLAG = 1 << 1
AXI_DMA_0_ALMOST_FULL_FLAG  = 1<<1
AXI_DMA_0_ALMOST_EMPTY_FLAG = 1<<0
AXI_DMA_1_ALMOST_FULL_FLAG  = 1<<3
AXI_DMA_1_ALMOST_EMPTY_FLAG = 1<<2

# Status Codes
STATUS_HALTED           = 0x00000001
STATUS_IDLE             = 0x00000002
STATUS_DMA_INTERNAL_ERR = 0x00000010
STATUS_DMA_SLAVE_ERR    = 0x00000020
STATUS_DMA_DECODE_ERR   = 0x00000040
STATUS_IOC_IRQ          = 0x00001000
STATUS_DELAY_IRQ        = 0x00002000
STATUS_ERR_IRQ          = 0x00004000

# Control Codes
HALT_DMA         = 0x00000000
RUN_DMA          = 0x00000001
RESET_DMA        = 0x00000004
ENABLE_IOC_IRQ   = 0x00001000
CLEAR_IOC_IRQ    = 0x00001000
ENABLE_DELAY_IRQ = 0x00002000
ENABLE_ERR_IRQ   = 0x00004000
ENABLE_ALL_IRQ   = 0x00007000

# OFFSET
# GPIO1_OFFSET = 0x41200000
# GPIO2_OFFSET = 0x41210000
# AXIL_OFFSET  = 0x40400000
# MM2S_OFFSET  = 0x0e000000
# S2MM_OFFSET  = 0x0f000000

MM2S_OFFSET_0  = 0x0090000000
S2MM_OFFSET_0  = 0x0092000000
GPIO_2_OFFSET  = 0x00A0030000
AXIL_0_OFFSET  = 0x00B0000000
#AXIL_1_OFFSET  = 0x00B0010000

ddr_memory = os.open("/dev/axi_mem", os.O_RDWR | os.O_SYNC)

axi_MM2S_0_virtual_addr = mmap.mmap(ddr_memory, 33554432, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=MM2S_OFFSET_0) # 32 MB
axi_S2MM_0_virtual_addr = mmap.mmap(ddr_memory, 33554432, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=S2MM_OFFSET_0) # 32 MB
axi_gpio_2_ctrl_addr = mmap.mmap(ddr_memory, 65536, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=GPIO_2_OFFSET) # 64 KB
axi_dma_0_ctrl_addr  = mmap.mmap(ddr_memory, 65536, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=AXIL_0_OFFSET) # 64 KB
#axi_dma_1_ctrl_addr  = mmap.mmap(ddr_memory, 65536, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=AXIL_1_OFFSET) # 64 KB

def write_dma(virtual_addr, offset, value):
    virtual_addr.seek(offset)
    virtual_addr.write((value).to_bytes(4, byteorder='little'))

def read_dma(virtual_addr, offset):
    virtual_addr.seek(offset)
    data = virtual_addr.read(4)
    return int.from_bytes(data, byteorder='little')

def read_dma_status(virtual_addr, offset):
    status = read_dma(virtual_addr, offset)
    print(f"Status (0x{status:08x}@0x{offset:02x}):")

def dma_s2mm_status(virtual_addr):
    status = read_dma(virtual_addr, S2MM_STATUS_REGISTER)
    print(f"Stream to memory-mapped status (0x{status:08x}@0x{S2MM_STATUS_REGISTER:02x}):", end="")
    if status & STATUS_HALTED:
        print(" Halted.")
    else:
        print(" Running.")
    if status & STATUS_IDLE:
        print(" Idle.")
    if status & STATUS_DMA_INTERNAL_ERR:
        print(" DMA internal error.")
    if status & STATUS_DMA_SLAVE_ERR:
        print(" DMA slave error.")
    if status & STATUS_DMA_DECODE_ERR:
        print(" DMA decode error.")
    if status & STATUS_IOC_IRQ:
        print(" IOC interrupt occurred.")
    if status & STATUS_DELAY_IRQ:
        print(" Interrupt on delay occurred.")
    if status & STATUS_ERR_IRQ:
        print(" Error interrupt occurred.")

def dma_mm2s_status(virtual_addr):
    status = read_dma(virtual_addr, MM2S_STATUS_REGISTER)
    print(f"Memory-mapped to stream status (0x{status:08x}@0x{MM2S_STATUS_REGISTER:02x}):", end="")
    if status & STATUS_HALTED:
        print(" Halted.")
    else:
        print(" Running.")
    if status & STATUS_IDLE:
        print(" Idle.")
    if status & STATUS_DMA_INTERNAL_ERR:
        print(" DMA internal error.")
    if status & STATUS_DMA_SLAVE_ERR:
        print(" DMA slave error.")
    if status & STATUS_DMA_DECODE_ERR:
        print(" DMA decode error.")
    if status & STATUS_IOC_IRQ:
        print(" IOC interrupt occurred.")
    if status & STATUS_DELAY_IRQ:
        print(" Interrupt on delay occurred.")
    if status & STATUS_ERR_IRQ:
        print(" Error interrupt occurred.")

def dma_mm2s_sync(virtual_addr):
    while True:
        mm2s_status = read_dma(virtual_addr, MM2S_STATUS_REGISTER)
        if (mm2s_status & IOC_IRQ_FLAG) and (mm2s_status & IDLE_FLAG):
            break

def dma_s2mm_sync(virtual_addr):
    while True:
        s2mm_status = read_dma(virtual_addr, S2MM_STATUS_REGISTER)
        if (s2mm_status & IOC_IRQ_FLAG) and (s2mm_status & IDLE_FLAG):
            break

def print_mem(virtual_address, byte_count):
    data = virtual_address[:byte_count]
    for i in range(byte_count):
        print(f"{data[i]:02X}", end="")
        if i % 4 == 3:
            print(" ", end="")
    print()


def do_mm2s_status():                     #### Maybe those can be deleted and implemented into the main
    dma_mm2s_status(axi_dma_0_ctrl_addr)

def do_s2mm_status():                     #### Maybe those can be deleted and implemented into the main
    dma_s2mm_status(axi_dma_0_ctrl_addr)

def do_status_s2mm_mm2s():
    dma_s2mm_status(axi_dma_0_ctrl_addr)
    dma_mm2s_status(axi_dma_0_ctrl_addr)
    print("FIFO STATUS")
    read_dma_status(axi_gpio_2_ctrl_addr, 0x0)

def do_s2mm_reset():
    write_dma(axi_dma_0_ctrl_addr, S2MM_CONTROL_REGISTER      , RESET_DMA)

def do_mm2s_reset():
    write_dma(axi_dma_0_ctrl_addr, MM2S_CONTROL_REGISTER      , RESET_DMA)

def do_s2mm_run():
    write_dma(axi_dma_0_ctrl_addr, S2MM_CONTROL_REGISTER      , RUN_DMA)

def do_mm2s_run():
    write_dma(axi_dma_0_ctrl_addr, MM2S_CONTROL_REGISTER      , RUN_DMA)

def do_s2mm_irq():
    write_dma(axi_dma_0_ctrl_addr, S2MM_CONTROL_REGISTER      , ENABLE_ALL_IRQ)

def do_mm2s_irq():
    write_dma(axi_dma_0_ctrl_addr, MM2S_CONTROL_REGISTER      , ENABLE_ALL_IRQ)

def do_s2mm_ioc():
    write_dma(axi_dma_0_ctrl_addr, S2MM_STATUS_REGISTER    , CLEAR_IOC_IRQ)

def do_mm2s_ioc():
    write_dma(axi_dma_0_ctrl_addr, MM2S_STATUS_REGISTER      , CLEAR_IOC_IRQ)

def do_s2mm_trn(byte):
    write_dma(axi_dma_0_ctrl_addr, S2MM_BUFF_LENGTH_REGISTER      , byte)
    #axi_dma_0_ctrl_addr[S2MM_BUFF_LENGTH_REGISTER]=0x0080

def do_mm2s_trn(byte):
    write_dma(axi_dma_0_ctrl_addr, MM2S_TRNSFR_LENGTH_REGISTER      , byte)
    #axi_dma_0_ctrl_addr[MM2S_TRNSFR_LENGTH_REGISTER]=0x0080

def do_read_s2mm_trn():
    read_dma_status(axi_dma_0_ctrl_addr, S2MM_BUFF_LENGTH_REGISTER)

def do_read_mm2s_trn():
    read_dma_status(axi_dma_0_ctrl_addr, MM2S_TRNSFR_LENGTH_REGISTER)

def do_s2mm_adr():
    write_dma(axi_dma_0_ctrl_addr, S2MM_DST_ADDRESS_REGISTER      , S2MM_OFFSET)

def do_mm2s_adr():
    write_dma(axi_dma_0_ctrl_addr, MM2S_SRC_ADDRESS_REGISTER      , MM2S_OFFSET)

def do_read_s2mm_adr():
    read_dma_status(axi_dma_0_ctrl_addr, S2MM_DST_ADDRESS_REGISTER)

def do_read_mm2s_adr():
    read_dma_status(axi_dma_0_ctrl_addr, MM2S_SRC_ADDRESS_REGISTER)

def do_read_s2mm_crtl():
    read_dma_status(axi_dma_0_ctrl_addr, S2MM_CONTROL_REGISTER)

def do_read_mm2s_crtl():
    read_dma_status(axi_dma_0_ctrl_addr, MM2S_CONTROL_REGISTER)

def do_read_fifo_status_1():
    read_dma_status(axi_gpio_2_ctrl_addr, 0x0)

def do_read_fifo_status_2():
    print("nothing to do")
    #read_dma_status(axi_gpio_2_ctrl_addr, 0x8)

def save_mem_to_file_hex(virtual_address, offset, byte_count, file_path):
    data = virtual_address[offset: (offset + byte_count)]
    with open(file_path, 'a') as file:
        for i in range(byte_count):
            file.write(f"{data[i]:02X}")
            if i % 4 == 3:
                file.write(" ")
        file.write("\n")
    #file.close()

def save_mem_to_file_bin(virtual_address, offset, byte_count, file_path):
    data = virtual_address[offset: (offset + byte_count)]
    with open(file_path, 'ab') as file:  # Open in binary append mode
        file.write(data)
    #file.close()

def do_fill_memory_high_speed_socket(data_buffer_array, total_transmitted_bytes, do_fill_memory_while, polling_period, max_packet_size, timeout_period, data_buffer_limit, debug, data_buffer_queue, BUFFER_SIZE, write_index):
    try:
        print(f"- S2MM info --> Started fill memory high speed socket process | Polling period: {polling_period/10} ms | Max packet size: {max_packet_size} bytes | Timeout period: {timeout_period} ms | Data buffer limit: {data_buffer_limit} bytes")
        print("")
        packet_count = 0
        index        = 0
        for ind in range(BUFFER_SIZE):
            data_buffer_array[ind] = 0
        while (do_fill_memory_while.value == 0):
            if (read_dma(axi_gpio_2_ctrl_addr, 0x0) & AXI_DMA_0_ALMOST_EMPTY_FLAG):
                if data_buffer_array[index] == 0:
                    write_dma(axi_dma_0_ctrl_addr, S2MM_DST_ADDRESS_REGISTER  , (S2MM_OFFSET_0 + (index*64*1024)))
                    write_dma(axi_dma_0_ctrl_addr, S2MM_BUFF_LENGTH_REGISTER  , max_packet_size)
                    dma_s2mm_sync(axi_dma_0_ctrl_addr)
                    data_buffer_array[index] =  read_dma(axi_dma_0_ctrl_addr, S2MM_BUFF_LENGTH_REGISTER)
                    total_transmitted_bytes.value = total_transmitted_bytes.value  + data_buffer_array[index]
                    data_buffer_queue[write_index.value] = index
                    write_index.value = (write_index.value + 1) % BUFFER_SIZE
                    index = (index + 1) % BUFFER_SIZE
                    packet_count += 1
                else:
                    print(f"backpressure detected on index: {index} and packet counter: {packet_count}")
            time.sleep(polling_period/10000)
        print("")
        print("- S2MM info --> Ended fill memory high speed socket process")
    except KeyboardInterrupt:
        print("")
        print(f"--->    KeyboardInterrupt occurred for fill memory high speed process")


def do_write_memory_indexing(data_buffer_array, total_transmitted_bytes, do_write_memory_while, polling_period, data_buffer_queue, BUFFER_SIZE, write_index, read_index, file_name):
    try:
        print(f"- S2MM info --> Started write memory process | Polling period: {polling_period/10} ms | File name: {file_name} ")
        print("")
        index                = 0
        total_written_bytes  = 0
        PRINT_INTERVAL       = 0.2 # seconds
        # DEBUG TIME #
        counter = 0
        indexing = 0
        indexing_time = 0
        sendall = 0
        sendall_time = 0
        deindexing = 0
        deindexing_time = 0
        debug = 0
        debug_time = 0
        total = 0
        # DEBUG TIME #
        while data_buffer_array[0] == 0 :
            time.sleep(polling_period/10000)
        start_time = time.time()
        while do_write_memory_while.value == 0 or (read_index.value != write_index.value):
            now_time = time.time()                           # DEBUG TIME #
            if read_index.value != write_index.value:
                index = data_buffer_queue[read_index.value]
                indexing_time = time.time()                  # DEBUG TIME #
                with open(file_name, 'ab') as file:
                    file.write(axi_S2MM_0_virtual_addr[(index*64*1024) : (index*64*1024) + data_buffer_array[index]])
                sendall_time = time.time()                   # DEBUG TIME #
                read_index.value = (read_index.value + 1) % BUFFER_SIZE
                total_written_bytes += data_buffer_array[index]
                data_buffer_array[index] = 0
                deindexing_time = time.time()                # DEBUG TIME #
                indexing   += (indexing_time-now_time)       # DEBUG TIME #
                sendall    += (sendall_time-indexing_time)   # DEBUG TIME #
                deindexing += (deindexing_time-sendall_time) # DEBUG TIME #
                counter    += 1                              # DEBUG TIME #
                debug_time  = time.time()                    # DEBUG TIME #
                debug      += (debug_time-deindexing_time)   # DEBUG TIME #
                total      += (debug_time-now_time)          # DEBUG TIME #
            else:
                time.sleep(polling_period/10000)
        current_time = time.time()
        print(f"- S2MM info --> Elapsed time {(current_time - start_time):.2f} s | Total transmitted bytes {total_transmitted_bytes.value:.2f} | Total written bytes {total_written_bytes:.2f} | AVG transmission speed {total_written_bytes / (current_time - start_time) / 1000000:.2f} MB/s", end='\r')
        print("")
        print("- S2MM info --> Ended write memory send memory process")
        print("")
        print(f"#################     DEBUG     #################")
        print(f"packets sent        : {counter}")
        print(f"avg indexing time   : {(indexing/counter)*1000:.3f} ms |  {100*(indexing/total):.2f} %")
        print(f"avg save file time  : {(sendall/counter)*1000:.3f} ms |  {100*(sendall/total):.2f} %  -> {total_written_bytes/sendall/1e6:.3f} MBps")
        print(f"avg deindexing time : {(deindexing/counter)*1000:.3f} ms |  {100*(deindexing/total):.2f} %")
        print(f"avg debug time      : {(debug/counter)*1000:.3f} ms |  {100*(debug/total):.2f} %")
        print(f"avg total time      : {(total/counter)*1000:.3f} ms |  {100*(total/total):.2f} %")
    except KeyboardInterrupt:
        print("--->    KeyboardInterrupt occurred for write memory send memory process")
        print("###     ")
        print(f"- S2MM info --> Elapsed time {(current_time - start_time):.2f} s | Total transmitted bytes {total_transmitted_bytes.value:.2f} | Total written bytes {total_written_bytes:.2f} | AVG transmission speed {total_written_bytes / (current_time - start_time) / 1000000:.2f} MB/s", end='\r')

# Pre-allocate headers for all possible packet sizes
header_cache = {
    size: struct.pack("!I", size) 
    for size in range(1, 65536)
}

def do_send_socket_no_print(data_buffer_array, total_transmitted_bytes, do_write_memory_while, polling_period, debug, data_buffer_queue, HOST, PORT_TCP, BUFFER_SIZE, write_index, read_index):
    try:
        print(f"- S2MM info --> Started TCP send memory process | Polling period: {polling_period/10} ms")
        print(f"- S2MM info --> Connecting to socket as client | HOST: {HOST} | PORT: {PORT_TCP}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            # Disable Nagle + increase send buffer
            client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4*1024*1024)  # 4MB buffer
            client.connect((HOST, PORT_TCP))

            print("")
            index                = 0
            total_written_bytes  = 0
            PRINT_INTERVAL       = 0.2 # seconds
            
            # DEBUG TIME #
            counter = 0

            indexing = 0
            indexing_time = 0
            sendall = 0
            sendall_time = 0
            deindexing = 0
            deindexing_time = 0
            debug = 0
            debug_time = 0
            total = 0
            # DEBUG TIME #

            while data_buffer_array[0] == 0 :
                time.sleep(polling_period/10000)
            start_time = time.time()
            while do_write_memory_while.value == 0 or (read_index.value != write_index.value):
                now_time = time.time()                           # DEBUG TIME #
                if read_index.value != write_index.value:
                    index = data_buffer_queue[read_index.value]
                    indexing_time = time.time()                  # DEBUG TIME #
                    client.sendall(header_cache[data_buffer_array[index]] + axi_S2MM_0_virtual_addr[(index*64*1024) : (index*64*1024) + data_buffer_array[index]])
                    sendall_time = time.time()                   # DEBUG TIME #
                    read_index.value = (read_index.value + 1) % BUFFER_SIZE
                    total_written_bytes += data_buffer_array[index]
                    data_buffer_array[index] = 0
                    deindexing_time = time.time()                # DEBUG TIME #
                    indexing   += (indexing_time-now_time)       # DEBUG TIME #
                    sendall    += (sendall_time-indexing_time)   # DEBUG TIME #
                    deindexing += (deindexing_time-sendall_time) # DEBUG TIME #
                    counter    += 1                              # DEBUG TIME #
                    debug_time  = time.time()                    # DEBUG TIME #
                    debug      += (debug_time-deindexing_time)   # DEBUG TIME #
                    total      += (debug_time-now_time)          # DEBUG TIME #

                else:
                    time.sleep(polling_period/10000)

            current_time = time.time()
            print(f"- S2MM info --> Elapsed time {(current_time - start_time):.2f} s | Total transmitted bytes {total_transmitted_bytes.value:.2f} | Total written bytes {total_written_bytes:.2f} | AVG transmission speed {total_written_bytes / (current_time - start_time) / 1000000:.2f} MB/s", end='\r')
            print("")
            print("- S2MM info --> Ended TCP send memory process")
            print("")
            print(f"#################     DEBUG     #################")
            print(f"packets sent        : {counter}")
            print(f"avg indexing time   : {(indexing/counter)*1000:.3f} ms |  {100*(indexing/total):.2f} %")
            print(f"avg sendall time    : {(sendall/counter)*1000:.3f} ms |  {100*(sendall/total):.2f} %  -> {total_written_bytes/sendall/1e6:.3f} MBps")
            print(f"avg deindexing time : {(deindexing/counter)*1000:.3f} ms |  {100*(deindexing/total):.2f} %")
            print(f"avg debug time      : {(debug/counter)*1000:.3f} ms |  {100*(debug/total):.2f} %")
            print(f"avg total time      : {(total/counter)*1000:.3f} ms |  {100*(total/total):.2f} %")
    except KeyboardInterrupt:
        print("--->    KeyboardInterrupt occurred for TCP send memory process")
        print("###     ")
        print(f"- S2MM info --> Elapsed time {(current_time - start_time):.2f} s | Total transmitted bytes {total_transmitted_bytes.value:.2f} | Total written bytes {total_written_bytes:.2f} | AVG transmission speed {total_written_bytes / (current_time - start_time) / 1000000:.2f} MB/s", end='\r')


def do_send_socket(data_buffer_array, total_transmitted_bytes, do_write_memory_while, polling_period, debug, data_buffer_queue, HOST, PORT_TCP, BUFFER_SIZE, write_index, read_index):
    try:
        print(f"- S2MM info --> Started TCP send memory process | Polling period: {polling_period/10} ms")
        print(f"- S2MM info --> Connecting to socket as client | HOST: {HOST} | PORT: {PORT_TCP}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            # Disable Nagle + increase send buffer
            client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4*1024*1024)  # 4MB buffer
            client.connect((HOST, PORT_TCP))
            print("")
            packet_length                  = 0
            total_written_bytes            = 0
            PRINT_INTERVAL                 = 0.2  # Update stats every 100ms
            while data_buffer_array[0] == 0 :
                time.sleep(polling_period/10000)
            start_time = time.time()
            current_time = start_time
            last_print   = start_time
            index = 0
            ## start debug parameters
            start_time_cycle = 0
            got_index_time = 0
            calculated_packet_length_time = 0
            end_send_all_time = 0
            end_time_cycle   = 0
            packet_length_debug = 0
            increment_read_index_time = 0
            ## end   debug parameters
            with read_index.get_lock():
                while do_write_memory_while.value == 0 or (read_index.value != write_index.value): #or not data_buffer_queue.empty():
                    if read_index.value != write_index.value:
                        start_time_cycle = time.time() # this is for debug
                        #index = data_buffer_queue[read_idx.value]
                        index = read_index.value
                        got_index_time = time.time() # this is for debug
                        #packet_length = struct.pack("!I", data_buffer_array[index])
                        packet_length = header_cache[data_buffer_array[index]]
                        calculated_packet_length_time = time.time() # this is for debug
                        client.sendall(packet_length + axi_S2MM_0_virtual_addr[(index*65536) : (index*65536) + data_buffer_array[index]])
                        end_send_all_time = time.time() # this is for debug
                        read_index.value = (read_index.value + 1) % BUFFER_SIZE
                        
                        increment_read_index_time = time.time() # this is for debug
                        total_written_bytes = total_written_bytes + data_buffer_array[index]
                        packet_length_debug = data_buffer_array[index] #debug
                        data_buffer_array[index] = 0
                        current_time = time.time()
                        if current_time - last_print > PRINT_INTERVAL:
                            print(f"- S2MM info --> Elapsed time {(current_time - start_time):.2f} s | Total transmitted bytes {total_transmitted_bytes.value:.2f} | Total written bytes {total_written_bytes:.2f} | AVG transmission speed {total_written_bytes / (current_time - start_time) / 1000000:.2f} MB/s", end='\r')
                            last_print = current_time
                        end_time_cycle = time.time() # this is for debug
                        print("###############################################")
                        print(f"Total time        : {(end_time_cycle - start_time_cycle)*1000:.3f} ms -> {100*(end_time_cycle - start_time_cycle)/(end_time_cycle - start_time_cycle):.3f} %  |")
                        print(f"Got index time    : {(got_index_time - start_time_cycle)*1000:.3f} ms -> {100*(got_index_time - start_time_cycle)/(end_time_cycle - start_time_cycle):.3f} %  |")
                        print(f"Packet length time: {(calculated_packet_length_time - got_index_time)*1000:.3f} ms -> {100*(calculated_packet_length_time - got_index_time)/(end_time_cycle - start_time_cycle):.3f} %  |")
                        print(f"Sendall time      : {(end_send_all_time - calculated_packet_length_time)*1000:.3f} ms -> {100*(end_send_all_time - calculated_packet_length_time)/(end_time_cycle - start_time_cycle):.3f} %  | {(packet_length_debug)/(end_send_all_time - calculated_packet_length_time)/1e6:.3f} MBps")
                        print(f"Increment time    : {(increment_read_index_time - end_send_all_time)*1000:.3f} ms -> {100*(increment_read_index_time - end_send_all_time)/(end_time_cycle - start_time_cycle):.3f} %  |")
                        print(f"Print time        : {(end_time_cycle - increment_read_index_time)*1000:.3f} ms -> {100*(end_time_cycle - increment_read_index_time)/(end_time_cycle - start_time_cycle):.3f} %  |")
                        print(f"SUM = {(100*(got_index_time - start_time_cycle)/(end_time_cycle - start_time_cycle))+(100*(end_time_cycle - increment_read_index_time))+(100*(calculated_packet_length_time - got_index_time)/(end_time_cycle - start_time_cycle))+(100*(end_time_cycle - end_send_all_time)/(end_time_cycle - start_time_cycle))+(100*(end_send_all_time - calculated_packet_length_time)/(end_time_cycle - start_time_cycle)):.3f}")
                    else:
                        time.sleep(polling_period/10000)
                        current_time = time.time()
            print(f"- S2MM info --> Elapsed time {(current_time - start_time):.2f} s | Total transmitted bytes {total_transmitted_bytes.value:.2f} | Total written bytes {total_written_bytes:.2f} | AVG transmission speed {total_written_bytes / (current_time - start_time) / 1000000:.2f} MB/s", end='\r')
            print("")
            print("- S2MM info --> Ended TCP send memory process")
    except KeyboardInterrupt:
        print("--->    KeyboardInterrupt occurred for TCP send memory process")
        print("###     ")
        print(f"- S2MM info --> Elapsed time {(current_time - start_time):.2f} s | Total transmitted bytes {total_transmitted_bytes.value:.2f} | Total written bytes {total_written_bytes:.2f} | AVG transmission speed {total_written_bytes / (current_time - start_time) / 1000000:.2f} MB/s", end='\r')


def do_data_acquisition(polling_period, file_name, file_type, max_packet_size, fill_process_type, timeout_period, data_buffer_limit, debug):
    try:

        print(r""" This dog is just for fun. If you feel sad look at him.
 For any questions contact Stefan Cristi Zugravel or Valerio Pagliarino.

                            _____^_(smart doggo)
                           |    |    \
                            \   /  ^ |
                           / \_/   0  \
                          /            \
                         /    ____      0
                        /      /  \___ _/

                """)

        data_buffer_array       = Array('i', [0, 0, 0, 0])


        manager = Manager()
        data_buffer_array_order = manager.list()
        #data_buffer_array_order = Array('i', [])

        total_transmitted_bytes = Value('i', 0)
        do_write_memory_while   = Value('i', 0)
        do_fill_memory_while    = Value('i', 0)
        stop                    = Value('i', 0)

        do_configure()

        if fill_process_type == "standard" :
            p1 = Process(target=do_fill_memory , args=(data_buffer_array, total_transmitted_bytes, do_fill_memory_while, polling_period, max_packet_size, stop, debug, data_buffer_array_order, ))
            p1.start()
        elif fill_process_type == "buffered" :
            p1 = Process(target=do_fill_memory_high_speed , args=(data_buffer_array, total_transmitted_bytes, do_fill_memory_while, polling_period, max_packet_size, timeout_period, data_buffer_limit, stop, debug, data_buffer_array_order, ))
            p1.start()
        else :
            print("***  ERROR  *** | Please choise 'standard' or 'buffered' options")

        p2 = Process(target=do_write_memory, args=(data_buffer_array, total_transmitted_bytes, do_write_memory_while, polling_period, file_name, file_type, stop, debug, data_buffer_array_order, ))
        p2.start()

        p1.join()
        p2.join()
        print("")
        print("")
    except KeyboardInterrupt:
        print("")
        print("")
        print("--->    KeyboardInterrupt occurred for data acquisition process")



def do_benchmark(NumberOfEvents, period, packet_size, polling_period, file_name, file_type, max_packet_size, fill_process_type, timeout_period, data_buffer_limit, debug):
    try:

        print(r""" This giraffe is just for fun. If you feel sad look at its funny eyes.
 For any questions contact Stefan Cristi Zugravel or Valerio Pagliarino.

                                   ._ o o
                                   \_`-)|_
                                ,""       \ 
                              ,"  ## |   ಠ ಠ. 
                            ," ##   ,-\__    `.
                          ,"       /     `--._;)
                        ,"     ## /
                      ,"   ##    /

                """)

        '''
        data_buffer_array       = Array('i', [0, 0, 0, 0])

        manager = Manager()
        data_buffer_array_order = manager.list()
        #data_buffer_array_order = Array('i', [])
        
        total_transmitted_bytes = Value('i', 0)
        do_write_memory_while   = Value('i', 0)
        do_fill_memory_while    = Value('i', 0)
        stop                    = Value('i', 0)

        do_configure()
        '''
        BUFFER_SIZE             = 240
        data_buffer_array       = Array('i', BUFFER_SIZE)
        write_index             = Value('i', 0)
        read_index              = Value('i', 0)
        data_buffer_queue       = RawArray('i', BUFFER_SIZE)
        total_transmitted_bytes = Value('i', 0)
        do_write_memory_while   = Value('i', 0)
        do_fill_memory_while    = Value('i', 0)

        do_configure()

        '''
        if fill_process_type == "standard" :
            p1 = Process(target=do_fill_memory , args=(data_buffer_array, total_transmitted_bytes, do_fill_memory_while, polling_period, max_packet_size, stop, debug, data_buffer_array_order, ))
            p1.start()
        elif fill_process_type == "buffered" :
            p1 = Process(target=do_fill_memory_high_speed , args=(data_buffer_array, total_transmitted_bytes, do_fill_memory_while, polling_period, max_packet_size, timeout_period, data_buffer_limit, stop, debug, data_buffer_array_order, ))
            p1.start()
        else :
            print("***  ERROR  *** | Please choise 'standard' or 'buffered' options")
        '''

        p1 = Process(target=do_fill_memory_high_speed_socket , args=(data_buffer_array, total_transmitted_bytes, do_fill_memory_while, polling_period, max_packet_size, timeout_period, data_buffer_limit, debug, data_buffer_queue, BUFFER_SIZE, write_index))
        p1.start()

        #p2 = Process(target=do_write_memory, args=(data_buffer_array, total_transmitted_bytes, do_write_memory_while, polling_period, file_name, file_type, stop, debug, data_buffer_array_order, ))
        p2 = Process(target=do_write_memory_indexing, args=(data_buffer_array, total_transmitted_bytes, do_write_memory_while, polling_period, data_buffer_queue, BUFFER_SIZE, write_index, read_index, file_name, ))
        p2.start()

        p3 = Process(target=do_load_fifo_rate_not_verbose, args=(NumberOfEvents, period, packet_size, ))
        p3.start()
        p3.join()
        do_write_memory_while.value = 1
        do_fill_memory_while.value = 1

        p1.join()
        p2.join()
        print("")
        print("")
    except KeyboardInterrupt:
        print("")
        print("")
        print("--->    KeyboardInterrupt occurred for benchmark process")





def do_benchmark_tcp(NumberOfEvents, period, packet_size, polling_period, max_packet_size, fill_process_type, timeout_period, data_buffer_limit, debug, file_path):
    try:

        print(r""" The parrot is just for fun. Be carefull. It was a  pirate...
 For any questions contact Stefan Cristi Zugravel or Valerio Pagliarino.

                           _------.
                          /  ,     \_
                        /   /  /{}\ |o\_
                       /    \  `--' /-' \    
                      |      \      \    |
                     |              |`-, |
                     /              /__/)/
                    |              |       ARRRG MATEY
                    
 Remember that YOU have to start manually the receiving server before this benchmark!
                """)

        BUFFER_SIZE       = 240
        data_buffer_array = Array('i', BUFFER_SIZE)
        write_index       = Value('i', 0)
        read_index        = Value('i', 0)
        data_buffer_queue = RawArray('i', BUFFER_SIZE)

        #manager = Manager()
        #data_buffer_array_order = manager.list()
        #data_buffer_queue = Queue(maxsize=240)
        
        total_transmitted_bytes = Value('i', 0)
        do_write_memory_while   = Value('i', 0)
        do_fill_memory_while    = Value('i', 0)


        #HOST = '127.0.0.1'
        HOST = '192.168.2.1'
        PORT_TCP = 5001

        do_configure()


        p1 = Process(target=do_fill_memory_high_speed_socket , args=(data_buffer_array, total_transmitted_bytes, do_fill_memory_while, polling_period, max_packet_size, timeout_period, data_buffer_limit, debug, data_buffer_queue, BUFFER_SIZE, write_index))
        p1.start()

        #p2 = Process(target=do_send_socket, args=(data_buffer_array, total_transmitted_bytes, do_write_memory_while, polling_period, debug, data_buffer_queue, HOST, PORT_TCP, BUFFER_SIZE, write_index, read_index, ))
        p2 = Process(target=do_send_socket_no_print, args=(data_buffer_array, total_transmitted_bytes, do_write_memory_while, polling_period, debug, data_buffer_queue, HOST, PORT_TCP, BUFFER_SIZE, write_index, read_index, ))
        p2.start()

        time.sleep(1)
        p3 = Process(target=do_load_fifo_rate_not_verbose, args=(NumberOfEvents, period, packet_size, ))
        p3.start()
        p3.join()
        do_write_memory_while.value = 1
        do_fill_memory_while.value = 1

        p1.join()
        p2.join()
        print("")
        print("")
    except KeyboardInterrupt:
        print("")
        print("")
        print("--->    KeyboardInterrupt occurred for benchmark process")



def do_configure():

    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("++                  BEGIN CONFIGURATION PROCEDURE                ++")
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    dma_s2mm_status(axi_dma_0_ctrl_addr)
    dma_mm2s_status(axi_dma_0_ctrl_addr)
    print("Start AXI DMA configuration")
    write_dma(axi_dma_0_ctrl_addr, S2MM_CONTROL_REGISTER      , RESET_DMA)
    write_dma(axi_dma_0_ctrl_addr, MM2S_CONTROL_REGISTER      , RESET_DMA)
    dma_s2mm_status(axi_dma_0_ctrl_addr)
    dma_mm2s_status(axi_dma_0_ctrl_addr)
    time.sleep(0.1)
    write_dma(axi_dma_0_ctrl_addr, S2MM_CONTROL_REGISTER      , ENABLE_ALL_IRQ)
    write_dma(axi_dma_0_ctrl_addr, MM2S_CONTROL_REGISTER      , ENABLE_ALL_IRQ)
    write_dma(axi_dma_0_ctrl_addr, S2MM_CONTROL_REGISTER      , RUN_DMA)
    write_dma(axi_dma_0_ctrl_addr, MM2S_CONTROL_REGISTER      , RUN_DMA)
    write_dma(axi_dma_0_ctrl_addr, S2MM_DST_ADDRESS_REGISTER  , S2MM_OFFSET)
    write_dma(axi_dma_0_ctrl_addr, MM2S_SRC_ADDRESS_REGISTER  , MM2S_OFFSET)
    #write_dma(axi_dma_0_ctrl_addr, S2MM_BUFF_LENGTH_REGISTER  , 4)
    #write_dma(axi_dma_0_ctrl_addr, MM2S_TRNSFR_LENGTH_REGISTER, 4)
    dma_s2mm_status(axi_dma_0_ctrl_addr)
    dma_mm2s_status(axi_dma_0_ctrl_addr)
    print("FIFO STATUS")
    read_dma_status(axi_gpio_2_ctrl_addr, 0x0)
    #read_dma_status(axi_gpio_2_ctrl_addr, 0x8)
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("++                   END CONFIGURATION PROCEDURE                 ++")
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("")
    print("")



def do_read_word(byte):
    #print("Source memory block data:      ", end="")
    #print_mem(axi_S2MM_0_virtual_addr, byte)

    #print("Clearing the destination register block...")
    #axi_S2MM_0_virtual_addr.write(bytes([0] * byte))

    #print("Memory before reading the word:   ", end="")
    #print_mem(axi_S2MM_0_virtual_addr, byte)

    start_time = time.time()

    #dma_s2mm_status(axi_dma_0_ctrl_addr)
    #write_dma(axi_dma_0_ctrl_addr, S2MM_CONTROL_REGISTER      , RESET_DMA     ) # Reset the DMA

    #dma_s2mm_status(axi_dma_0_ctrl_addr)
    #write_dma(axi_dma_0_ctrl_addr, S2MM_CONTROL_REGISTER      , ENABLE_ALL_IRQ) # Enable all interrupts.

    #dma_s2mm_status(axi_dma_0_ctrl_addr)
    #write_dma(axi_dma_0_ctrl_addr, S2MM_CONTROL_REGISTER      , RUN_DMA       ) # Run DMA

    #dma_s2mm_status(axi_dma_0_ctrl_addr)
    #write_dma(axi_dma_0_ctrl_addr, S2MM_DST_ADDRESS_REGISTER  , S2MM_OFFSET   ) # Writing source address of the data from MM2S in DDR...

    #dma_s2mm_status(axi_dma_0_ctrl_addr)
    #write_dma(axi_dma_0_ctrl_addr, S2MM_STATUS_REGISTER      , CLEAR_IOC_IRQ     )

    #dma_s2mm_status(axi_dma_0_ctrl_addr)
    write_dma(axi_dma_0_ctrl_addr, S2MM_BUFF_LENGTH_REGISTER  , byte          ) # Writing MM2S transfer length of 4 bytes -> 32 bit -> 1 word


    
    #dma_s2mm_status(axi_dma_0_ctrl_addr)
    dma_s2mm_sync(axi_dma_0_ctrl_addr)                                         # Waiting for MM2S synchronization...

    end_time = time.time()

    start_time_txt = time.time()
    save_mem_to_file_hex(axi_S2MM_0_virtual_addr, 0, byte, "output.txt")
    end_time_txt = time.time()

    start_time_bin = time.time()
    save_mem_to_file_bin(axi_S2MM_0_virtual_addr, 0, byte, "output.bin")
    end_time_bin = time.time()

    print("Memory after reading the word:   ", end="")
    #print_mem(axi_S2MM_0_virtual_addr, byte)
    print("FIFO STATUS")
    read_dma_status(axi_gpio_2_ctrl_addr, 0x0)
    #read_dma_status(axi_gpio_2_ctrl_addr, 0x8)
    print("=============================")
    delta_time = end_time - start_time
    data_throughput = byte/delta_time
    print(f"Time elapsed:      {delta_time*1000} ms")
    print(f"Bytes transmitted: {byte} bytes, {byte/1000} KB, {byte/1000000} MB")
    print(f"Data throughput:   {data_throughput/1000000} MB/s, {8*data_throughput/1000000000} Gb/s")
    print("=============================")
    print(f"Time elapsed to write txt file -> {(end_time_txt - start_time_txt)*1000} ms")
    print("=============================")
    print(f"Time elapsed to write bin file -> {(end_time_bin - start_time_bin)*1000} ms")

def do_ready_to_receive(byte):
    print("==================================================================================")
    print("= Setting up AXI DMA driver to receive packets. Press q to stop data acquisition =")
    print("==================================================================================")

    print("*")
    print("*")
    print("*")
    print("--->  START CONFIGURATION  <---")
    do_configure()
    print("--->  END CONFIGURATION  <---")
    print("*")
    print("*")
    print("*")

    #print("-->  Reset the DMA.")
    #write_dma(axi_dma_0_ctrl_addr, S2MM_CONTROL_REGISTER, RESET_DMA)
    #dma_s2mm_status(axi_dma_0_ctrl_addr)

    #print("-->  Enable all interrupts.")
    #write_dma(axi_dma_0_ctrl_addr, S2MM_CONTROL_REGISTER, ENABLE_ALL_IRQ)
    #dma_s2mm_status(axi_dma_0_ctrl_addr)

    #print("-->  Writing the destination address for the data from S2MM in DDR...")
    write_dma(axi_dma_0_ctrl_addr, S2MM_DST_ADDRESS_REGISTER, S2MM_OFFSET)
    #dma_s2mm_status(axi_dma_0_ctrl_addr)

    #print("-->  Run the S2MM channel.")
    #write_dma(axi_dma_0_ctrl_addr, S2MM_CONTROL_REGISTER, RUN_DMA)
    #dma_s2mm_status(axi_dma_0_ctrl_addr)
    print("***  WAITING FOR A PACKET")
    while True:

        #print("-->  Clear all the interrupts...")
        #write_dma(axi_dma_0_ctrl_addr, S2MM_STATUS_REGISTER    , CLEAR_IOC_IRQ  )

        if ((int(read_dma(axi_gpio_2_ctrl_addr, 0x0)))>10):
            start_time = time.time()
            #print(f"-->  Writing S2MM transfer length of {byte} bytes...")
            write_dma(axi_dma_0_ctrl_addr, S2MM_BUFF_LENGTH_REGISTER, byte)

            #print("-->  Waiting for S2MM synchronization...")
            dma_s2mm_sync(axi_dma_0_ctrl_addr)
            end_time = time.time()

            received_bytes = read_dma(axi_dma_0_ctrl_addr, S2MM_BUFF_LENGTH_REGISTER)
            print(f"***  Total number of bytes received during transaction {received_bytes} bytes")



            print("***  Writing to files")
            #print("***  Destination memory block: ", end="")
            #print_mem(axi_S2MM_0_virtual_addr, byte)
            start_time_txt = time.time()
            save_mem_to_file_hex(axi_S2MM_0_virtual_addr, 0, received_bytes, "output.txt")
            end_time_txt = time.time()
            start_time_bin = time.time()
            save_mem_to_file_bin(axi_S2MM_0_virtual_addr, 0, received_bytes, "output.bin")
            end_time_bin = time.time()
            print(f"S2MM Data throughput: {(received_bytes/(end_time - start_time))/1000000} MB/s, {8*(received_bytes/(end_time - start_time))/1000000000} Gb/s")
            print(f"Time elapsed to write txt file -> {(end_time_txt - start_time_txt)*1000} ms -> {(received_bytes/(end_time_txt - start_time_txt))/1000000} MB/s")
            print(f"Time elapsed to write bin file -> {(end_time_bin - start_time_bin)*1000} ms -> {(received_bytes/(end_time_bin - start_time_bin))/1000000} MB/s")
            print("***  DONE")
            print("=======================================================================")
            print("***  WAITING FOR A PACKET")
        else:
            time.sleep(0.01)




def do_load_fifo(NumberOfBytes):
    print("=======================================================================")
    print("=     Loading the FIFO memory with a configurable number of bytes     =")
    print("=======================================================================")

    #print("-->  Source memory before writing:   ")
    #print_mem(axi_MM2S_0_virtual_addr, NumberOfBytes)

    for i in range(NumberOfBytes + 1):
        struct.pack_into('>I', axi_MM2S_0_virtual_addr, i * 4, i)

    print("-->  Source memory after writing:   ")
    #print_mem(axi_MM2S_0_virtual_addr, NumberOfBytes)

    #print("Status before reset")
    #dma_mm2s_status(axi_dma_0_ctrl_addr)
    #write_dma(axi_dma_0_ctrl_addr, MM2S_CONTROL_REGISTER      , RESET_DMA     ) # Reset the DMA
    #write_dma(axi_dma_0_ctrl_addr, MM2S_CONTROL_REGISTER      , ENABLE_ALL_IRQ) # Enable all interrupts.

    #print("Status after reset and before run")
    #dma_mm2s_status(axi_dma_0_ctrl_addr)
    #write_dma(axi_dma_0_ctrl_addr, MM2S_CONTROL_REGISTER      , RUN_DMA       ) # Run DMA

    print("-->  Writing the start address for the data from MM2S in DDR...")
    write_dma(axi_dma_0_ctrl_addr, MM2S_SRC_ADDRESS_REGISTER  , MM2S_OFFSET   )
    dma_mm2s_status(axi_dma_0_ctrl_addr)
    
    #print("-->  Clear all the interrupts...")
    #write_dma(axi_dma_0_ctrl_addr, MM2S_STATUS_REGISTER      , CLEAR_IOC_IRQ  )
    #dma_mm2s_status(axi_dma_0_ctrl_addr)

    print(f"-->  Writing S2MM transfer length of {NumberOfBytes} bytes...")
    start_time = time.time()
    write_dma(axi_dma_0_ctrl_addr, MM2S_TRNSFR_LENGTH_REGISTER, NumberOfBytes ) # Writing MM2S transfer length of 4 bytes -> 32 bit -> 1 word
    #dma_mm2s_status(axi_dma_0_ctrl_addr)

    dma_mm2s_sync(axi_dma_0_ctrl_addr)                                          # Waiting for MM2S synchronization...
    end_time = time.time()


    print("---->   FIFO STATUS   <----")
    read_dma_status(axi_gpio_2_ctrl_addr, 0x0)
    #read_dma_status(axi_gpio_2_ctrl_addr, 0x8)

    print("=============================")
    delta_time = end_time - start_time
    data_throughput = NumberOfBytes/delta_time
    print(f"Time elapsed:      {delta_time*1000} ms")
    print(f"Bytes transmitted: {NumberOfBytes} bytes, {NumberOfBytes/1000} KB, {NumberOfBytes/1000000} MB")
    print(f"Data throughput:   {data_throughput/1000000} MB/s, {8*data_throughput/1000000000} Gb/s")


def do_load_fifo_rate(NumberOfRepetitions):
    print("==========================================================")
    print(f"Loading {NumberOfRepetitions} emulated data packets of 50000 bytes each")
    
    NumberOfBytes = 50000
    dead_time     = 0.005
    print(f"dead time between events is set to {dead_time*1000} ms")

    for i in range(NumberOfBytes + 1):
        struct.pack_into('>I', axi_MM2S_0_virtual_addr, i * 4, i)

    start_time = time.time()

    for j in range(NumberOfRepetitions):
        
        write_dma(axi_dma_0_ctrl_addr, MM2S_SRC_ADDRESS_REGISTER  , MM2S_OFFSET   )
        write_dma(axi_dma_0_ctrl_addr, MM2S_TRNSFR_LENGTH_REGISTER, NumberOfBytes )
        dma_mm2s_sync(axi_dma_0_ctrl_addr)
        if j < (NumberOfRepetitions - 1):
            print(f"------>     sent {j+1} packets", end='\r')
        else:
            print(f"------>     sent {j+1} packets")
        time.sleep(dead_time)

    end_time = time.time()

    print(f"------>     elapsed time = {end_time - start_time} s")
    print(f"------>     event rate   = {NumberOfRepetitions/(end_time - start_time)} Hz")
    print(f"------>     data rate    = {(50000*NumberOfRepetitions)/(end_time - start_time)/1000000} MB/s")
    print("==========================================================")

def do_load_fifo_rate_not_verbose(NumberOfRepetitions, period, PacketSize):

    dead_time      = period/10000

    print(f"- MM2S info --> Started process | Loading {NumberOfRepetitions} data packets of {PacketSize} bytes each. Dead time is {period/10} ms")
    print("")

    #time.sleep(1.0)

    for i in range(PacketSize + 1):
        struct.pack_into('>I', axi_MM2S_0_virtual_addr, i * 4, i)

    start_time = time.time()

    for j in range(NumberOfRepetitions):
        
        write_dma(axi_dma_0_ctrl_addr, MM2S_SRC_ADDRESS_REGISTER  , MM2S_OFFSET   )
        write_dma(axi_dma_0_ctrl_addr, MM2S_TRNSFR_LENGTH_REGISTER, PacketSize )
        dma_mm2s_sync(axi_dma_0_ctrl_addr)
        #if j < (NumberOfRepetitions - 1):
            #print(f"------>     sent {j+1} packets", end='\r')
        #else:
            #print(f"------>     sent {j+1} packets")
        time.sleep(dead_time)

    end_time = time.time()

    print("")
    print(f"- MM2S info --> Elapsed time {end_time - start_time:.2f} s | Event rate {NumberOfRepetitions/(end_time - start_time):.2f} Hz | Data rate {(PacketSize*NumberOfRepetitions)/(end_time - start_time)/1000000:.2f} MB/s")
    #print("==========================================================")




def main():

    parser = argparse.ArgumentParser(description="Python3 driver For the Eclypse Z7 board. Developed at INFN Turin.")
    parser.add_argument('--led', metavar='value', type=int, help='Value of the leds (int) between 1 and 64')
    parser.add_argument('--load_fifo', type=int, help='Number of word to put in the FIFO -> MAX is 512')
    parser.add_argument('-l', '--load_fifo_rate', type=int, help='Insert number of repetitions')

    parser.add_argument('--benchmark', action='store_true', help='Perform a transmission speed benchmark. Example usage: python3 eclypse_driver.py --benchmark --number_of_packets 1000 --packet_period 3 --packet_size 60000 --polling_period 20 --file_name test.bin --file_type b --max_packet_size 65535')
    parser.add_argument('--packet_period', type=int, default=10, help='period between MM2S transfers to be used in benchmark in hundreds of us - default=10')
    parser.add_argument('--packet_size', type=int, default=50000, help='number of byte in a packet to be used in benchmark - default=50000')
    parser.add_argument('--max_packet_size', type=int, default=65000, help='Max number of bytes that the driver can receive in a single transaction - default=65000')
    parser.add_argument('--number_of_packets', type=int, default=100, help='Number of packets to be used in the benchmark - default=100')
    parser.add_argument('--polling_period', type=int, default=10, help='Polling period of the S2MM python driver value expressed in hundreds of us - default=10')
    parser.add_argument('--file_name', type=str, default="output_default_file_name.bin", help='Provide filename to be used for benchmark please - default="output_default_file_name.bin"')
    parser.add_argument('--file_type', type=str, choices=['b', 't'], default='b', help='Select file type, b for binary, t for text. To be noted that text type is extremely slow - default="b"')
    parser.add_argument('--fill_process_type', type=str, choices=['standard', 'buffered'], default='buffered', help='Select fill memory function - default="buffered"')
    parser.add_argument('--timeout_period', type=int, default=1000, help='Timeout time for buffered fill memory dump to file in ms - default=1000')
    parser.add_argument('--data_buffer_limit', type=int, default=2097152, help='Max number of bytes that the driver can buffer in a single transaction - default=2097152 -> 2 MB')
    parser.add_argument('--debug', action='store_true', help='Enable debug messages')

    parser.add_argument('--acquisition', action='store_true', help='Start the data taking. Example usage: eclypse_driver.py --acquisition --polling_period 20 --file_name test.bin --file_type b --max_packet_size 65535')

    parser.add_argument('--benchmark_tcp', action='store_true', help='Perform a transmission speed benchmark. Example usage: python3 eclypse_driver.py --benchmark --number_of_packets 1000 --packet_period 3 --packet_size 60000 --polling_period 20 --file_name test.bin --file_type b --max_packet_size 65535')

    parser.add_argument('--mm2s_status', action='store_true', help='Read the MM2S status word')
    parser.add_argument('--s2mm_status', action='store_true', help='Read the S2MM status word')
    parser.add_argument('-s', '--status_s2mm_mm2s', action='store_true', help='Read the status word for both S2MM and MM2S')
    parser.add_argument('-r', '--s_mm_receive', type=int, help='Configure the link to receive packets')
    parser.add_argument('--mm2s_reset', action='store_true', help='Reset the MM2S link')
    parser.add_argument('--s2mm_reset', action='store_true', help='Reset the S2MM link')
    parser.add_argument('--mm2s_run', action='store_true', help='Run the MM2S link')
    parser.add_argument('--s2mm_run', action='store_true', help='Run the S2MM link')
    parser.add_argument('--mm2s_irq', action='store_true', help='Enale all IRQ on the MM2S link')
    parser.add_argument('--s2mm_irq', action='store_true', help='Enale all IRQ on the S2MM link')
    parser.add_argument('--mm2s_ioc', action='store_true', help='Clear IOC IRQ on the MM2S link')
    parser.add_argument('--s2mm_ioc', action='store_true', help='Clear IOC IRQ on the S2MM link')
    parser.add_argument('--mm2s_trn', type=int, help='Set MM2S tranfer length to 32 bytes')
    parser.add_argument('--s2mm_trn', type=int, help='Set S2MM tranfer length to 32 bytes')
    parser.add_argument('--mm2s_trn_read', action='store_true', help='Read MM2S tranfer length to 32 bytes')
    parser.add_argument('--s2mm_trn_read', action='store_true', help='Read S2MM tranfer length to 32 bytes')
    parser.add_argument('--mm2s_crtl_read', action='store_true', help='Read MM2S tranfer length to 32 bytes')
    parser.add_argument('--s2mm_crtl_read', action='store_true', help='Read S2MM tranfer length to 32 bytes')
    parser.add_argument('--mm2s_adr', action='store_true', help='Set MM2S start address')
    parser.add_argument('--s2mm_adr', action='store_true', help='Set S2MM start address')
    parser.add_argument('--mm2s_adr_read', action='store_true', help='Read MM2S start address')
    parser.add_argument('--s2mm_adr_read', action='store_true', help='Read S2MM start address')
    parser.add_argument('-c', '--configure_axi', action='store_true', help='Configuration procedure for the AXI S2MM and MM2S')
    parser.add_argument('--read_word', type=int, help='Read a configurable number of bytes from the S2MM link')
    parser.add_argument('--other', action='store_true', help='Perform the other action-> remember to type "--other ok"')
    parser.add_argument('--read_led_status', action='store_true', help='Perform the other action-> remember to type "--other ok"')
    parser.add_argument('--read_fifo_status_0', action='store_true', help='Perform the other action-> remember to type "--other ok"')
    parser.add_argument('--read_fifo_status_1', action='store_true', help='Perform the other action-> remember to type "--other ok"')
    parser.add_argument('--read_fifo_status_2', action='store_true', help='Perform the other action-> remember to type "--other ok"')
    args = parser.parse_args()


    if args.led :
        led_config(args.led)
    elif args.benchmark:
        do_benchmark(args.number_of_packets, args.packet_period, args.packet_size, args.polling_period, args.file_name, args.file_type, args.max_packet_size, args.fill_process_type, args.timeout_period, args.data_buffer_limit, args.debug)
    elif args.benchmark_tcp:
        do_benchmark_tcp(args.number_of_packets, args.packet_period, args.packet_size, args.polling_period, args.max_packet_size, args.fill_process_type, args.timeout_period, args.data_buffer_limit, args.debug, args.file_name)
    elif args.acquisition:
        do_data_acquisition(args.polling_period, args.file_name, args.file_type, args.max_packet_size, args.fill_process_type, args.timeout_period, args.data_buffer_limit, args.debug)
    elif args.load_fifo_rate:
        do_load_fifo_rate(args.load_fifo_rate)
    elif args.load_fifo:
        do_load_fifo(args.load_fifo)
    elif args.mm2s_status:
        do_mm2s_status()
    elif args.s2mm_status:
        do_s2mm_status()
    elif args.status_s2mm_mm2s:
        do_status_s2mm_mm2s()
    elif args.mm2s_reset:
        do_mm2s_reset()
    elif args.s2mm_reset:
        do_s2mm_reset()
    elif args.mm2s_run:
        do_mm2s_run()
    elif args.s2mm_run:
        do_s2mm_run()
    elif args.mm2s_irq:
        do_mm2s_irq()
    elif args.s2mm_irq:
        do_s2mm_irq()
    elif args.mm2s_ioc:
        do_mm2s_ioc()
    elif args.s2mm_ioc:
        do_s2mm_ioc()
    elif args.mm2s_trn:
        do_mm2s_trn(args.mm2s_trn)
    elif args.s2mm_trn:
        do_s2mm_trn(args.s2mm_trn)
    elif args.mm2s_trn_read:
        do_read_mm2s_trn()
    elif args.s2mm_trn_read:
        do_read_s2mm_trn()
    elif args.mm2s_adr:
        do_mm2s_adr()
    elif args.s2mm_adr:
        do_s2mm_adr()
    elif args.mm2s_adr_read:
        do_read_mm2s_adr()
    elif args.s2mm_adr_read:
        do_read_s2mm_adr()
    elif args.mm2s_crtl_read:
        do_read_mm2s_crtl()
    elif args.s2mm_crtl_read:
        do_read_s2mm_crtl()
    elif args.configure_axi:
        do_configure()
    elif args.s_mm_receive:
        do_ready_to_receive(args.s_mm_receive)
    elif args.read_led_status:
        do_read_led_status()
    elif args.read_fifo_status_0:
        do_read_fifo_status_0()
    elif args.read_fifo_status_1:
        do_read_fifo_status_1()
    elif args.read_fifo_status_2:
        do_read_fifo_status_2()
    elif args.read_word:
        do_read_word(args.read_word)
    elif args.other :
        debug()
    else :
        print("Please provide an argument or call --help")

    axi_dma_0_ctrl_addr.close()
    axi_gpio_2_ctrl_addr.close()
    axi_MM2S_0_virtual_addr.close()
    axi_S2MM_0_virtual_addr.close()
    os.close(ddr_memory)


if __name__ == "__main__":
    main()