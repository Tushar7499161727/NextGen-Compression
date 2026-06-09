import os
import math
import re
from collections import Counter

class HeuristicClassifier:
    """Classifies data chunks using entropy, headers, and statistical sampling."""
    
    @staticmethod
    def shannon_entropy(data):
        if not data:
            return 0
        entropy = 0
        counts = Counter(data)
        for count in counts.values():
            p_x = count / len(data)
            entropy -= p_x * math.log2(p_x)
        return entropy

    @staticmethod
    def classify(chunk):
        # 1. Magic Byte Check (Common Headers)
        if chunk.startswith(b'\xFF\xD8\xFF'): return 'IMAGE' # JPEG
        if chunk.startswith(b'\x89PNG\r\n\x1a\n'): return 'IMAGE' # PNG
        if chunk.startswith(b'%PDF'): return 'IMAGE' # Treating PDF as complex/image stream often better
        if chunk.startswith(b'BM'): return 'IMAGE' # BMP
        
        # 2. Entropy Check
        entropy = HeuristicClassifier.shannon_entropy(chunk[:16384]) # Check first 16KB for speed
        
        # 3. Text/Regex Sampling
        try:
            # Check if chunk is mostly valid ASCII/printable
            text_part = chunk[:4096].decode('utf-8', errors='ignore')
            printable = sum(1 for c in text_part if 32 <= ord(c) <= 126 or ord(c) in [9, 10, 13])
            if printable / max(len(text_part), 1) > 0.9 and entropy < 5.5:
                # Further check with regex for common code/text patterns
                if re.search(r'[a-zA-Z0-9_\-]{4,}', text_part):
                    return 'TEXT'
        except:
            pass
            
        # 4. Binary/Compressed Detection
        # If entropy is very high (> 7.8), it's likely already compressed media or encrypted
        if entropy > 7.5:
            return 'BINARY_COMPRESSED'
            
        return 'MIXED_BINARY'

class SlidingWindowSlicer:
    """Reads a file and yields classified chunks."""
    
    def __init__(self, file_path, chunk_size=1024 * 1024):
        self.file_path = file_path
        self.chunk_size = chunk_size
        
    def stream_chunks(self):
        if not os.path.exists(self.file_path):
            return
            
        with open(self.file_path, 'rb') as f:
            while True:
                data = f.read(self.chunk_size)
                if not data:
                    break
                
                label = HeuristicClassifier.classify(data)
                yield {'data': data, 'label': label, 'size': len(data)}
