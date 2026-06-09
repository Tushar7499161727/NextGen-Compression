from .profiler import SlidingWindowSlicer
from .aggregator import BlockAggregator
from .compressor import MultiStreamCompressor
from .container import AdaptiveContainer
import os
import zlib
import subprocess
import tempfile

class AdaptiveEngineV3:
    def __init__(self, bin_dir):
        self.bin_dir = bin_dir
        self.compressor = MultiStreamCompressor(bin_dir)
        self.bins = {
            'zstd': os.path.join(bin_dir, 'zstd.exe'),
            '7zip': os.path.join(bin_dir, '7za.exe'),
        }

    def compress_file(self, input_path, output_path):
        slicer = SlidingWindowSlicer(input_path)
        aggregator = BlockAggregator()
        container = AdaptiveContainer(output_path)
        
        def processed_block_stream():
            for block in aggregator.aggregate(slicer.stream_chunks()):
                comp_data, algo = self.compressor.compress_block(block)
                yield {
                    'label': block['label'],
                    'algo': algo,
                    'data': comp_data,
                    'checksum': block['checksum'],
                    'orig_size': block['size']
                }
        
        container.write_package(processed_block_stream())

    def decompress_file(self, input_path, output_dir):
        manifest = AdaptiveContainer.read_manifest(input_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # In this v3 prototype, we assume we are decompressing a single combined file
        # To keep it simple, we'll restore it to "[filename]_restored.ext"
        base_name = os.path.basename(input_path).replace('.adaptive', '').replace('.adapt', '')
        output_path = os.path.join(output_dir, base_name)
        
        with open(output_path, 'wb') as out_f:
            with open(input_path, 'rb') as in_f:
                for block in manifest:
                    in_f.seek(block['start'])
                    comp_data = in_f.read(block['end'] - block['start'])
                    
                    decomp_data = self._decompress_block(comp_data, block['algo'])
                    
                    # Verify Integrity
                    crc = zlib.crc32(decomp_data) & 0xFFFFFFFF
                    if crc != block['checksum']:
                        print(f"Warning: Block {block['id']} Checksum Mismatch! Data might be corrupt.")
                        # In a real system, we'd try to recover or skip.
                    
                    out_f.write(decomp_data)
        
        return output_path

    def _decompress_block(self, data, algo):
        if algo == "STORE":
            return data
            
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_tmp = os.path.join(tmp_dir, "comp.bin")
            output_tmp = os.path.join(tmp_dir, "raw.bin")
            
            with open(input_tmp, "wb") as f:
                f.write(data)

            if algo == "ZSTD_T":
                cmd = [self.bins['zstd'], '-d', input_tmp, '-o', output_tmp, '-f']
                subprocess.run(cmd, creationflags=0x08000000, stderr=subprocess.DEVNULL)
            
            elif algo.startswith("7Z"):
                # 7zip 'e' reads from archive file
                cmd = [self.bins['7zip'], 'e', input_tmp, f'-o{tmp_dir}', '-aoa', '-y']
                subprocess.run(cmd, creationflags=0x08000000, stderr=subprocess.DEVNULL)
                
                # 7zip might have changed the name inside the temp archive
                files = [os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir) if f != "comp.bin"]
                if files:
                    # Find the extracted block
                    output_tmp = max(files, key=os.path.getsize)
                    if os.path.exists(output_tmp):
                        with open(output_tmp, "rb") as f:
                            return f.read()

            if algo == "ZSTD_T" and os.path.exists(output_tmp):
                with open(output_tmp, "rb") as f:
                    return f.read()
        
        return data # Fallback
