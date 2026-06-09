import subprocess
import time
import os

def verify_integrity(binary_path, archive_path):
    """
    Checks if an ARCHIVE is valid using list-based execution.
    """
    if not os.path.exists(archive_path):
        return (False, "File missing.")
        
    ext = os.path.splitext(archive_path)[1].lower()
    if ext not in ['.7z', '.adapt', '.zpaq', '.paq', '.zst']:
        return (True, "Skip: Not an archive.")

    test_flag = "t" if ("7za" in binary_path.lower() or "zpaq" in binary_path.lower()) else "-t"
    test_cmd = [binary_path, test_flag, archive_path]
    
    try:
        result = subprocess.run(
            test_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return (result.returncode == 0, (result.stderr or result.stdout or "").strip())
    except Exception as e:
        return (False, f"Integrity Crash: {str(e)}")

def run_compressor(cmd, input_path, output_path, timeout=120):
    """
    Standardizes command execution and improves diagnostics.
    """
    start_time = time.time()
    
    if isinstance(cmd, list):
        binary_path = cmd[0]
        cmd_for_log = ' '.join([f'"{arg}"' if ' ' in arg else str(arg) for arg in cmd])
    else:
        binary_path = cmd.split()[0].replace('"', '')
        cmd_for_log = cmd

    try:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(out_dir, exist_ok=True)

        # 0. PERMISSION CHECK: Verify if we can actually write here
        test_file = os.path.join(out_dir, f".perm_test_{int(time.time())}")
        try:
            with open(test_file, "w") as f: f.write("test")
            os.remove(test_file)
        except (PermissionError, OSError):
            return {"success": False, "error": "Access Denied: Windows Security (Controlled Folder Access) is blocking this folder. Please allow python.exe in Ransomware Protection settings."}

        # 1. PRE-CHECK: Allocation Safety
        if os.path.exists(output_path):
            try:
                import stat
                if os.path.isdir(output_path):
                    import shutil
                    shutil.rmtree(output_path, ignore_errors=True)
                else:
                    os.chmod(output_path, stat.S_IWRITE)
                    os.remove(output_path)
            except: pass

        # 2. Execution (Always prefer list-based for safety)
        process = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # 3. Success Logic
        if process.returncode == 0:
            time.sleep(0.5) # Let Windows finalize IO
            if os.path.exists(output_path):
                # Verify
                success, msg = verify_integrity(binary_path, output_path)
                if not success:
                    return {"success": False, "error": f"Integrity Fail: {msg}"}

                return {
                    "success": True,
                    "time": time.time() - start_time,
                    "output_size": os.path.getsize(output_path),
                    "final_path": output_path
                }

        # 4. Failure Diagnostics
        err_out = (process.stderr or "").strip()
        std_out = (process.stdout or "").strip()
        full_err = f"{err_out}\n{std_out}".strip()
        
        print(f"\n[DEBUG] Command: {cmd_for_log}")
        print(f"[DEBUG] Engine Error: {full_err}")
        
        return {"success": False, "error": f"Engine Fail: {full_err[:100]}"}
            
    except Exception as e:
        return {"success": False, "error": f"Runner Error: {str(e)}"}
