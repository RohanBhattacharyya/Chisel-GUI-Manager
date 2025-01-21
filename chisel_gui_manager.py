#!/usr/bin/env python3
import sys
import json
import os
import subprocess
from pathlib import Path
from typing import List, Dict
from PySide6.QtGui import QGuiApplication

from PySide6.QtCore import (
    Qt,
    QTimer,
    QSize,
    Slot
)
from PySide6.QtGui import (
    QAction,
    QIcon
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QDialog,
    QMessageBox,
    QSystemTrayIcon,
    QMenu
)

CONFIG_FILE = str(Path(__file__).parent / "config.json")
DEFAULT_PORT = 1080
DEFAULT_SOCKS_HOST = "127.0.0.1"


def load_config() -> Dict:
    """Load configuration from config.json or return defaults if missing."""
    if not os.path.exists(CONFIG_FILE):
        return {
            "connections": [],
            "settings": {
                "startup": "When logged in",
                "shutoff": "On log off"
            }
        }
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(config_data: Dict):
    """Save configuration to config.json."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)


class Connection:
    """Model for a Chisel connection."""
    def __init__(self, name: str, url: str, arguments: str):
        self.name = name
        self.url = url
        self.arguments = arguments

    def to_dict(self):
        return {
            "name": self.name,
            "url": self.url,
            "arguments": self.arguments
        }

    @staticmethod
    def from_dict(data: Dict):
        return Connection(data["name"], data["url"], data["arguments"])


class AddConnectionDialog(QDialog):
    def __init__(self, parent=None, connection=None, index=None):
        super().__init__(parent)
        self.setWindowTitle("Add Chisel Connection" if connection is None else "Edit Chisel Connection")
        self.setFixedSize(400, 200)

        self.connection = connection
        self.index = index

        layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.url_edit = QLineEdit()
        self.args_edit = QLineEdit()

        # Populate fields if editing
        if self.connection:
            self.name_edit.setText(self.connection.name)
            self.url_edit.setText(self.connection.url)
            self.args_edit.setText(self.connection.arguments)
        else:
            # Default argument includes "socks"
            self.args_edit.setText("socks")

        layout.addRow("Name:", self.name_edit)
        layout.addRow("URL:", self.url_edit)
        layout.addRow("Arguments:", self.args_edit)

        # Horizontal layout for Save, Cancel (and possibly Delete)
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        # If editing an existing connection, also add a Delete button
        if self.connection is not None and self.index is not None:
            self.delete_btn = QPushButton("Delete")
            # Optional: Make it red or style it differently
            # self.delete_btn.setStyleSheet("background-color: #e53935; color: white;")
            btn_layout.addWidget(self.delete_btn)
            self.delete_btn.clicked.connect(self.delete_connection)

        layout.addRow(btn_layout)
        self.setLayout(layout)

        # Signals
        self.save_btn.clicked.connect(self.save_connection)
        self.cancel_btn.clicked.connect(self.reject)

    def save_connection(self):
        name = self.name_edit.text().strip()
        url = self.url_edit.text().strip()
        args = self.args_edit.text().strip()

        if not name or not url:
            QMessageBox.warning(self, "Warning", "Name and URL cannot be empty.")
            return

        # Update existing or create new
        if self.connection:
            self.connection.name = name
            self.connection.url = url
            self.connection.arguments = args
        else:
            self.connection = Connection(name, url, args)

        self.accept()

    def delete_connection(self):
        """
        When the user clicks the 'Delete' button, call back to the parent
        to remove this connection from the list, then close.
        """
        main_window = self.parent()  # We expect the parent to be MainWindow
        if hasattr(main_window, 'delete_connection') and self.index is not None:
            main_window.delete_connection(self.index)
        self.reject()  # Or self.close(), ensures this dialog is done



class SettingsDialog(QDialog):
    """Dialog for application settings."""
    def __init__(self, parent=None, settings_data=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(400, 200)

        self.settings_data = settings_data if settings_data else {}

        layout = QFormLayout()

        # Startup combo box
        self.startup_combo = QComboBox()
        self.startup_combo.addItems([
            "When logged in",
            "On lid open",
            "Never",
            "Manual only"
        ])
        self.startup_combo.setCurrentText(self.settings_data.get("startup", "When logged in"))
        layout.addRow("Startup:", self.startup_combo)

        # Shutoff combo box
        self.shutoff_combo = QComboBox()
        self.shutoff_combo.addItems([
            "On log off",
            "On lid close",
            "Never",
        ])
        self.shutoff_combo.setCurrentText(self.settings_data.get("shutoff", "On log off"))
        layout.addRow("Shutoff:", self.shutoff_combo)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

        self.setLayout(layout)

        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn.clicked.connect(self.reject)

    @Slot()
    def save_settings(self):
        self.settings_data["startup"] = self.startup_combo.currentText()
        self.settings_data["shutoff"] = self.shutoff_combo.currentText()
        self.accept()


class MainWindow(QMainWindow):
    """Main window of the Chisel GUI Manager."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chisel GUI Manager")
        self.resize(600, 400)

        # Load config from file
        self.config_data = load_config()
        self.connections: List[Connection] = [
            Connection.from_dict(c) for c in self.config_data.get("connections", [])
        ]
        self.settings_data = self.config_data.get("settings", {})

        self.active_process = None  # Will hold the active chisel subprocess if any
        self.active_connection_index = None

        # To store references to connect/disconnect buttons for each row
        self.connection_buttons = []  # list of (connect_btn, disconnect_btn)

        # Central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top layout: big label + status indicator
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_widget.setLayout(top_layout)

        # SOCKS label
        self.top_label = QLabel(f"SOCKS5 {DEFAULT_SOCKS_HOST}:{DEFAULT_PORT}")
        self.top_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        top_layout.addWidget(self.top_label, alignment=Qt.AlignLeft)

        # Connection status label
        self.connection_status_label = QLabel("Not Connected")
        self.connection_status_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold;")
        top_layout.addWidget(self.connection_status_label, alignment=Qt.AlignRight)

        main_layout.addWidget(top_widget, alignment=Qt.AlignTop)

        # Connection list area
        self.connection_list_layout = QVBoxLayout()
        main_layout.addLayout(self.connection_list_layout)

        # Render connections
        self.render_connections()

        # Add button
        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(QSize(40, 40))
        self.add_btn.setStyleSheet(
            "border-radius: 20px;"
            "font-size: 24px;"
            "background-color: #2196F3;"
            "color: white;"
        )
        self.add_btn.clicked.connect(self.add_connection_dialog)
        main_layout.addWidget(self.add_btn, alignment=Qt.AlignRight)

        # System Tray
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon.fromTheme("network-wired"))
        self.tray_icon.setToolTip("Chisel GUI Manager")
        tray_menu = QMenu()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        tray_menu.addAction(exit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)  # Connect the signal
        self.tray_icon.show()
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_connection_status)
        self.status_timer.start(1000)

    def on_tray_icon_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.showNormal()
            self.activateWindow()
            QGuiApplication.processEvents()  # Ensure the window is focused

        # Timer to check process status
          # check every second

    def render_connections(self):
        """Render the connections in the layout."""
        # Clear current layout & button references
        self.connection_buttons.clear()
        for i in reversed(range(self.connection_list_layout.count())):
            item = self.connection_list_layout.itemAt(i)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            self.connection_list_layout.removeItem(item)

        for idx, conn in enumerate(self.connections):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(10, 5, 10, 5)
            row_layout.setSpacing(10)

            # Slightly lighter background, rounded corners
            row_widget.setStyleSheet("""
                background-color: #f0f0f0;
                border-radius: 10px;
            """)

            # Connection name + url
            text_widget = QWidget()
            text_layout = QVBoxLayout(text_widget)
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(0)
            name_label = QLabel(conn.name)
            name_label.setStyleSheet("color: black; font-weight: bold")
            url_label = QLabel(conn.url)
            url_label.setStyleSheet("color: gray; font-size: 10px;")
            text_layout.addWidget(name_label)
            text_layout.addWidget(url_label)
            row_layout.addWidget(text_widget, stretch=1)

            # Connect and Disconnect buttons
            connect_btn = QPushButton("Connect")
            
            disconnect_btn = QPushButton("Disconnect")

            disconnect_btn.setStyleSheet("color: black")
            connect_btn.setStyleSheet("color: black")

            # By default, if nothing is connected, all connect buttons are enabled, disconnect disabled:
            connect_btn.setEnabled(True)
            disconnect_btn.setEnabled(False)

            connect_btn.clicked.connect(lambda _, i=idx: self.connect_connection(i))
            disconnect_btn.clicked.connect(lambda _, i=idx: self.disconnect_connection(i))

            row_layout.addWidget(connect_btn)
            row_layout.addWidget(disconnect_btn)

            # Settings button
            settings_button = QPushButton("Settings")
            settings_button.setStyleSheet("color: black")
            settings_button.clicked.connect(lambda _, i=idx: self.open_connection_settings(i))
            row_layout.addWidget(settings_button)

            self.connection_list_layout.addWidget(row_widget)
            self.connection_buttons.append((connect_btn, disconnect_btn))

        # After creation, update button states
        self.update_buttons_state()

    def update_buttons_state(self):
        """
        Enable/disable Connect/Disconnect buttons for each connection based on
        which one is active.
        """
        for i, (connect_btn, disconnect_btn) in enumerate(self.connection_buttons):
            if self.active_connection_index is None:
                # No active connection => all "Connect" buttons enabled, "Disconnect" disabled
                connect_btn.setEnabled(True)
                disconnect_btn.setEnabled(False)
            else:
                if i == self.active_connection_index:
                    # For the active connection, disable "Connect", enable "Disconnect"
                    connect_btn.setEnabled(False)
                    disconnect_btn.setEnabled(True)
                else:
                    # For other connections, enable "Connect", disable "Disconnect"
                    connect_btn.setEnabled(True)
                    disconnect_btn.setEnabled(False)

    def delete_connection(self, index):
        """Remove the connection at 'index' from self.connections, then save & refresh."""
        if 0 <= index < len(self.connections):
            self.connections.pop(index)
            self.save_all()
            self.render_connections()
    def add_connection_dialog(self):
        """Open dialog to add new connection."""
        dialog = AddConnectionDialog(self)
        if dialog.exec():
            if dialog.connection is not None:
                self.connections.append(dialog.connection)
                self.save_all()
                self.render_connections()

    def open_connection_settings(self, index):
        connection_to_edit = self.connections[index]
        dialog = AddConnectionDialog(self, connection=connection_to_edit, index=index)
        if dialog.exec():
            # If the dialog closes normally (Save), changes are stored in connection_to_edit
            self.save_all()
            self.render_connections()


    def connect_connection(self, index):
        """
        Attempt to connect the selected connection.
        If another connection is active, disconnect it first.
        """
        # Stop any running process if different from this one
        if self.active_connection_index is not None and self.active_connection_index != index:
            self.stop_chisel_process()
            self.active_connection_index = None

        # If we don't already have the process running for this index, start it.
        if self.active_connection_index != index:
            self.active_connection_index = index
            self.start_chisel(self.connections[index])

        self.update_buttons_state()

    def disconnect_connection(self, index):
        """
        Disconnect if the given index is the currently active connection.
        """
        if self.active_connection_index == index:
            self.stop_chisel_process()
            self.active_connection_index = None
            self.update_buttons_state()

    def start_chisel(self, conn: Connection):
        """Launch the chisel client for a given connection in the background."""
        cmd = [
            "chisel",
            "client",
            conn.url,
        ]
        extra_args = conn.arguments.split()
        cmd.extend(extra_args)

        try:
            self.active_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print(f"Started Chisel with command: {' '.join(cmd)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start chisel:\n{str(e)}")
            self.active_process = None
            self.active_connection_index = None

    def stop_chisel_process(self):
        """Stop the currently running chisel process if any."""
        if self.active_process and self.active_process.poll() is None:
            self.active_process.terminate()
            self.active_process.wait()
            print("Stopped Chisel process.")
        self.active_process = None

    def update_connection_status(self):
        """
        Periodically check if the active chisel process is alive.
        If alive => show "Connected to {connection_name}" (green).
        Otherwise => "Not Connected" (red).
        """
        if self.active_connection_index is not None and self.active_process:
            if self.active_process.poll() is None:
                # Process is running => connected
                conn_name = self.connections[self.active_connection_index].name
                self.connection_status_label.setText(f"Connected to {conn_name}")
                self.connection_status_label.setStyleSheet("color: green; font-size: 14px; font-weight: bold;")
                return
            else:
                # Process ended unexpectedly
                self.stop_chisel_process()
                self.active_connection_index = None
                self.update_buttons_state()

        # If we reach here, not connected
        self.connection_status_label.setText("Not Connected")
        self.connection_status_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold;")

    def open_global_settings(self):
        """Open the global Settings dialog."""
        dialog = SettingsDialog(self, self.settings_data)
        if dialog.exec():
            self.settings_data = dialog.settings_data
            self.save_all()

    def closeEvent(self, event):
        """Override the close event to hide to tray or exit."""
        reply = QMessageBox.question(
            self,
            "Minimize to Tray?",
            "Do you want to close the window and keep it running in the system tray, or fully exit?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            event.ignore()
            self.hide()
        elif reply == QMessageBox.No:
            self.tray_icon.hide()
            self.stop_chisel_process()
            self.save_all()
            event.accept()
        else:
            event.ignore()

    def save_all(self):
        """Save all connections and settings to config file."""
        data = {
            "connections": [c.to_dict() for c in self.connections],
            "settings": self.settings_data
        }
        save_config(data)
        self.config_data = data


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
