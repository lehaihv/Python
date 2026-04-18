import sys
import serial.tools.list_ports
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QComboBox, QPushButton, QLabel, 
                             QFileDialog, QProgressBar, QMessageBox)
from PyQt6.QtCore import Qt
from ota_worker import OTAWorker

class UART_OTA_Tool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ESP32-S3 UART OTA Tool")
        self.setFixedSize(450, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Serial Config
        config_layout = QHBoxLayout()
        self.port_cb = QComboBox()
        self.refresh_ports()
        self.baud_cb = QComboBox()
        self.baud_cb.addItems(["9600", "115200", "230400", "921600"])
        self.baud_cb.setCurrentText("115200")
        
        config_layout.addWidget(QLabel("Port:"))
        config_layout.addWidget(self.port_cb)
        config_layout.addWidget(QLabel("Baud:"))
        config_layout.addWidget(self.baud_cb)
        layout.addLayout(config_layout)

        # File Selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("Select firmware .bin")
        self.file_label.setFrameStyle(1)
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(btn_browse)
        layout.addLayout(file_layout)

        # Progress
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Idle")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Action Button
        self.btn_send = QPushButton("Start OTA Update")
        self.btn_send.setFixedHeight(50)
        self.btn_send.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_send.clicked.connect(self.start_ota)
        layout.addWidget(self.btn_send)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def refresh_ports(self):
        self.port_cb.clear()
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb.addItems(ports)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Firmware", "", "Binary Files (*.bin)")
        if file_path:
            self.file_label.setText(file_path)

    def start_ota(self):
        port = self.port_cb.currentText()
        baud = int(self.baud_cb.currentText())
        file = self.file_label.text()

        if not port or ".bin" not in file:
            QMessageBox.warning(self, "Error", "Select Port and Valid .bin file!")
            return

        self.btn_send.setEnabled(False)
        self.worker = OTAWorker(port, baud, file)
        self.worker.progress_update.connect(self.progress_bar.setValue)
        self.worker.status_update.connect(self.status_label.setText)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success, message):
        self.btn_send.setEnabled(True)
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Failed", message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UART_OTA_Tool()
    window.show()
    sys.exit(app.exec())
