/**
 * @file SOC_driver.c
 * @brief Memory manipulation module for Python extension
 */

#define PY_SSIZE_T_CLEAN // Pulls in the Python API
#include <Python.h>
#include "alcor_address_map.h"


#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>

// /**
//  * @brief Allocates a block of memory and returns its address.
//  * 
//  * @param self Unused.
//  * @param args Python arguments (size of memory to allocate).
//  * @return PyObject* Pointer to the allocated memory as a long integer.
//  */
// static PyObject * mem_alloc(PyObject *self, PyObject *args)
// {
//     size_t size;
//     char *ptr;

//     // Parse the input argument (size of memory to allocate)
//     if (!PyArg_ParseTuple(args, "n", &size))
//         return NULL;

//     // Allocate memory
//     ptr = malloc(size);
//     if (!ptr)
//         return PyErr_NoMemory();
//     *((unsigned char *)ptr) = 0;
//     // Return the memory address as an integer
//     return PyLong_FromVoidPtr(ptr);
// }


/**
 * @brief Writes a 32-bit value to a specified memory address.
 * 
 * @param self Unused.
 * @param args Python arguments (address as long, value as long ).
 * @return PyObject* None.
 */
static PyObject * mem_write(PyObject *self, PyObject *args)
{
    long address;
    uint32_t value;

    if (!PyArg_ParseTuple(args, "lI", &address, &value)) {
        return NULL;
    }

    // // Convert long address to pointer
    // void *address = (void *)(uintptr_t)address_long;

    // PySys_WriteStdout("mem_write: received address as long: %ld\n", address);
    // PySys_WriteStdout("Writing value %i\n", value);
    int fd = open("/dev/axi_mem", O_RDWR);  

        if (fd < 0) {
        perror("open");
        return NULL;
    }

    off_t offset = address-AXI_base_address;  // Offset di scrittura

    // Scrive direttamente all'offset specificato
    if (pwrite(fd, &value, sizeof(value), offset) != sizeof(value)) {
        PyErr_SetFromErrno(PyExc_IOError);
        // perror("pwrite");
        close(fd);

        Py_RETURN_NONE;
    }
    close(fd);
    Py_RETURN_NONE;
}

/**
 * @brief Reads a 32-bit value from a specified memory address.
 * 
 * @param self Unused.
 * @param args Python arguments (address as unsigned long).
 * @return PyObject* The 32-bit value read.
 */
static PyObject * mem_read(PyObject *self, PyObject *args)
{
    long address;
    int32_t read_value;

    if (!PyArg_ParseTuple(args, "k", &address))
        return NULL;

    off_t offset = address-AXI_base_address;  // Offset di scrittura
    int fd = open("/dev/axi_mem", O_RDWR);  

    // Open file
        if (fd < 0) {
        perror("open");
        return NULL;
    }
    // Read 32-bit value from memory

    if (pread(fd, &read_value, sizeof(read_value), offset) != sizeof(read_value)) {
        // perror("pread");
        PyErr_SetFromErrno(PyExc_IOError);
        close(fd);
        Py_RETURN_NONE;

    }
    close(fd);

    return PyLong_FromUnsignedLong(read_value);
}

// /**
//  * @brief Frees a previously allocated memory block.
//  * 
//  * @param self Unused.
//  * @param args Python arguments (pointer to allocated memory).
//  * @return PyObject* None.
//  */
// static PyObject * mem_free(PyObject *self, PyObject *args)
// {
//     void *ptr;

//     // Parse the pointer argument
//     if (!PyArg_ParseTuple(args, "O&", PyLong_AsVoidPtr, &ptr))
//         return NULL;

//     // Free allocated memory
//     free(ptr);

//     Py_RETURN_NONE;
// }

// /**
//  * @brief Write serial data word
//  * 
//  * @param self Unused.
//  * @param args Python arguments (long ser_ctrl_number, long data_word_number, ,long 32_bit_word).
//  * @return PyObject* None.
//  */
// static PyObject * write_dataword_to_ser(PyObject *self, PyObject *args)
// {
//     int data_word_number;
//     int ser_ctrl_number;
//     long data_word;

