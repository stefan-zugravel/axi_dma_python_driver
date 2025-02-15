import os
import mmap
import struct
import argparse
import time

from multiprocessing import Process, Array, Value, Manager

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
GPIO1_OFFSET = 0x41200000
GPIO2_OFFSET = 0x41210000
AXIL_OFFSET  = 0x40400000
MM2S_OFFSET  = 0x0e000000
S2MM_OFFSET  = 0x0f000000

ddr_memory = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
gpio_virtual_addr1 = mmap.mmap(ddr_memory, 65535, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=GPIO1_OFFSET)
gpio_virtual_addr2 = mmap.mmap(ddr_memory, 65535, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=GPIO2_OFFSET)
dma_virtual_addr   = mmap.mmap(ddr_memory, 65535, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=AXIL_OFFSET)

virtual_src_addr   = mmap.mmap(ddr_memory, 16777215, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=MM2S_OFFSET)
virtual_dst_addr   = mmap.mmap(ddr_memory, 16777215, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=S2MM_OFFSET)




def write_dma(virtual_addr, offset, value):
    #struct.pack_into('<I', virtual_addr, offset, value)
    virtual_addr.seek(offset)
    virtual_addr.write((value).to_bytes(4, byteorder='little'))

def read_dma(virtual_addr, offset):
    virtual_addr.seek(offset)  # Move to the correct offset
    data = virtual_addr.read(4)  # Read 4 bytes (assuming 32-bit value)
    return int.from_bytes(data, byteorder='little')  # Convert bytes to int
    #return struct.unpack_from('<I', virtual_addr, offset)[0]

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
        #dma_mm2s_status(virtual_addr)

def dma_mm2s_wait_idle(virtual_addr):                    ########  UNUSED -> to be deleted
    while True:
        mm2s_status = read_dma(virtual_addr, MM2S_STATUS_REGISTER)
        if (mm2s_status & IDLE_FLAG):
            break
        dma_mm2s_status(virtual_addr)

def dma_s2mm_sync(virtual_addr):
    while True:
        s2mm_status = read_dma(virtual_addr, S2MM_STATUS_REGISTER)
        if (s2mm_status & IOC_IRQ_FLAG) and (s2mm_status & IDLE_FLAG):
            break
        #dma_s2mm_status(virtual_addr)

def print_mem(virtual_address, byte_count):
    data = virtual_address[:byte_count]
    for i in range(byte_count):
        print(f"{data[i]:02X}", end="")
        if i % 4 == 3:
            print(" ", end="")
    print()

def debug():
    
    print("Hello World! - Running DMA transfer test application.")

    print("Writing random data to source register block...")
    data = [0xEFBEADDE, 0x11223344, 0xABABABAB, 0xCDCDCDCD, 0x00001111, 0x22223333, 0x44445555, 0x66667777]
    for i, value in enumerate(data):
        struct.pack_into('<I', virtual_src_addr, i * 4, value)

    print("Clearing the destination register block...")
    virtual_dst_addr.write(bytes([0] * 32))

    print("Source memory block data:      ", end="")
    print_mem(virtual_src_addr, 32)

    print("Destination memory block data: ", end="")
    print_mem(virtual_dst_addr, 32)

    print("Reset the DMA.")
    write_dma(dma_virtual_addr, S2MM_CONTROL_REGISTER, RESET_DMA)
    write_dma(dma_virtual_addr, MM2S_CONTROL_REGISTER, RESET_DMA)
    dma_s2mm_status(dma_virtual_addr)
    dma_mm2s_status(dma_virtual_addr)

    print("Enable all interrupts.")
    write_dma(dma_virtual_addr, S2MM_CONTROL_REGISTER, ENABLE_ALL_IRQ)
    write_dma(dma_virtual_addr, MM2S_CONTROL_REGISTER, ENABLE_ALL_IRQ)
    dma_s2mm_status(dma_virtual_addr)
    dma_mm2s_status(dma_virtual_addr)

    print("Writing source address of the data from MM2S in DDR...")
    write_dma(dma_virtual_addr, MM2S_SRC_ADDRESS_REGISTER, MM2S_OFFSET)
    print("Writing the destination address for the data from S2MM in DDR...")
    write_dma(dma_virtual_addr, S2MM_DST_ADDRESS_REGISTER, S2MM_OFFSET)

    print("Run the MM2S channel.")
    write_dma(dma_virtual_addr, MM2S_CONTROL_REGISTER, RUN_DMA)

    print("Run the S2MM channel.")
    write_dma(dma_virtual_addr, S2MM_CONTROL_REGISTER, RUN_DMA)

    print("Writing MM2S transfer length of 32 bytes...")
    write_dma(dma_virtual_addr, MM2S_TRNSFR_LENGTH_REGISTER, 0x00000008)

    print("Writing S2MM transfer length of 32 bytes...")
    write_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER, 0x00000008)

    print("Waiting for MM2S synchronization...")
    dma_mm2s_sync(dma_virtual_addr)

    print("Waiting for S2MM synchronization...")
    dma_s2mm_sync(dma_virtual_addr)

    print("Destination memory block: ", end="")
    print_mem(virtual_dst_addr, 32)


