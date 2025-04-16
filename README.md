--> Implementation of Selective Repeat Protocol <--


## Overview

📚 This project demonstrates the implementation of the Selective Repeat Protocol with a graphical/animated interface using Python. The project includes the simulation of sender and receiver communication and provides an interactive GUI built with Tkinter.

---

## Prerequisites

1. **Python**: 🐍 Ensure Python 3.8 or later is installed on your system. Download from [Python.org](https://www.python.org/).
2. **Pip**: 📦 Verify that `pip` is installed for package management.
3. **Required Libraries**:
   - Tkinter (pre-installed with Python)

---

## Path Setting

1. **For Windows**:
   - 🖥️ Add Python to your system's PATH if not already done. Refer to [Python PATH Guide](https://docs.python.org/3/using/windows.html#excursus-setting-environment-variables).

2. **For Linux/macOS**:
   - 🐧 Ensure `python3` is in your PATH. You can check with:
     ```bash
     python3 --version
     ```
   - If not, update your PATH in `.bashrc` or `.zshrc`.

---

## Installation Steps

1. **Clone or Download the Repository**:
   - Clone the repository using Git:
     ```bash
     git clone https://github.com/your-repo/selective-repeat-protocol.git
     ```
   - Alternatively, download the ZIP file and extract it.

2. **Navigate to the Project Directory**:

---

## Execution Steps 

- The project can be run directly as a script which in turn opens a GUI (STEP 1)

- If you want an executable -
   Refer to STEP 2 to convert it to .exe


1. **Run the Main Script**:

   - 🚀 Execute the following command from the project directory:
     ```bash
     python main.py
     ```
   
   - 🖼️ A Tkinter-based GUI will open, showcasing the sender and receiver simulation.
   - Interact with the GUI to observe the Selective Repeat Protocol in action.

3. **How to generate an excutable**:

   MAKE SURE PYINSTALLER IS INSTALLED
   if not, 
   run the following command 
   > pip install pyinstaller


   - 🛠️ Generate an executable:

     ```bash
     pyinstaller --onefile --icon="PATH to icon image" --noconsole main.py 
     ```

   **important** - 
   - icon image should be of extension .ico 
   - assets/ directory contains one example icon.ico file 
   - replace "PATH to icon image" with the path to icon.ico 

     (--icon set icon image (optional) ; --noconsole to not display terminal while running gui)
   
   - The executable will be located in the `dist` folder.

---

## Troubleshooting
1. **Dependency Issues**:
   - ❗ If you encounter missing modules, manually install them using `pip install <module-name>`.

2. **Permission Errors**:
   - 🔐 Run the command prompt or terminal as administrator.

3. **Execution Errors**:
   - 🛠️ Ensure all files, including `icon.ico`, are in the correct paths.

---

- Incase of proper functionality not being implemented run the code ATLEAST TWICE using the restart or pause/reset buttons 

---

## Folder Structure (for easy navigation)
```
Selective_Repeat_Protocol/
|-- assets/                  # Contains icons and other resources
|   |-- icon.ico
|-- src/                     # Source files
|   |-- main.py              # Main script
|-- README.md                # Readme file
|-- writeup.pdf              # 2 page writeup
```

## Additional Notes
- 🐍 Make sure the Python version supports the `threading` and `tkinter` modules.
- ✅ Test the executable file on target machines to verify compatibility.