//     if (!PyArg_ParseTuple(args, "iil", &ser_ctrl_number, &data_word_number, &data_word)) {
//         return NULL;  // Parsing error
//     }
//     // PySys_WriteStdout("data_word_number: %i, ser_ctrl_number: %i, data_word %li\n", data_word_number, ser_ctrl_number, data_word);
//     long base_address = AXI_SER_CTRL_BASE_ADDRESS[ser_ctrl_number];
//     long shift = SER_DATA_TO_SER_SHIFT(data_word_number);  
//     long to_write_addr = base_address + shift;
//     // PySys_WriteStdout("Base_address: %lx, shift: %lx, to_write_addr %lx, data %lx\n", base_address, shift, to_write_addr, data_word);
//     // Creiamo una tupla con gli argomenti da passare a mem_write
//     PyObject *py_args = PyTuple_Pack(2, 
//                                      PyLong_FromLong(to_write_addr), 
//                                      PyLong_FromLong(data_word));
//     if (!py_args) {
//         PyErr_SetString(PyExc_ValueError, "Failed to create arguments tuple.");
//         return NULL;
//     }
    
//     PyObject *result = mem_write(self, py_args);
//     Py_DECREF(py_args);  // Rilasciamo la memoria dell'argomento passato

//     if (!result) {
//         PyErr_SetString(PyExc_ValueError, "Memwrite failed.");
//         return NULL;
//     }

//     Py_DECREF(result);  // Liberiamo la memoria di ritorno se necessario
//     Py_RETURN_NONE;
// }

// /*   
//  * @brief Write serial control word
//  * 
//  * @param self Unused.
//  * @param args Python arguments (long ser_ctrl_number, long ctrl_word).
//  * @return PyObject* None.
//  */
// static PyObject * write_cmdword_to_ser(PyObject *self, PyObject *args)
// {
//     int ser_ctrl_number;
//     long ctrl_word;

//     // Parsing degli argomenti
//     if (!PyArg_ParseTuple(args, "il", &ser_ctrl_number, &ctrl_word)) {
//         return NULL;  // Errore nel parsing
//     }

//     // Calcolo dell'indirizzo di scrittura
//     long base_address = AXI_SER_CTRL_BASE_ADDRESS[ser_ctrl_number];
//     long shift = SER_CTRL_WORD_SHIFT;
//     long to_write_addr = base_address + shift;

//     // Creiamo una tupla con gli argomenti da passare a mem_write
//     PyObject *py_args = PyTuple_Pack(2, 
//                                      PyLong_FromLong(to_write_addr), 
//                                      PyLong_FromLong(ctrl_word));
//     if (!py_args) {
//         PyErr_SetString(PyExc_ValueError, "Failed to create arguments tuple.");
//         return NULL;
//     }

//     // Chiamata diretta alla funzione mem_write
//     PyObject *result = mem_write(self, py_args);
//     Py_DECREF(py_args);  // Rilasciamo la memoria dell'argomento passato

//     if (!result) {
//         PyErr_SetString(PyExc_ValueError, "Memwrite failed.");
//         return NULL;
//     }

//     Py_DECREF(result);  // Liberiamo la memoria di ritorno se necessario
//     Py_RETURN_NONE;
// }

// /*   
//  * @brief Read serial controller status word
//  * 
//  * @param self Unused.
//  * @param args Python arguments (long ser_ctrl_number).
//  * @return PyObject* None.
//  */
// static PyObject * read_statusword_from_ser(PyObject *self, PyObject *args)
// {
//     int ser_ctrl_number;
//     unsigned long to_read_addr;
    
//     // Parsing degli argomenti
//     if (!PyArg_ParseTuple(args, "ik", &ser_ctrl_number, &to_read_addr)) {
//         return NULL;  // Errore nel parsing
//     }

//     // Calcolo dell'indirizzo di lettura
//     unsigned long base_address = AXI_SER_CTRL_BASE_ADDRESS[ser_ctrl_number];
//     unsigned long shift = SER_STATUS_WORD_shift;
//     to_read_addr = base_address + shift;