def led_config(value):
    print("Performing configuration of the LEDs.")
    write_dma(gpio_virtual_addr1, 0x00, value)

def do_mm2s_status():                     #### Maybe those can be deleted and implemented into the main
    dma_mm2s_status(dma_virtual_addr)

def do_s2mm_status():                     #### Maybe those can be deleted and implemented into the main
    dma_s2mm_status(dma_virtual_addr)

def do_status_s2mm_mm2s():
    dma_s2mm_status(dma_virtual_addr)
    dma_mm2s_status(dma_virtual_addr)
    print("FIFO STATUS")
    read_dma_status(gpio_virtual_addr1, 0x8)
    read_dma_status(gpio_virtual_addr2, 0x0)

def do_s2mm_reset():
    write_dma(dma_virtual_addr, S2MM_CONTROL_REGISTER      , RESET_DMA)

def do_mm2s_reset():
    write_dma(dma_virtual_addr, MM2S_CONTROL_REGISTER      , RESET_DMA)

def do_s2mm_run():
    write_dma(dma_virtual_addr, S2MM_CONTROL_REGISTER      , RUN_DMA)

def do_mm2s_run():
    write_dma(dma_virtual_addr, MM2S_CONTROL_REGISTER      , RUN_DMA)

def do_s2mm_irq():
    write_dma(dma_virtual_addr, S2MM_CONTROL_REGISTER      , ENABLE_ALL_IRQ)

def do_mm2s_irq():
    write_dma(dma_virtual_addr, MM2S_CONTROL_REGISTER      , ENABLE_ALL_IRQ)

def do_s2mm_ioc():
    write_dma(dma_virtual_addr, S2MM_STATUS_REGISTER    , CLEAR_IOC_IRQ)

def do_mm2s_ioc():
    write_dma(dma_virtual_addr, MM2S_STATUS_REGISTER      , CLEAR_IOC_IRQ)

def do_s2mm_trn(byte):
    write_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER      , byte)
    #dma_virtual_addr[S2MM_BUFF_LENGTH_REGISTER]=0x0080

def do_mm2s_trn(byte):
    write_dma(dma_virtual_addr, MM2S_TRNSFR_LENGTH_REGISTER      , byte)
    #dma_virtual_addr[MM2S_TRNSFR_LENGTH_REGISTER]=0x0080

def do_read_s2mm_trn():
    read_dma_status(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER)

def do_read_mm2s_trn():
    read_dma_status(dma_virtual_addr, MM2S_TRNSFR_LENGTH_REGISTER)

def do_s2mm_adr():
    write_dma(dma_virtual_addr, S2MM_DST_ADDRESS_REGISTER      , S2MM_OFFSET)

def do_mm2s_adr():
    write_dma(dma_virtual_addr, MM2S_SRC_ADDRESS_REGISTER      , MM2S_OFFSET)

def do_read_s2mm_adr():
    read_dma_status(dma_virtual_addr, S2MM_DST_ADDRESS_REGISTER)

def do_read_mm2s_adr():
    read_dma_status(dma_virtual_addr, MM2S_SRC_ADDRESS_REGISTER)

def do_read_s2mm_crtl():
    read_dma_status(dma_virtual_addr, S2MM_CONTROL_REGISTER)

def do_read_mm2s_crtl():
    read_dma_status(dma_virtual_addr, MM2S_CONTROL_REGISTER)

def do_read_led_status():                 ###### To DELETE?
    read_dma_status(gpio_virtual_addr1, 0x0)    

