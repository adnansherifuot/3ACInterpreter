# 3-Address Code (3AC) Interpreter

This project is a virtual machine (VM) and interpreter for a custom 3-Address Code (3AC) language. It is designed to parse and execute 3AC instructions, managing a program counter, call stack, global memory, and a heap for dynamic memory allocation. The interpreter features a simple graphical user interface (GUI) built with Tkinter to display program output.

## Features

The interpreter supports a variety of instructions, making it a capable VM for a simple compiled language.

- **Core Operations**: Standard arithmetic (`ADD`, `SUB`, `MUL`, `DIV`), logical (`AND`, `OR`), and comparison (`EQ`, `NE`, `LT`, `GT`, etc.) operations.
- **Control Flow**: Unconditional and conditional jumps (`JUMP`, `JUMPT`, `JUMPF`) using labels.
- **Function Support**: A full function call stack, including support for parameters passed by value (`PARAM`) and by reference (`REF_PARAM`).
- **Memory Management**:
  - A global memory space for global variables.
  - A heap for dynamic memory allocation (`ALLOC_HEAP`, `FREE_HEAP`).
  - Pointer operations for direct memory manipulation (`ADDR_OF`, `DEREF_LOAD`, `DEREF_STORE`).
- **Data Structures**: Indexed memory access for arrays and other data structures (`INDEX_LOAD`, `INDEX_STORE`).
- **String Manipulation**: Support for string concatenation, length calculation, and character access.
- **Simple UI**: A console window to show program output via the `PRINT` instruction or log runtime messages.

A full specification of the language syntax can be found in the `3AC Syntax for interpreter.txt` file.

## Requirements

To run this project, you will need:

- **Python 3.6 or newer**: The project is written in Python 3.
- **Tkinter**: This is the standard GUI toolkit for Python. It comes pre-installed with most Python distributions on Windows and macOS.

### For Linux Users

If you are using a Debian-based Linux distribution (like Ubuntu), you may need to install Tkinter separately. You can do so with the following command:

```bash
sudo apt-get update
sudo apt-get install python3-tk
```

## How to Install and Run

1.  **Clone or Download the Project**:
    Get the project files onto your local machine. If you are using Git, you can clone the repository:
    ```bash
    git clone https://github.com/adnansherifuot/3ACInterpreter
    cd 3ACInterpreter
    ```
    Otherwise, download and extract the source code into a directory named `3ACInterpreter`.

2.  **Project Structure**:
    Ensure all project files are in the same directory. The expected structure is:
    ```
    3ACInterpreter/
    ├── vm.py
    ├── instruction.py
    ├── stack_frame.py
    ├── interpreter.py  (or your main application script)
    └── 3AC Syntax for interpreter.txt
    ```

3.  **Run the Application**:
    Execute the main script from your terminal to launch the interpreter's GUI.
    ```bash
    python interpreter.py
    ```

    *(Note: The entry point script might have a different name, like `app.py` or `gui.py`. Please replace `main.py` with the correct filename.)*

