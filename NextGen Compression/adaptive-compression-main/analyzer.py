import os
import math
from collections import Counter

def shannon_entropy(data):
    """
    Calculates the Shannon Entropy of the data.
    Higher entropy (close to 8.0) means the data is already compressed/encrypted.
    Lower entropy means it is highly compressible.
    """
    if not data:
        return 0
    entropy = 0
    counts = Counter(data)
    for count in counts.values():
        p_x = count / len(data)
        entropy -= p_x * math.log2(p_x)
    return entropy

from PIL import Image

def sample_features(file_path, sample_kb=64):
    """
    Analyzes a file using statistical and VISUAL heuristics.
    """
    if not os.path.exists(file_path) or os.path.isdir(file_path):
        return None
        
    size = os.path.getsize(file_path)
    ext = file_path.lower().split('.')[-1]
    
    # --- VISUAL INTELLIGENCE ---
    img_type = None
    img_dims = None
    is_video = ext in ['mp4', 'mkv', 'avi', 'mov', 'flv', 'wmv']
    
    if ext in ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp']:
        try:
            with Image.open(file_path) as img:
                img_type = img.format
                img_dims = img.size # (width, height)
        except:
            pass

    # If the file is smaller than our sample size, just read the whole thing
    read_size = min(size, sample_kb * 1024)
    
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(read_size)
    except Exception:
        return None
    
    if not sample:
        return {'entropy': 0, 'size_bytes': size, 'is_text': False, 'repetition': 0, 'compressible': False}

    # 1. Calculate Shannon Entropy (0.0 to 8.0)
    entropy = shannon_entropy(sample)
    
    # 2. Structural Repetition (4-byte sliding window)
    chunks = [sample[i:i+4] for i in range(0, len(sample) - 3, 4)]
    repetition_ratio = 1.0 - (len(set(chunks)) / len(chunks)) if chunks else 0
    
    # 3. Robust Text vs Binary detection
    null_count = sample.count(0)
    text_chars = sum(1 for c in sample if 32 <= c <= 126 or c in (9,10,13))
    text_ratio = text_chars / len(sample)
    
    # Heuristic for text: High printable ratio AND low null-byte count
    is_text = text_ratio > 0.8 and null_count < (len(sample) * 0.01)
    
    # 4. Final Compressibility Heuristic
    # If entropy is > 7.5, the file is likely already a ZIP, JPG, or Encrypted.
    is_compressible = entropy < 7.5 or repetition_ratio > 0.1

    return {
        'entropy': round(entropy, 2),
        'size_bytes': size,
        'size_mb': round(size / (1024 * 1024), 2),
        'is_text': is_text,
        'repetition': round(repetition_ratio, 4),
        'compressible': is_compressible,
        'magic': sample[:8].hex().upper(),
        'visual': {
            'is_image': img_type is not None,
            'is_video': is_video,
            'format': img_type,
            'dimensions': img_dims
        }
    }