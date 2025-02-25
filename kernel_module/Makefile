.PHONY: help compile compile_kernel clean_kernel

help:
	@echo "Options:"

compile:
	@gcc -fPIC -shared -I /usr/include/python3.10 -Og driver_test.c -o SOC_driver.so && echo "Compiled"

obj-m += axi_mem_driver.o
KDIR := /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)
CONFIG_MODULE_SIG=n
compile_kernel:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean_kernel:
	@set -e; \
	if [ -e /dev/axi_mem ]; then sudo rm /dev/axi_mem; echo "/dev/axi_mem removed"; fi; \
	if lsmod | grep -q axi_mem_driver; then sudo rmmod axi_mem_driver; echo "Module axi_mem_driver removed"; fi;
	$(MAKE) -C $(KDIR) M=$(PWD) clean

init_device:
	@set -e; \
	echo "Setting kernel module";\
	sudo insmod axi_mem_driver.ko || { echo "insmod failed"; exit 1; }; \
	MAJOR=$$(awk '/axi_mem/ {print $$1}' /proc/devices); \
	if [ -z "$$MAJOR" ]; then echo "Device not found in /proc/devices"; exit 1; fi; \
	if [ ! -e /dev/axi_mem ]; then sudo mknod /dev/axi_mem c $$MAJOR 0; fi; \
	sudo chmod 666 /dev/axi_mem; \
	echo "Kernel device initialized successfully";\
	echo "Firmware flashing...";\
	sudo fpgautil -b ~/work/firmware_files/ip_integration_wrapper.bit; \
	echo "Firmware flashed"

flash_fpga:
	@set -e; \
	sudo fpgautil -b ~/work/firmware_files/ip_integration_wrapper.bit;\
	echo "Firmware flashed"
