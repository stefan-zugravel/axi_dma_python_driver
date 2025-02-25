#include <linux/module.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/io.h>
#include <linux/cdev.h>


MODULE_LICENSE("GPL");
MODULE_AUTHOR("Alberto_Bortone");
MODULE_DESCRIPTION("AXI Memory Access Driver");

#define DEVICE_NAME "axi_mem"
#define MEM_BASE_ADDR  0x90000000  // Base address that
#define MEM_SIZE       0x30000000   


static void __iomem *mapped_mem;
static int dev_major;

/* Open device*/
static int axi_mem_open(struct inode *inode, struct file *file) {
    pr_info("AXI meme driver: Device opened\n");
    return 0;
}

/* Read */
static ssize_t axi_mem_read(struct file *file, char __user *buf, size_t count, loff_t *ppos) {
    uint32_t value;

    if (*ppos >= MEM_SIZE) return 0;  // Avoid over-read
    value = ioread32(mapped_mem + *ppos);  // Read mapped memory

    if (copy_to_user(buf, &value, sizeof(value)))
        return -EFAULT;

    return sizeof(value);
}

/* Write */
static ssize_t axi_mem_write(struct file *file, const char __user *buf, size_t count, loff_t *ppos) {
    uint32_t value;

    if (*ppos + sizeof(value) > MEM_SIZE) return 0;  // Over-write check
    if (copy_from_user(&value, buf, sizeof(value)))
        return -EFAULT;

    iowrite32(value, mapped_mem + *ppos);  // Write mapped mempry
    return sizeof(value);
}

/* File operations structure */
static struct file_operations axi_mem_fops = {
    .owner   = THIS_MODULE,
    .open    = axi_mem_open,
    .read    = axi_mem_read,
    .write   = axi_mem_write,
};

/* Kernel module init*/
static int __init axi_mem_init(void) {
    dev_major = register_chrdev(0, DEVICE_NAME, &axi_mem_fops); // Register device
    if (dev_major < 0) {
        pr_err("Failed to register device\n");
        return dev_major;
    }

    /* Map physycal memory */
    mapped_mem = ioremap(MEM_BASE_ADDR, MEM_SIZE);
    if (!mapped_mem) {
        unregister_chrdev(dev_major, DEVICE_NAME);
        pr_err("Failed to map memory\n");
        return -ENOMEM;
    }

    pr_info("axi_mem driver initialized, device major: %d\n", dev_major);
    return 0;
}

/* Cleanup */
static void __exit axi_mem_exit(void) {
    if (mapped_mem)
        iounmap(mapped_mem);
    unregister_chrdev(dev_major, DEVICE_NAME);
    pr_info("axi_mem driver unloaded\n");
}

module_init(axi_mem_init);
module_exit(axi_mem_exit);