def do_read_fifo_status_0():
    read_dma_status(gpio_virtual_addr1, 0x8)

def do_read_fifo_status_1():
    read_dma_status(gpio_virtual_addr2, 0x0)

def do_read_fifo_status_2():
    print("nothing to do")
    #read_dma_status(gpio_virtual_addr2, 0x8)

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

def do_fill_memory(data_buffer_array, total_transmitted_bytes, do_fill_memory_while, polling_period, max_packet_size, stop, debug, data_buffer_array_order):
    try:
        print(f"- S2MM info --> Started fill memory process | Polling period: {polling_period/10} ms | Max packet size: {max_packet_size} bytes")
        print("")
        #time.sleep(0.5)
        total_transmitted_bytes_buffer = 0
        while do_fill_memory_while.value == 0:
            if (int(read_dma(gpio_virtual_addr2, 0x0)))>10 :
                if   data_buffer_array[0] == 0 :
                    write_dma(dma_virtual_addr, S2MM_DST_ADDRESS_REGISTER  , 0x0f000000)
                    write_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER  , max_packet_size)
                    dma_s2mm_sync(dma_virtual_addr)
                    data_buffer_array[0] = read_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER)
                    data_buffer_array_order.append(0)
                    total_transmitted_bytes_buffer = total_transmitted_bytes_buffer  + data_buffer_array[0]
                    total_transmitted_bytes.value = total_transmitted_bytes_buffer

                elif data_buffer_array[1] == 0 :
                    write_dma(dma_virtual_addr, S2MM_DST_ADDRESS_REGISTER  , 0x0f400000)
                    write_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER  , max_packet_size)
                    dma_s2mm_sync(dma_virtual_addr)
                    data_buffer_array[1] = read_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER)
                    data_buffer_array_order.append(1)
                    total_transmitted_bytes_buffer = total_transmitted_bytes_buffer  + data_buffer_array[1]
                    total_transmitted_bytes.value = total_transmitted_bytes_buffer

                elif data_buffer_array[2] == 0 :
                    write_dma(dma_virtual_addr, S2MM_DST_ADDRESS_REGISTER  , 0x0f800000)
                    write_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER  , max_packet_size)
                    dma_s2mm_sync(dma_virtual_addr)
                    data_buffer_array[2] = read_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER)
                    data_buffer_array_order.append(2)
                    total_transmitted_bytes_buffer = total_transmitted_bytes_buffer  + data_buffer_array[2]
                    total_transmitted_bytes.value = total_transmitted_bytes_buffer

                elif data_buffer_array[3] == 0 :
                    write_dma(dma_virtual_addr, S2MM_DST_ADDRESS_REGISTER  , 0x0fc00000)
                    write_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER  , max_packet_size)
                    dma_s2mm_sync(dma_virtual_addr)
                    data_buffer_array[3] = read_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER)
                    data_buffer_array_order.append(3)
                    total_transmitted_bytes_buffer = total_transmitted_bytes_buffer  + data_buffer_array[3]
                    total_transmitted_bytes.value = total_transmitted_bytes_buffer

                else :
                    print(f"Backpressure detected  --> {data_buffer_array_order}")
                    time.sleep(polling_period/10000)
        time.sleep(0.005)
        stop.value = 1
        print("")
        print("- S2MM info --> Ended fill memory process")
    except KeyboardInterrupt:
        print("")
        print(f"--->    KeyboardInterrupt occurred for fill memory process")


