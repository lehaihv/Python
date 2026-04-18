import time
import serial
from PyQt6.QtCore import QThread, pyqtSignal

class OTAWorker(QThread):
    progress_update = pyqtSignal(int)
    status_update = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, port, baud, file_path):
        super().__init__()
        self.port = port
        self.baud = baud
        self.file_path = file_path
        self.is_running = True

    def run(self):
        try:
            with serial.Serial(self.port, self.baud, timeout=2) as ser:
                self.status_update.emit("Opening file...")
                with open(self.file_path, "rb") as f:
                    firmware_data = f.read()
                    total_size = len(firmware_data)
                
                # 1. Handshake
                self.status_update.emit("Sending Handshake...")
                ser.write(b'\xAA\x55') # Example Handshake bytes
                response = ser.read(2)
                
                if response != b'\x55\xAA':
                    self.finished.emit(False, "Handshake failed! Slave not responding.")
                    return

                # 2. Transfer Data
                chunk_size = 256  # Matches ESP32 buffer size
                offset = 0
                self.status_update.emit("Transferring Firmware...")

                while offset < total_size:
                    if not self.is_running:
                        break
                    
                    chunk = firmware_data[offset : offset + chunk_size]
                    ser.write(chunk)
                    
                    # Wait for ACK for this chunk
                    ack = ser.read(1)
                    if ack != b'\x06': # Standard ACK (0x06)
                        self.finished.emit(False, f"Error at offset {offset}")
                        return

                    offset += len(chunk)
                    progress = int((offset / total_size) * 100)
                    self.progress_update.emit(progress)

                # 3. Finalize
                ser.write(b'\x04') # End of Transmission (EOT)
                self.status_update.emit("Update Complete!")
                self.finished.emit(True, "Firmware updated successfully!")

        except Exception as e:
            self.finished.emit(False, str(e))

    def stop(self):
        self.is_running = False
