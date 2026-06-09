# simulator.py

def simulate_transfer(bytes_size, bandwidth_kbps=512, loss_rate=0.02):
    """
    Calculates estimated transfer time including the cost of packet loss.
    """
    if bytes_size <= 0:
        return 0
        
    bits = bytes_size * 8
    bps = bandwidth_kbps * 1000
    
    # Base time: Total bits / speed
    base_seconds = bits / bps
    
    # Retransmission factor: If loss is 5%, we expect to send 1.05x the data
    # Formula: 1 / (1 - P)
    loss_multiplier = 1 / (1 - loss_rate) if loss_rate < 1 else 100
    
    return base_seconds * loss_multiplier

def format_time(seconds):
    """Converts raw seconds into a readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"