//     // Tuple to by passed to meme_read
//     PyObject *py_args = PyTuple_Pack(1, PyLong_FromUnsignedLong(to_read_addr));
//     if (!py_args) {
//         PyErr_SetString(PyExc_ValueError, "Failed to create arguments tuple.");
//         return NULL;
//     }

//     // Chiamata diretta alla funzione mem_read
//     PyObject *result = mem_read(self, py_args);
//     Py_DECREF(py_args);  // Rilasciamo la memoria dell'argomento passato

//     if (!result) {
//         PyErr_SetString(PyExc_ValueError, "Memread failed.");
//     }

//     return result;
// }


// /*   
//  * @brief Read data wods from serializer
//  * 
//  * @param self Unused.
//  * @param args Python arguments (long ser_ctrl_number).
//  * @return PyObject* None.
//  */
// static PyObject * read_dataword_from_ser(PyObject *self, PyObject *args)
// {
//     int data_word_number;
//     int ser_ctrl_number;
//     unsigned long to_read_addr;
    
//     // Parsing degli argomenti
//     if (!PyArg_ParseTuple(args, "ii", &ser_ctrl_number, &data_word_number)) {
//         return NULL;  // Errore nel parsing
//     }

//     // Calcolo dell'indirizzo di lettura
//     long base_address = AXI_SER_CTRL_BASE_ADDRESS[ser_ctrl_number];
//     long shift = SER_DATA_TO_SER_SHIFT(data_word_number);  
//     to_read_addr = base_address + shift;

//     // Tuple to by passed to mem_read
//     PyObject *py_args = PyTuple_Pack(1, PyLong_FromUnsignedLong(to_read_addr));
//     if (!py_args) {
//         PyErr_SetString(PyExc_ValueError, "Failed to create arguments tuple.");
//         return NULL;
//     }

//     // Chiamata diretta alla funzione mem_read
//     PyObject *result = mem_read(self, py_args);
//     Py_DECREF(py_args);  // Rilasciamo la memoria dell'argomento passato

//     if (!result) {
//         PyErr_SetString(PyExc_ValueError, "Memread failed.");
//     }

//     return result;
// }



///////////////////////////////////////////////////////////////////////
/*******************Method table, struture and init*******************/
///////////////////////////////////////////////////////////////////////

/**
 * @brief Method table for the Python module.
 */
static PyMethodDef SOC_driverMethods[] = {
    {"mem_read",  mem_read, METH_VARARGS, "Read an arbitrary memory location."},
    {"mem_write",  mem_write, METH_VARARGS, "Write a 32-bit value to an arbitrary memory location."},
    // {"mem_alloc",  mem_alloc, METH_VARARGS, "Allocate memory and return pointer."},
    // {"mem_free",  mem_free, METH_VARARGS, "Free previously allocated memory."},
    // {"write_dataword_to_ser", write_dataword_to_ser, METH_VARARGS, "Write serial controller data word "},
    // {"write_cmdword_to_ser", write_cmdword_to_ser, METH_VARARGS, "Write serial controller command word "},
    // {"read_statusword_from_ser", read_statusword_from_ser, METH_VARARGS, "Read serial controller status word "},
    // {"read_dataword_from_ser", read_dataword_from_ser, METH_VARARGS, "Read data world returned by serializer "},

    {NULL, NULL, 0, NULL} /* Sentinel */
};

/**
 * @brief Module definition structure.
 */
static struct PyModuleDef SOC_driver = {
    PyModuleDef_HEAD_INIT,
    "SOC_driver",   /* Name of module */
    "First test",   /* Module documentation, may be NULL */
    -1,              /* Size of per-interpreter state, or -1 for global state */
    SOC_driverMethods
};

/**
 * @brief Module initialization function.
 * 
 * @return PyObject* The initialized module.
 */
PyMODINIT_FUNC PyInit_SOC_driver(void)
{
    Py_Initialize();
    return PyModule_Create(&SOC_driver);
}