####################################################################### WIP  --> aded timeout_period, added data_buffer_limit
def do_fill_memory_high_speed(data_buffer_array, total_transmitted_bytes, do_fill_memory_while, polling_period, max_packet_size, timeout_period, data_buffer_limit, stop, debug, data_buffer_array_order):
    try:
        print(f"- S2MM info --> Started fill memory high speed process | Polling period: {polling_period/10} ms | Max packet size: {max_packet_size} bytes | Timeout period: {timeout_period} ms | Data buffer limit: {data_buffer_limit} bytes")
        print("")
        #time.sleep(0.5)
        total_transmitted_bytes_buffer = 0
        data_buffer_counter_0 = 0
        data_buffer_counter_1 = 0
        data_buffer_counter_2 = 0
        data_buffer_counter_3 = 0
        begin_time = time.time()
        while (do_fill_memory_while.value == 0) or (data_buffer_counter_0 > 0) or (data_buffer_counter_1 > 0) or (data_buffer_counter_2 > 0) or (data_buffer_counter_3 > 0):
            time_is_out = (time.time() - begin_time) > (timeout_period/1000)
            if ((int(read_dma(gpio_virtual_addr2, 0x0)))>10) or time_is_out :
                begin_time = time.time()
                if data_buffer_array[0] == 0 and data_buffer_counter_1 == 0 and data_buffer_counter_2 == 0 and data_buffer_counter_3 == 0:
                    if not(time_is_out) :
                        write_dma(dma_virtual_addr, S2MM_DST_ADDRESS_REGISTER  , (0x0f000000+data_buffer_counter_0))
                        write_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER  , max_packet_size)
                        dma_s2mm_sync(dma_virtual_addr)
                        data_buffer_counter_0 = data_buffer_counter_0 + read_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER)
                    if ((data_buffer_counter_0 > data_buffer_limit) or time_is_out) and data_buffer_counter_0 > 0:
                        if debug:
                            print("used buffer 0")
                            print(data_buffer_array_order)
                            print(f"Data buffer array before {data_buffer_array[0]}")
                            print(f"Data buffer counter {data_buffer_counter_0}")
                        data_buffer_array_order.append(0)
                        data_buffer_array[0] = data_buffer_counter_0
                        data_buffer_counter_0 = 0
                        if debug:
                            print(f"Data buffer array after {data_buffer_array[0]}")
                        total_transmitted_bytes_buffer = total_transmitted_bytes_buffer  + data_buffer_array[0]
                        total_transmitted_bytes.value = total_transmitted_bytes_buffer

                elif data_buffer_array[1] == 0 and data_buffer_counter_0 == 0 and data_buffer_counter_2 == 0 and data_buffer_counter_3 == 0:
                    if not(time_is_out) :
                        write_dma(dma_virtual_addr, S2MM_DST_ADDRESS_REGISTER  , (0x0f400000+data_buffer_counter_1))
                        write_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER  , max_packet_size)
                        dma_s2mm_sync(dma_virtual_addr)
                        data_buffer_counter_1 = data_buffer_counter_1 + read_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER)
                    if ((data_buffer_counter_1 > data_buffer_limit) or time_is_out) and data_buffer_counter_1 > 0:
                        if debug:
                            print("used buffer 1")
                        data_buffer_array[1] = data_buffer_counter_1
                        data_buffer_array_order.append(1)
                        data_buffer_counter_1 = 0
                        total_transmitted_bytes_buffer = total_transmitted_bytes_buffer  + data_buffer_array[1]
                        total_transmitted_bytes.value = total_transmitted_bytes_buffer

                elif data_buffer_array[2] == 0 and data_buffer_counter_1 == 0 and data_buffer_counter_0 == 0 and data_buffer_counter_3 == 0:
                    if not(time_is_out) :
                        write_dma(dma_virtual_addr, S2MM_DST_ADDRESS_REGISTER  , (0x0f800000+data_buffer_counter_2))
                        write_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER  , max_packet_size)
                        dma_s2mm_sync(dma_virtual_addr)
                        data_buffer_counter_2 = data_buffer_counter_2 + read_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER)
                    if ((data_buffer_counter_2 > data_buffer_limit) or time_is_out) and data_buffer_counter_2 > 0:
                        if debug:
                            print("used buffer 2") 
                        data_buffer_array[2] = data_buffer_counter_2
                        data_buffer_array_order.append(2)
                        data_buffer_counter_2 = 0
                        total_transmitted_bytes_buffer = total_transmitted_bytes_buffer  + data_buffer_array[2]
                        total_transmitted_bytes.value = total_transmitted_bytes_buffer

                elif data_buffer_array[3] == 0 and data_buffer_counter_1 == 0 and data_buffer_counter_0 == 0 and data_buffer_counter_2 == 0:
                    if not(time_is_out) :
                        write_dma(dma_virtual_addr, S2MM_DST_ADDRESS_REGISTER  , (0x0fc00000+data_buffer_counter_3))
                        write_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER  , max_packet_size)
                        dma_s2mm_sync(dma_virtual_addr)
                        data_buffer_counter_3 = data_buffer_counter_3 + read_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER)
                    if ((data_buffer_counter_3 > data_buffer_limit) or time_is_out) and data_buffer_counter_3 > 0:
                        if debug:
                            print("used buffer 3") 
                        data_buffer_array[3] = data_buffer_counter_3
                        data_buffer_array_order.append(3)
                        data_buffer_counter_3 = 0
                        total_transmitted_bytes_buffer = total_transmitted_bytes_buffer  + data_buffer_array[3]
                        total_transmitted_bytes.value = total_transmitted_bytes_buffer

                else :
                    print(f"Backpressure detected  --> {data_buffer_array_order}")
                    time.sleep(polling_period/10000)
        time.sleep(0.005)
        stop.value = 1
        print("")
        print("- S2MM info --> Ended fill memory high speed process")
    except KeyboardInterrupt:
        print("")
        print(f"--->    KeyboardInterrupt occurred for fill memory high speed process")
