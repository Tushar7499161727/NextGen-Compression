import os
import csv
from datetime import datetime

PERF_TABLE_PATH = "data/perf_table.csv"
LOG_DIR = "data/logs"

def init_storage():
    """Ensure folders and CSV headers exist."""
    os.makedirs("data", exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    
    if not os.path.exists(PERF_TABLE_PATH):
        with open(PERF_TABLE_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["algo", "sample_type", "time", "ratio", "timestamp"])

def log_performance(algo, sample_type, time_taken, ratio):
    """Appends actual run data to the historical table."""
    with open(PERF_TABLE_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([algo, sample_type, round(time_taken, 4), round(ratio, 4), datetime.now()])

def log_demo_run(data_dict):
    """Creates a unique log for the demo presentation."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(LOG_DIR, f"demo_run_{timestamp}.csv")
    
    with open(log_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=data_dict.keys())
        writer.writeheader()
        writer.writerow(data_dict)
    return log_path