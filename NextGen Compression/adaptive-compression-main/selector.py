import math
import time
import os
import subprocess
import psutil

# Default baselines
PERF_LOOKUP = {
    "7zip": {"ratio_factor": 0.35, "speed_mbps": 10.0},
    "zstd": {"ratio_factor": 0.55, "speed_mbps": 70.0},
    "paq":  {"ratio_factor": 0.15, "speed_mbps": 0.4},
    "webp": {"ratio_factor": 0.20, "speed_mbps": 25.0},
    "ffmpeg": {"ratio_factor": 0.30, "speed_mbps": 15.0} # Encoding is slower but very efficient
}

DYNAMIC_PERF = PERF_LOOKUP.copy()

def get_system_ram_safety():
    """Returns available RAM in GB."""
    return psutil.virtual_memory().available / (1024 ** 3)

def calibrate_speeds(bin_paths):
    """Benchmarks hardware to update speed assumptions."""
    global DYNAMIC_PERF
    test_file = "calib_test.tmp"
    test_out = "calib_test.out"
    
    # Create ~2MB of dummy data
    with open(test_file, "wb") as f:
        f.write(os.urandom(1024 * 1024) + b"A" * (1024 * 1024))

    for tool, path in bin_paths.items():
        if not os.path.exists(path): continue
        
        # Build test command
        cmd = [path, "a", test_out, test_file] if "7za" in path else [path, test_file, "-o", test_out]
        
        start = time.time()
        try:
            # 0x08000000 is CREATE_NO_WINDOW for Windows
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                           creationflags=0x08000000, timeout=5)
            duration = time.time() - start
            DYNAMIC_PERF[tool]["speed_mbps"] = 2.0 / max(duration, 0.001)
        except:
            pass 

    for f in [test_file, test_out]:
        if os.path.exists(f): os.remove(f)

def score_algo(features, perf_estimate, constraints):
    size = features.get('size_bytes', 0)
    if size <= 0 or not perf_estimate: return -99999

    compression_gain = (size - perf_estimate['expected_size']) / size
    max_t = constraints.get('max_time', 60)
    time_ratio = perf_estimate['expected_time'] / (max_t if max_t > 0 else 1)
    
    priority = constraints.get('priority', 'balanced')
    if priority == 'size':
        w_gain, w_time = 25.0, 0.5  
    elif priority == 'speed':
        w_gain, w_time = 1.0, 20.0
    else:
        w_gain, w_time = 8.0, 4.0

    score = (w_gain * compression_gain) - (w_time * time_ratio)
    
    if perf_estimate['expected_time'] > max_t:
        score -= 500 
        
    return score

def get_battery_status():
    """Returns (is_on_battery, percent)."""
    try:
        battery = psutil.sensors_battery()
        if battery:
            return not battery.power_plugged, battery.percent
    except:
        pass
    return False, 100

def get_network_status():
    """Returns (is_congested, speed_kbps)."""
    try:
        net1 = psutil.net_io_counters()
        time.sleep(0.1)
        net2 = psutil.net_io_counters()
        # Calculate KB/s
        speed = ((net2.bytes_sent - net1.bytes_sent) + (net2.bytes_recv - net1.bytes_recv)) / 102.4
        return speed > 500, speed # Congested if > 500 KB/s
    except:
        return False, 0

def get_best_tool(features, constraints):
    """
    Final decision engine with Memory, Power & Network Guard.
    """
    if not features: return "zstd"

    # --- POWER GUARD ---
    on_battery, battery_pct = get_battery_status()
    actual_constraints = constraints.copy()
    
    # If on battery, we favor SPEED to save energy
    if on_battery:
        if actual_constraints.get('priority') == 'size':
            actual_constraints['priority'] = 'balanced'
        elif actual_constraints.get('priority') == 'balanced':
            actual_constraints['priority'] = 'speed'

    # --- NETWORK GUARD ---
    # If network is busy, prioritize SIZE to save upload bandwidth
    is_congested, _ = get_network_status()
    if is_congested and constraints.get('network_aware', True):
        actual_constraints['priority'] = 'size'

    # --- MEMORY GUARD ---
    available_ram = get_system_ram_safety()
    # PAQ is extremely RAM hungry. If RAM < 3GB, we force-disable PAQ.
    ram_restricted = []
    if available_ram < 3.0 or (on_battery and battery_pct < 25):
        ram_restricted.append("paq")

    # --- FEATURE EXTRACTION ---
    entropy = features.get('entropy', 0)
    repetition = features.get('repetition', 0)
    size_mb = features.get('size_bytes', 0) / (1024 * 1024)
    visual = features.get('visual', {})
    is_image = visual.get('is_image', False)
    is_video = visual.get('is_video', False)
    is_media = is_image or is_video

    # --- MEDIA GUARD ---
    if is_image:
        # If it's an image, WebP is almost always superior for ratio
        if entropy < 7.9:
            return "webp"
        else:
            # Already optimized image
            for tool in DYNAMIC_PERF:
                 DYNAMIC_PERF[tool]['ratio_factor'] = 0.99
    
    if is_video:
        # For video, FFmpeg is the absolute king
        if entropy < 7.9:
            return "ffmpeg"
        else:
            # Already compressed video
            for tool in DYNAMIC_PERF:
                 DYNAMIC_PERF[tool]['ratio_factor'] = 0.99
             
    best_tool = "zstd"
    best_score = -float('inf')
    
    # Bypass if data is uncompressible (Media like encrypted video)
    if entropy >= 7.99 and not is_media:
        return "SKIP"

    for tool, stats in DYNAMIC_PERF.items():
        # --- Engine Filtering ---
        if tool in ram_restricted: continue
        
        # WEBP is only for images
        if tool == "webp" and not is_image: continue
        
        # FFMPEG is only for videos
        if tool == "ffmpeg" and not is_video: continue

        # PAQ is too slow for very large files
        if size_mb > 500 and tool == "paq": continue

        # --- Scoring ---
        predicted_ratio = max(stats['ratio_factor'], entropy / 8.0)
        if repetition > 0.2:
            predicted_ratio -= (repetition * 0.12)

        predicted_ratio = max(0.01, min(predicted_ratio, 1.01))
        
        estimate = {
            'expected_size': features['size_bytes'] * predicted_ratio,
            'expected_time': size_mb / stats['speed_mbps']
        }
        
        score = score_algo(features, estimate, actual_constraints)
        
        if score > best_score:
            best_score = score
            best_tool = tool
            
    return best_tool