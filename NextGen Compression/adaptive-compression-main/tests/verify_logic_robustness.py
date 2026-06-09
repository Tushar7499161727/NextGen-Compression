import os
import shutil
import time
import sys

# Add current dir to sys.path to import local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import compressor_manager
import runner
import analyzer

def setup_test_env():
    test_root = os.path.join(current_dir, "test_workspace")
    if os.path.exists(test_root):
        shutil.rmtree(test_root)
    os.makedirs(test_root)
    return test_root

def create_dummy_file(path, size_kb=10):
    with open(path, "wb") as f:
        f.write(os.urandom(size_kb * 1024))

def test_collision_handling():
    root = setup_test_env()
    manager = compressor_manager.CompressorManager()
    
    # 1. Test Compression with Existing Archive
    print("\n--- Test 1: Compression with Existing Archive ---")
    src = os.path.join(root, "source.txt")
    create_dummy_file(src)
    archive = src + ".adapt"
    
    # Create a "fake" existing archive
    with open(archive, "w") as f: f.write("Already here")
    
    print(f"Compressing {src} to {archive} (where {archive} already exists)...")
    cmd = manager.get_command("7zip", src, archive, level="fast")
    res = runner.run_compressor(cmd, src, archive)
    
    if res.get("success"):
        print("Success: 7zip handled overwrite/append.")
    else:
        print(f"FAILED: {res.get('error')}")

    # 2. Test Decompression with Existing Original
    print("\n--- Test 2: Decompression with Existing Original ---")
    dest = src # source.txt
    # Archive is already created from Test 1
    
    # Ensure source exists (as a collision)
    create_dummy_file(dest, size_kb=5) # Smaller to see if it changes
    
    print(f"Decompressing {archive} to {dest} (where {dest} already exists)...")
    
    # Simulate the logic I put in app.py
    if os.path.exists(dest):
        try:
            os.remove(dest)
            print("Cleanup: Removed existing destination file.")
        except Exception as e:
            print(f"CRITICAL: Failed to remove collision: {e}")

    ext = archive.split('.')[-1]
    cmd = manager.get_decompress_command(archive, dest, ext)
    res = runner.run_compressor(cmd, archive, dest)
    
    if res.get("success") and os.path.exists(dest):
        print(f"Success: Decompressed file restored. Size: {os.path.getsize(dest)} bytes")
    else:
        print(f"FAILED: {res.get('error')}")

    # 3. Test Folder Collision (File name is same as a folder)
    print("\n--- Test 3: File vs Folder Collision ---")
    folder_path = os.path.join(root, "collision_test")
    os.makedirs(folder_path)
    
    # Now try to decompress something that wants to be named "collision_test"
    dummy_archive = os.path.join(root, "collision_test.adapt")
    # We'll just reuse the valid 7z from before but rename for test
    shutil.copy(archive, dummy_archive)
    
    print(f"Decompressing {dummy_archive} over a FOLDER named {folder_path}...")
    
    # Logic in app.py (updated to handle folder)
    if os.path.exists(folder_path):
        try:
            if os.path.isdir(folder_path):
                shutil.rmtree(folder_path)
                print("Cleanup: Removed colliding directory.")
            else:
                os.remove(folder_path)
        except Exception as e:
            print(f"Error cleaning up: {e}")

    cmd = manager.get_decompress_command(dummy_archive, folder_path, "adapt")
    res = runner.run_compressor(cmd, dummy_archive, folder_path)
    
    if res.get("success") and os.path.isfile(folder_path):
        print("Success: Folder collision resolved.")
    else:
        print(f"FAILED: {res.get('error')}")

if __name__ == "__main__":
    try:
        test_collision_handling()
    except Exception as e:
        print(f"Test crashed: {e}")