#######################################################################

def do_write_memory(data_buffer_array, total_transmitted_bytes, do_write_memory_while, polling_period, file_name, file_type, stop, debug, data_buffer_array_order):
    try:
        print(f"- S2MM info --> Started write memory process | Polling period: {polling_period/10} ms | File name: {file_name} | File type: {file_type}")
        print("")
        total_written_bytes            = 0
        total_transmitted_bytes_value  = 0
        #time.sleep(0.5)
        while data_buffer_array[0] == 0 :
            time.sleep(polling_period/10000)
        start_time = time.time()
        current_time = start_time
        if debug:
            print(data_buffer_array[0] > 0)
            print(data_buffer_array_order)
            print(data_buffer_array_order[0] == 0)
        while do_write_memory_while.value == 0 or stop.value == 0:
            if   data_buffer_array[0] > 0 and data_buffer_array_order[0] == 0:
                if debug:
                    print(f"Wrote memory 0 ----> {data_buffer_array_order}") 
                if file_type == 'b':
                    save_mem_to_file_bin(virtual_dst_addr, int(0x00000000), data_buffer_array[0], file_name)
                else :
                    save_mem_to_file_hex(virtual_dst_addr, int(0x00000000), data_buffer_array[0], file_name)
                total_written_bytes = total_written_bytes + data_buffer_array[0]
                total_transmitted_bytes_value = total_transmitted_bytes.value
                data_buffer_array[0] = 0
                data_buffer_array_order.pop(0)
                current_time = time.time()
                print(f"- S2MM info --> Elapsed time {(current_time - start_time):.2f} s | Total transmitted bytes {total_transmitted_bytes_value:.2f} | Total written bytes {total_written_bytes:.2f} | AVG transmission speed {total_written_bytes / (current_time - start_time) / 1000000:.2f} MB/s", end='\r')

            elif data_buffer_array[1] > 0 and data_buffer_array_order[0] == 1:
                if debug:
                    print(f"Wrote memory 1 ----> {data_buffer_array_order}") 
                if file_type == 'b':
                    save_mem_to_file_bin(virtual_dst_addr, int(0x00400000), data_buffer_array[1], file_name)
                else:
                    save_mem_to_file_hex(virtual_dst_addr, int(0x00400000), data_buffer_array[1], file_name)
                total_written_bytes = total_written_bytes + data_buffer_array[1]
                total_transmitted_bytes_value = total_transmitted_bytes.value
                data_buffer_array[1] = 0
                data_buffer_array_order.pop(0)
                current_time = time.time()
                print(f"- S2MM info --> Elapsed time {(current_time - start_time):.2f} s | Total transmitted bytes {total_transmitted_bytes_value:.2f} | Total written bytes {total_written_bytes:.2f} | AVG transmission speed {total_written_bytes / (current_time - start_time) / 1000000:.2f} MB/s", end='\r')

            elif data_buffer_array[2] > 0 and data_buffer_array_order[0] == 2:
                if debug:
                    print(f"Wrote memory 2 ----> {data_buffer_array_order}") 
                if file_type == 'b':
                    save_mem_to_file_bin(virtual_dst_addr, int(0x00800000), data_buffer_array[2], file_name)
                else:
                    save_mem_to_file_hex(virtual_dst_addr, int(0x00800000), data_buffer_array[2], file_name)
                total_written_bytes = total_written_bytes + data_buffer_array[2]
                total_transmitted_bytes_value = total_transmitted_bytes.value
                data_buffer_array[2] = 0
                data_buffer_array_order.pop(0)
                current_time = time.time()
                print(f"- S2MM info --> Elapsed time {(current_time - start_time):.2f} s | Total transmitted bytes {total_transmitted_bytes_value:.2f} | Total written bytes {total_written_bytes:.2f} | AVG transmission speed {total_written_bytes / (current_time - start_time) / 1000000:.2f} MB/s", end='\r')

            elif data_buffer_array[3] > 0 and data_buffer_array_order[0] == 3:
                if debug:
                    print(f"Wrote memory 3 ----> {data_buffer_array_order}") 
                if file_type == 'b':
                    save_mem_to_file_bin(virtual_dst_addr, int(0x00c00000), data_buffer_array[3], file_name)
                else:
                    save_mem_to_file_hex(virtual_dst_addr, int(0x00c00000), data_buffer_array[3], file_name)
                total_written_bytes = total_written_bytes + data_buffer_array[3]
                total_transmitted_bytes_value = total_transmitted_bytes.value
                data_buffer_array[3] = 0
                data_buffer_array_order.pop(0)
                current_time = time.time()
                print(f"- S2MM info --> Elapsed time {(current_time - start_time):.2f} s | Total transmitted bytes {total_transmitted_bytes_value:.2f} | Total written bytes {total_written_bytes:.2f} | AVG transmission speed {total_written_bytes / (current_time - start_time) / 1000000:.2f} MB/s", end='\r')

            else :
                time.sleep(polling_period/10000)
                total_transmitted_bytes_value = total_transmitted_bytes.value
                current_time = time.time()
                print(f"- S2MM info --> Elapsed time {(current_time - start_time):.2f} s | Total transmitted bytes {total_transmitted_bytes_value:.2f} | Total written bytes {total_written_bytes:.2f} | AVG transmission speed {total_written_bytes / (current_time - start_time) / 1000000:.2f} MB/s", end='\r')

        print("")
        print("- S2MM info --> Ended write memory process")
        #print("###     ")
        #print("###     ")
        #print("###     ")
        #print(f"###     Total elapsed time      : {current_time - start_time:.2f} s")
        #print(f"###     Total transmitted bytes : {total_transmitted_bytes_value:.2f}")
        #print(f"###     Total written bytes     : {total_written_bytes:.2f}")
        #print(f"###     Avg transmission speed  : {total_written_bytes / (current_time - start_time) / 1000000:.2f} MB/s")

    except KeyboardInterrupt:
        print("--->    KeyboardInterrupt occurred for write memory process                                                                                     ")
        print("###     ")
        print("###     ")
        print("###     ")
        print(f"###     Total elapsed time      : {current_time - start_time:.2f} s")
        print(f"###     Total transmitted bytes : {total_transmitted_bytes_value:.2f}")
        print(f"###     Total written bytes     : {total_written_bytes:.2f}")
        print(f"###     Avg transmission speed  : {total_written_bytes / (current_time - start_time) / 1000000:.2f} MB/s")


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
    dma_s2mm_status(dma_virtual_addr)
    dma_mm2s_status(dma_virtual_addr)
    print("Start AXI DMA configuration")
    write_dma(dma_virtual_addr, S2MM_CONTROL_REGISTER      , RESET_DMA)
    write_dma(dma_virtual_addr, MM2S_CONTROL_REGISTER      , RESET_DMA)
    dma_s2mm_status(dma_virtual_addr)
    dma_mm2s_status(dma_virtual_addr)
    time.sleep(0.1)
    write_dma(dma_virtual_addr, S2MM_CONTROL_REGISTER      , ENABLE_ALL_IRQ)
    write_dma(dma_virtual_addr, MM2S_CONTROL_REGISTER      , ENABLE_ALL_IRQ)
    write_dma(dma_virtual_addr, S2MM_CONTROL_REGISTER      , RUN_DMA)
    write_dma(dma_virtual_addr, MM2S_CONTROL_REGISTER      , RUN_DMA)
    write_dma(dma_virtual_addr, S2MM_DST_ADDRESS_REGISTER  , S2MM_OFFSET)
    write_dma(dma_virtual_addr, MM2S_SRC_ADDRESS_REGISTER  , MM2S_OFFSET)
    #write_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER  , 4)
    #write_dma(dma_virtual_addr, MM2S_TRNSFR_LENGTH_REGISTER, 4)
    dma_s2mm_status(dma_virtual_addr)
    dma_mm2s_status(dma_virtual_addr)
    print("FIFO STATUS")
    read_dma_status(gpio_virtual_addr1, 0x8)
    read_dma_status(gpio_virtual_addr2, 0x0)
    #read_dma_status(gpio_virtual_addr2, 0x8)
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("++                   END CONFIGURATION PROCEDURE                 ++")
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("")
    print("")



