# Chisel GUI Manager

A GUI-based manager for handling and organizing **Chisel** connections. This application simplifies managing your Chisel SOCKS5 connections, enabling users to add, edit, delete, and manage connections easily through an intuitive graphical interface. It also supports minimizing to the system tray for easy accessibility.

Made with 90% AI, 10% human intervention. 

---

## Features

- **GUI for Chisel:** No more command-line hassle. Add, edit, and manage connections directly.
- **Tray Integration:** Minimize the app to the system tray, and restore it with a double-click.
- **[Planned] Connection Management:**
  - Start and stop connections.
  - Save connection configurations for reuse.
- **Settings:** Customize startup and shutdown behaviors.

---

## Dependencies

This program requires the following dependencies:

- Python 3.8 or later
- [Chisel](https://github.com/jpillora/chisel)
- [PySide6](https://pypi.org/project/PySide6/)

---

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/RohanBhattacharyya/Chisel-GUI-Manager
   cd Chisel-GUI-Manager
   ```

2. **Install Python Dependencies**:
   Ensure you have `pip` installed and run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Chisel**:
   Follow the instructions [here](https://github.com/jpillora/chisel?tab=readme-ov-file#install) to install Chisel on your system.

4. **Run the Application**:
   ```bash
   python chisel_gui_manager.py
   ```

---

## How to Use

1. Launch the application using the instructions above.
2. Use the "+" button to add a new Chisel connection.
   - Provide a name, URL, and any required arguments (e.g., `socks`).
3. Start a connection by clicking the **Connect** button.
4. Stop the connection using the **Disconnect** button.
5. Minimize the application to the tray for unobtrusive background operation. Restore it with a double-click on the tray icon.

---

## System Tray Functionality

When minimized to the tray:
- **Double-click** the tray icon to restore the window.
- Right-click the tray icon for an **Exit** option.

---

## Configuration

The application stores connection details and settings in a `config.json` file located in the same directory as the script. The file automatically updates when changes are made through the application.

### Default Configuration File:
```json
{
  "connections": [],
  "settings": {
    "startup": "When logged in",
    "shutoff": "On log off"
  }
}
```

---

## Troubleshooting

1. **PySide6 is missing**:
   Ensure you have imported all necessary modules correctly. Specifically:
   ```bash
   pip install -r requirements.txt
   ```

2. **Chisel Not Found**:
   Verify Chisel is installed and accessible from your system's PATH.

3. **Permissions Issue**:
   Run the application with sufficient permissions if accessing restricted ports or files.

---

## Contributing

Feel free to fork the repository and submit pull requests. Contributions are welcome for bug fixes, feature enhancements, and documentation improvements.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Fun Facts

- Chisel is a fast TCP/UDP tunnel. Pairing it with a GUI makes managing connections even simpler!
- The tray icon integration ensures the app stays out of your way while providing quick access when needed.

---

Enjoy seamless Chisel connection management with Chisel GUI Manager! 🚀

