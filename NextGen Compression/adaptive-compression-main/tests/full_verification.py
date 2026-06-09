import os
import subprocess
import time
from analyzer import sample_features
from selector import get_best_tool
from compressor_manager import CompressorManager
import runner
from engine_v3.core import AdaptiveEngineV3

def test_system():
    print("=== STARTING FULL SYSTEM VERIFICATION ===\n")
    
    # 1. Binary Check
    manager = CompressorManager()
    engines = ["7zip", "zstd", "paq", "webp", "ffmpeg"]
    print("--- 1. Engine Binary Check ---")
    for engine in engines:
        exe = manager.bins.get(engine)
        if engine == "tar":
            print(f"[OK] {engine}: System Built-in")
            continue
        if exe and os.path.exists(exe):
            print(f"[OK] {engine}: Found at {os.path.basename(exe)}")
        else:
            print(f"[FAIL] {engine}: MISSING!")
            
    # 2. Logic Check: Heuristics
    print("\n--- 2. Heuristic Logic Verification ---")
    
    # Test cases: (name, features)
    test_cases = [
        ("Text File", {'entropy': 4.5, 'visual': {'is_image': False, 'is_video': False}, 'size_bytes': 1024*1024}),
        ("Image File", {'entropy': 6.5, 'visual': {'is_image': True, 'is_video': False}, 'size_bytes': 2*1024*1024}),
        ("Video File", {'entropy': 7.1, 'visual': {'is_image': False, 'is_video': True}, 'size_bytes': 50*1024*1024}),
        ("Already Compressed", {'entropy': 7.95, 'visual': {'is_image': False, 'is_video': False}, 'size_bytes': 1*1024*1024})
    ]
    
    for name, feat in test_cases:
        best = get_best_tool(feat, {"priority": "ratio", "max_time": 3600})
        print(f"[{name}] Suggested: {best}")
        
    # 3. Compression Round-trip (Small dummy files)
    print("\n--- 3. Compression Round-trip (Tiny Tests) ---")
    test_dir = "test_run"
    os.makedirs(test_dir, exist_ok=True)
    
    try:
        # Create a text file
        txt_file = os.path.join(test_dir, "test.txt")
        with open(txt_file, "w") as f:
            f.write("A" * 1000 + "B" * 1000 + "C" * 1000)
            
        # Test Zstd
        zst_out = txt_file + ".zst"
        zst_cmd = manager.get_command("zstd", txt_file, zst_out)
        res = runner.run_compressor(zst_cmd, txt_file, zst_out)
        if res['success']:
            print(f"[OK] Zstd Compression Success")
            # Decompress
            zst_dec = os.path.join(test_dir, "test_dec.txt")
            dec_cmd = manager.get_decompress_command(zst_out, zst_dec, "zst")
            dec_res = runner.run_compressor(dec_cmd, zst_out, zst_dec)
            if dec_res['success']:
                print(f"[OK] Zstd Decompression Success")
            else:
                print(f"[FAIL] Zstd Decompression: {dec_res['error']}")
        else:
            print(f"[FAIL] Zstd Compression: {res['error']}")
            
        # Test WebP (Simulated image)
        # Note: cwebp needs a real image format like PNG/JPG/TIFF
        # We'll skip actual cwebp run unless we have a tiny tiff, but we checked binary exists.
        
        # Test Tar
        tar_out = os.path.join(test_dir, "test.tar")
        tar_cmd = manager.get_command("tar", txt_file, tar_out)
        res = runner.run_compressor(tar_cmd, txt_file, tar_out)
        if res['success']:
            print(f"[OK] Tar Archiving Success")
        else:
            print(f"[FAIL] Tar Archiving: {res['error']}")

        # 4. V3 Pipeline (Super-Block)
        print("\n--- 4. V3 Pipeline Integration ---")
        v3_out = txt_file + ".adaptive"
        v3_engine = AdaptiveEngineV3(bin_dir=manager.bin)
        success = v3_engine.compress_file(txt_file, v3_out)
        if os.path.exists(v3_out):
            print("[OK] V3 Engine Compression Success")
            v3_dec = os.path.join(test_dir, "v3_extracted")
            os.makedirs(v3_dec, exist_ok=True)
            dec_out = v3_engine.decompress_file(v3_out, v3_dec)
            if os.path.exists(dec_out):
                print("[OK] V3 Engine Decompression Success")
            else:
                print("[FAIL] V3 Engine Decompression")
        else:
            print("[FAIL] V3 Engine Compression")
            
    finally:
        # Cleanup
        import shutil
        # shutil.rmtree(test_dir, ignore_errors=True)
        pass

    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    test_system()