def do_read_word(byte):
    #print("Source memory block data:      ", end="")
    #print_mem(virtual_dst_addr, byte)

    #print("Clearing the destination register block...")
    #virtual_dst_addr.write(bytes([0] * byte))

    #print("Memory before reading the word:   ", end="")
    #print_mem(virtual_dst_addr, byte)

    start_time = time.time()

    #dma_s2mm_status(dma_virtual_addr)
    #write_dma(dma_virtual_addr, S2MM_CONTROL_REGISTER      , RESET_DMA     ) # Reset the DMA

    #dma_s2mm_status(dma_virtual_addr)
    #write_dma(dma_virtual_addr, S2MM_CONTROL_REGISTER      , ENABLE_ALL_IRQ) # Enable all interrupts.

    #dma_s2mm_status(dma_virtual_addr)
    #write_dma(dma_virtual_addr, S2MM_CONTROL_REGISTER      , RUN_DMA       ) # Run DMA

    #dma_s2mm_status(dma_virtual_addr)
    #write_dma(dma_virtual_addr, S2MM_DST_ADDRESS_REGISTER  , S2MM_OFFSET   ) # Writing source address of the data from MM2S in DDR...

    #dma_s2mm_status(dma_virtual_addr)
    #write_dma(dma_virtual_addr, S2MM_STATUS_REGISTER      , CLEAR_IOC_IRQ     )

    #dma_s2mm_status(dma_virtual_addr)
    write_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER  , byte          ) # Writing MM2S transfer length of 4 bytes -> 32 bit -> 1 word


    
    #dma_s2mm_status(dma_virtual_addr)
    dma_s2mm_sync(dma_virtual_addr)                                         # Waiting for MM2S synchronization...

    end_time = time.time()

    start_time_txt = time.time()
    save_mem_to_file_hex(virtual_dst_addr, 0, byte, "output.txt")
    end_time_txt = time.time()

    start_time_bin = time.time()
    save_mem_to_file_bin(virtual_dst_addr, 0, byte, "output.bin")
    end_time_bin = time.time()

    print("Memory after reading the word:   ", end="")
    #print_mem(virtual_dst_addr, byte)
    print("FIFO STATUS")
    read_dma_status(gpio_virtual_addr1, 0x8)
    read_dma_status(gpio_virtual_addr2, 0x0)
    #read_dma_status(gpio_virtual_addr2, 0x8)
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
    #write_dma(dma_virtual_addr, S2MM_CONTROL_REGISTER, RESET_DMA)
    #dma_s2mm_status(dma_virtual_addr)

    #print("-->  Enable all interrupts.")
    #write_dma(dma_virtual_addr, S2MM_CONTROL_REGISTER, ENABLE_ALL_IRQ)
    #dma_s2mm_status(dma_virtual_addr)

    #print("-->  Writing the destination address for the data from S2MM in DDR...")
    write_dma(dma_virtual_addr, S2MM_DST_ADDRESS_REGISTER, S2MM_OFFSET)
    #dma_s2mm_status(dma_virtual_addr)

    #print("-->  Run the S2MM channel.")
    #write_dma(dma_virtual_addr, S2MM_CONTROL_REGISTER, RUN_DMA)
    #dma_s2mm_status(dma_virtual_addr)
    print("***  WAITING FOR A PACKET")
    while True:

        #print("-->  Clear all the interrupts...")
        #write_dma(dma_virtual_addr, S2MM_STATUS_REGISTER    , CLEAR_IOC_IRQ  )

        if ((int(read_dma(gpio_virtual_addr2, 0x0)))>10):
            start_time = time.time()
            #print(f"-->  Writing S2MM transfer length of {byte} bytes...")
            write_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER, byte)

            #print("-->  Waiting for S2MM synchronization...")
            dma_s2mm_sync(dma_virtual_addr)
            end_time = time.time()

            received_bytes = read_dma(dma_virtual_addr, S2MM_BUFF_LENGTH_REGISTER)
            print(f"***  Total number of bytes received during transaction {received_bytes} bytes")



            print("***  Writing to files")
            #print("***  Destination memory block: ", end="")
            #print_mem(virtual_dst_addr, byte)
            start_time_txt = time.time()
            save_mem_to_file_hex(virtual_dst_addr, 0, received_bytes, "output.txt")
            end_time_txt = time.time()
            start_time_bin = time.time()
            save_mem_to_file_bin(virtual_dst_addr, 0, received_bytes, "output.bin")
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
    #print_mem(virtual_src_addr, NumberOfBytes)

    for i in range(NumberOfBytes + 1):
        struct.pack_into('>I', virtual_src_addr, i * 4, i)

    print("-->  Source memory after writing:   ")
    #print_mem(virtual_src_addr, NumberOfBytes)

    #print("Status before reset")
    #dma_mm2s_status(dma_virtual_addr)
    #write_dma(dma_virtual_addr, MM2S_CONTROL_REGISTER      , RESET_DMA     ) # Reset the DMA
    #write_dma(dma_virtual_addr, MM2S_CONTROL_REGISTER      , ENABLE_ALL_IRQ) # Enable all interrupts.

    #print("Status after reset and before run")
    #dma_mm2s_status(dma_virtual_addr)
    #write_dma(dma_virtual_addr, MM2S_CONTROL_REGISTER      , RUN_DMA       ) # Run DMA

    print("-->  Writing the start address for the data from MM2S in DDR...")
    write_dma(dma_virtual_addr, MM2S_SRC_ADDRESS_REGISTER  , MM2S_OFFSET   )
    dma_mm2s_status(dma_virtual_addr)
    
    #print("-->  Clear all the interrupts...")
    #write_dma(dma_virtual_addr, MM2S_STATUS_REGISTER      , CLEAR_IOC_IRQ  )
    #dma_mm2s_status(dma_virtual_addr)

    print(f"-->  Writing S2MM transfer length of {NumberOfBytes} bytes...")
    start_time = time.time()
    write_dma(dma_virtual_addr, MM2S_TRNSFR_LENGTH_REGISTER, NumberOfBytes ) # Writing MM2S transfer length of 4 bytes -> 32 bit -> 1 word
    #dma_mm2s_status(dma_virtual_addr)

    dma_mm2s_sync(dma_virtual_addr)                                          # Waiting for MM2S synchronization...
    end_time = time.time()


    print("---->   FIFO STATUS   <----")
    read_dma_status(gpio_virtual_addr1, 0x8)
    read_dma_status(gpio_virtual_addr2, 0x0)
    #read_dma_status(gpio_virtual_addr2, 0x8)

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
        struct.pack_into('>I', virtual_src_addr, i * 4, i)

    start_time = time.time()

    for j in range(NumberOfRepetitions):
        
        write_dma(dma_virtual_addr, MM2S_SRC_ADDRESS_REGISTER  , MM2S_OFFSET   )
        write_dma(dma_virtual_addr, MM2S_TRNSFR_LENGTH_REGISTER, NumberOfBytes )
        dma_mm2s_sync(dma_virtual_addr)
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

    dead_time      = period/1000

    print(f"- MM2S info --> Started process | Loading {NumberOfRepetitions} data packets of {PacketSize} bytes each. Dead time is {period} ms")
    print("")

    #time.sleep(1.0)

    for i in range(PacketSize + 1):
        struct.pack_into('>I', virtual_src_addr, i * 4, i)

    start_time = time.time()

    for j in range(NumberOfRepetitions):
        
        write_dma(dma_virtual_addr, MM2S_SRC_ADDRESS_REGISTER  , MM2S_OFFSET   )
        write_dma(dma_virtual_addr, MM2S_TRNSFR_LENGTH_REGISTER, PacketSize )
        dma_mm2s_sync(dma_virtual_addr)
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
    parser.add_argument('--packet_period', type=int, default=5, help='period between MM2S transfers to be used in benchmark in ms - default=5')
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

    dma_virtual_addr.close()
    gpio_virtual_addr1.close()
    gpio_virtual_addr2.close()
    virtual_src_addr.close()
    virtual_dst_addr.close()
    os.close(ddr_memory)


if __name__ == "__main__":
    main()