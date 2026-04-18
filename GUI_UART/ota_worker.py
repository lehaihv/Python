import time
import struct
import serial
from PyQt6.QtCore import QThread, pyqtSignal

# Protocol Constants
PKT_SOF          = 0x7E
PKT_DATA_SIZE    = 512
PKT_HEADER_SIZE  = 5
PKT_FOOTER_SIZE  = 2

CMD_OTA_START    = 0x0001
CMD_ACK          = 0x0002
CMD_NACK         = 0x0003
CMD_OTA_END      = 0x0004
CMD_OTA_OK       = 0x0005
CMD_OTA_FAIL     = 0x0006
CMD_ABORT        = 0x0007

OTA_TRIGGER      = bytes([0xAA, 0xBB, 0xCC, 0xDD])

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

    def crc16_ccitt(self, data: bytes):
        """Matches C++ crc16_buf (CCITT-FALSE)"""
        crc = 0xFFFF
        for byte in data:
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return crc

    def create_packet(self, seq_or_cmd, data=b""):
        """Wraps data in [SOF][SEQ/CMD][LEN][DATA][CRC]"""
        length = len(data)
        # Header: SOF(1), Seq/Cmd(2), Len(2)
        header = struct.pack(">BHH", PKT_SOF, seq_or_cmd, length)
        payload = header + data
        # CRC is calculated on everything except SOF
        crc = self.crc16_ccitt(payload[1:])
        return payload + struct.pack(">H", crc)

    def read_exact(self, ser, n, timeout=3.0):
        """Helper to read specific number of bytes within timeout"""
        data = b""
        start_time = time.time()
        while len(data) < n and (time.time() - start_time) < timeout:
            chunk = ser.read(n - len(data))
            if chunk:
                data += chunk
        return data if len(data) == n else None

    def wait_ack(self, ser, expected_seq, timeout=3.0):
        """Wait for an ACK packet matching the sequence number"""
        pkt_len = PKT_HEADER_SIZE + PKT_FOOTER_SIZE
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            sof = ser.read(1)
            if not sof or sof[0] != PKT_SOF:
                continue
            
            rest = self.read_exact(ser, pkt_len - 1, timeout=1.0)
            if not rest: continue
            
            # Unpack: [Seq(H)][Len(H)][CRC(H)]
            seq, length, crc = struct.pack(">HHH", *struct.unpack(">HH", rest[:4]), struct.unpack(">H", rest[4:])[0])
            # Simplified unpack for validation
            seq = (rest[0] << 8) | rest[1]
            # In your C++ code: cmd/ack is check via frame[4] (last byte of header)
            is_ack = (rest[3] == (CMD_ACK & 0xFF)) 
            
            if seq == expected_seq and is_ack:
                return True
        return False

    def run(self):
        try:
            with serial.Serial(self.port, self.baud, timeout=0.1) as ser:
                with open(self.file_path, "rb") as f:
                    fw_data = f.read()
                
                fw_size = len(fw_data)
                self.status_update.emit(f"Sending Trigger...")
                ser.write(OTA_TRIGGER)
                time.sleep(0.5)

                # 1. OTA_START
                success = False
                start_packet = self.create_packet(CMD_OTA_START, struct.pack(">I", fw_size))
                for i in range(5):
                    self.status_update.emit(f"OTA_START attempt {i+1}...")
                    ser.write(start_packet)
                    if self.wait_ack(ser, CMD_OTA_START):
                        success = True
                        break
                
                if not success:
                    self.finished.emit(False, "Slave failed to ACK OTA_START")
                    return

                # 2. Data Transfer
                offset = 0
                seq = 0
                while offset < fw_size:
                    if not self.is_running: return
                    
                    chunk_size = min(PKT_DATA_SIZE, fw_size - offset)
                    chunk = fw_data[offset : offset + chunk_size]
                    
                    pkt = self.create_packet(seq, chunk)
                    
                    retry = 0
                    pkt_acked = False
                    while retry < 5:
                        ser.write(pkt)
                        if self.wait_ack(ser, seq):
                            pkt_acked = True
                            break
                        retry += 1
                        self.status_update.emit(f"Retry seq {seq} ({retry}/5)...")
                    
                    if not pkt_acked:
                        ser.write(self.create_packet(CMD_ABORT))
                        self.finished.emit(False, f"Failed at seq {seq}")
                        return

                    offset += chunk_size
                    seq += 1
                    self.progress_update.emit(int((offset / fw_size) * 100))

                # 3. OTA_END
                self.status_update.emit("Ending OTA, verifying...")
                ser.write(self.create_packet(CMD_OTA_END))

                # 4. Final Result
                final_resp = self.read_exact(ser, PKT_HEADER_SIZE + PKT_FOOTER_SIZE, timeout=15.0)
                if final_resp and final_resp[0] == PKT_SOF:
                    cmd = (final_resp[1] << 8) | final_resp[2]
                    if cmd == CMD_OTA_OK:
                        self.finished.emit(True, "Update Successful! Slave rebooting.")
                    else:
                        self.finished.emit(False, f"Slave reported failure: 0x{cmd:04X}")
                else:
                    self.finished.emit(True, "Update sent. No final ACK (Slave likely rebooted).")

        except Exception as e:
            self.finished.emit(False, str(e))
