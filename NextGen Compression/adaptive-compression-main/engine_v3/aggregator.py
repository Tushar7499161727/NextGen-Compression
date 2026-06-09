import zlib

class SuperBlock:
    def __init__(self, label):
        self.label = label
        self.chunks = []
        self.size = 0
        self.checksum = 0
        
    def add_chunk(self, data):
        self.chunks.append(data)
        self.size += len(data)
        
    def finalize(self):
        full_data = b''.join(self.chunks)
        self.checksum = zlib.crc32(full_data) & 0xFFFFFFFF
        return full_data, self.checksum

class BlockAggregator:
    """
    Implements the '3-2-2' Aggregation Logic:
    - 3 Classification States (Text, Binary, Media)
    - 2 Consolidation Rules (Adjacency & Label-Match)
    - 2 Efficiency Goals (Dictionary Reuse & Stream Continuity)
    
    Merges adjacent chunks of the same type into SuperBlocks for maximum compression density.
    """
    
    def __init__(self, max_block_size=8 * 1024 * 1024):
        self.max_block_size = max_block_size
        
    def aggregate(self, chunk_stream):
        current_block = None
        
        for chunk in chunk_stream:
            data = chunk['data']
            label = chunk['label']
            
            # Start a new block if:
            # 1. No block exists
            # 2. Label changes
            # 3. Size limit reached
            if (not current_block or 
                current_block.label != label or 
                current_block.size + len(data) > self.max_block_size):
                
                if current_block:
                    block_data, crc = current_block.finalize()
                    yield {
                        'label': current_block.label,
                        'data': block_data,
                        'checksum': crc,
                        'size': current_block.size
                    }
                
                current_block = SuperBlock(label)
            
            current_block.add_chunk(data)
            
        # Yield the final block
        if current_block:
            block_data, crc = current_block.finalize()
            yield {
                'label': current_block.label,
                'data': block_data,
                'checksum': crc,
                'size': current_block.size
            }
