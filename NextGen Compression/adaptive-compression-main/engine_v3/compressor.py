import subprocess
import os
import tempfile
import time

class MultiStreamCompressor:
    """Bridges SuperBlocks to offline binaries (zstd, 7za)."""
    
    def __init__(self, bin_dir):
        self.bin_dir = bin_dir
        self.bins = {
            'zstd': os.path.join(bin_dir, 'zstd.exe'),
            '7zip': os.path.join(bin_dir, '7za.exe'),
        }

    def _run_binary(self, cmd):
        try:
            # 0x08000000 = CREATE_NO_WINDOW
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                creationflags=0x08000000,
                timeout=30
            )
            return result.returncode == 0, result.stdout
        except:
            return False, b""

    def compress_block(self, block):
        """
        Compresses a single block using the best tool.
        Returns (compressed_data, algorithm_used).
        """
        label = block['label']
        data = block['data']
        
        # Temp files for binary interaction
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_tmp = os.path.join(tmp_dir, "input.raw")
            output_tmp = os.path.join(tmp_dir, "output.compressed")
            
            with open(input_tmp, "wb") as f:
                f.write(data)

            success = False
            compressed_data = None
            algo = "STORE"

            if label == 'TEXT' and os.path.exists(self.bins['zstd']):
                # Text -> Zstd High
                cmd = [self.bins['zstd'], '-19', '-f', input_tmp, '-o', output_tmp]
                ok, _ = self._run_binary(cmd)
                if ok and os.path.exists(output_tmp):
                    success, algo = True, "ZSTD_T"
            
            elif label == 'IMAGE' and os.path.exists(self.bins['7zip']):
                # Image -> 7z LZMA2
                # 'a' is add, '-mx9' is ultra, '-si' is stdin but we use files for reliability
                cmd = [self.bins['7zip'], 'a', '-mx9', '-si', output_tmp]
                # Piping manually since 7za 'a' with -si reads stdin
                try:
                    process = subprocess.Popen(
                        [self.bins['7zip'], 'a', '-mx9', '-si', output_tmp],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=0x08000000
                    )
                    process.communicate(input=data)
                    if process.returncode == 0 and os.path.exists(output_tmp):
                        success, algo = True, "7Z_I"
                except:
                    pass

            # Fallback for BINARY or failed compression
            if not success and os.path.exists(self.bins['7zip']):
                # Fast packing
                try:
                    process = subprocess.Popen(
                        [self.bins['7zip'], 'a', '-mx1', '-si', output_tmp],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=0x08000000
                    )
                    process.communicate(input=data)
                    if process.returncode == 0 and os.path.exists(output_tmp):
                        success, algo = True, "7Z_F"
                except:
                    pass

            if success:
                with open(output_tmp, "rb") as f:
                    compressed_data = f.read()
                
                # Check if compression actually made it smaller
                if len(compressed_data) >= len(data):
                    return data, "STORE"
                return compressed_data, algo
            
            return data, "STORE"
