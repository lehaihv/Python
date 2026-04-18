import sys
import serial.tools.list_ports
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QComboBox, QPushButton, QLabel, 
                             QFileDialog, QProgressBar, QMessageBox)
from ota_worker import OTAWorker

class OTATool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ESP32 CAN-OTA Master Tool")
        self.setFixedSize(400, 250)
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        layout = QVBoxLayout()

        # Port Selection
        port_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        self.refresh_ports()
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "115200", "921600", "1000000"])
        self.baud_combo.setCurrentText("115200")
        
        port_layout.addWidget(QLabel("Port:"))
        port_layout.addWidget(self.port_combo)
        port_layout.addWidget(QLabel("Baud:"))
        port_layout.addWidget(self.baud_combo)
        layout.addLayout(port_layout)

        # File Selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(btn_browse)
        layout.addLayout(file_layout)

        # Progress and Status
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel("Status: Idle")
        layout.addWidget(self.status_label)

        # Send Button
        self.btn_send = QPushButton("Start OTA Update")
        self.btn_send.clicked.connect(self.start_ota)
        self.btn_send.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        layout.addWidget(self.btn_send)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def refresh_ports(self):
        self.port_combo.clear()
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo.addItems(ports)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Firmware", "", "Binary Files (*.bin)")
        if file_path:
            self.file_label.setText(file_path)

    def start_ota(self):
        port = self.port_combo.currentText()
        baud = int(self.baud_combo.currentText())
        file_path = self.file_label.text()

        if not port or file_path == "No file selected":
            QMessageBox.warning(self, "Error", "Please select a port and a firmware file.")
            return

        self.btn_send.setEnabled(False)
        self.worker = OTAWorker(port, baud, file_path)
        self.worker.progress_update.connect(self.progress_bar.setValue)
        self.worker.status_update.connect(self.status_label.setText)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success, message):
        self.btn_send.setEnabled(True)
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OTATool()
    window.show()
    sys.exit(app.exec())
