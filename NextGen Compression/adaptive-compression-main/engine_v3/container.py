import json
import struct
import os

class AdaptiveContainer:
    """Handles the V3 binary format with Dual Manifests."""
    
    def __init__(self, output_path):
        self.output_path = output_path
        self.blocks = []
        self.current_offset = 0

    def _align_to_4kb(self, f):
        padding = (4096 - (f.tell() % 4096)) % 4096
        if padding > 0:
            f.write(b'\x00' * padding)
        return f.tell()

    def write_package(self, block_stream):
        """Streams blocks into the final binary file."""
        with open(self.output_path, 'wb') as f:
            # 1. Header: Signature(7) + ManifestOffset(8)
            f.write(b'ADAPTV3')
            f.write(struct.pack('<Q', 0)) # Placeholder for Manifest Offset
            self.current_offset = 15

            for block in block_stream:
                self.current_offset = self._align_to_4kb(f)
                
                start_off = self.current_offset
                f.write(block['data'])
                end_off = f.tell()
                
                self.blocks.append({
                    'id': len(self.blocks),
                    'type': block['label'],
                    'algo': block['algo'],
                    'start': start_off,
                    'end': end_off,
                    'checksum': block['checksum'],
                    'orig_size': block['orig_size']
                })
                self.current_offset = end_off

            # 2. Write Manifest (Tail)
            manifest_json = json.dumps(self.blocks).encode('utf-8')
            manifest_size = len(manifest_json)
            
            manifest_start = f.tell()
            f.write(manifest_json)
            f.write(struct.pack('<Q', manifest_size)) # 8 bytes size
            f.write(b'ADAPTV3') # Signature
            
            # 3. Update Header with the real offset
            f.seek(7)
            f.write(struct.pack('<Q', manifest_start))
            
        print(f"Package created: {self.output_path} ({len(self.blocks)} blocks)")

    @staticmethod
    def read_manifest(path):
        """Reads the manifest from the end of the file (robust to header damage)."""
        file_size = os.path.getsize(path)
        with open(path, 'rb') as f:
            # Check Tail first
            f.seek(-15, os.SEEK_END)
            footer = f.read(15)
            if footer.endswith(b'ADAPTV3'):
                size = struct.unpack('<Q', footer[:8])[0]
                if size > file_size: raise ValueError("Manifest size exceeds file size.")
                f.seek(-(15 + size), os.SEEK_END)
                manifest_data = f.read(size)
            else:
                # Fallback to Header
                f.seek(0)
                sig = f.read(7)
                if sig != b'ADAPTV3': raise ValueError("Invalid binary signature.")
                m_off = struct.unpack('<Q', f.read(8))[0]
                if m_off > file_size: raise ValueError("Manifest offset out of bounds.")
                f.seek(m_off)
                # We need to know where the manifest ends if reading from header
                # For simplicity in this v3, we assume tail is preferred.
                # If we really want robustness, we'd store manifest size in header too.
                # Let's just read until the tail footer begins.
                manifest_data = f.read(file_size - m_off - 15)
            
            return json.loads(manifest_data.decode('utf-8'))
