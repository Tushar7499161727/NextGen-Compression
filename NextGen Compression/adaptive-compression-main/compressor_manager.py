import os
import sys

class CompressorManager:
    def __init__(self):
        # Handle the "Frozen" path (for PyInstaller) vs "Script" path
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.bin = os.path.join(base_path, "bin")

        # --- Match EXACT binary names ---
        self.bins = {
            "7zip": os.path.join(self.bin, "7za.exe"),
            "zstd": os.path.join(self.bin, "zstd.exe"),
            "paq":  os.path.join(self.bin, "zpaq.exe"),
            "webp": os.path.join(self.bin, "cwebp.exe"),
            "ffmpeg": os.path.join(self.bin, "ffmpeg.exe"),
            "tar":  "tar" # Windows built-in
        }

    def _prepare_paths(self, *paths):
        """Standardize all paths for Windows engines."""
        return [os.path.normpath(os.path.abspath(p)) for p in paths]

    def get_command(self, tool, input_p, output_p, level="fast"):
        """Generates the command to COMPRESS a file."""
        exe_path = self.bins.get(tool)
        if tool != "tar" and (not exe_path or not os.path.exists(exe_path)):
            # Fallback to 7zip if specialized tool missing
            tool = "7zip"
            exe_path = self.bins["7zip"]

        input_p, output_p = self._prepare_paths(input_p, output_p)

        if tool == "7zip":
            mx = "-mx1" if level == "fast" else "-mx9"
            return [exe_path, "a", mx, "-ssw", "-y", output_p, input_p]
            
        elif tool == "zstd":
            z_level = "-3" if level == "fast" else "-19"
            return [exe_path, z_level, "-f", input_p, "-o", output_p]
            
        elif tool == "paq":
            p_method = "-m1" if level == "fast" else "-m5"
            return [exe_path, "add", output_p, input_p, p_method]

        elif tool == "webp":
            # cwebp [options] input_file -o output_file.webp
            quality = "50" if level == "fast" else "80"
            return [exe_path, "-q", quality, input_p, "-o", output_p]

        elif tool == "ffmpeg":
            # ffmpeg -i input -vcodec libx265 -crf 28 output.mp4
            crf = "28" if level == "fast" else "23"
            return [exe_path, "-i", input_p, "-vcodec", "libx265", "-crf", crf, "-preset", "faster", "-y", output_p]

        elif tool == "tar":
            # tar -cf archive.tar file_or_dir
            return [exe_path, "-cf", output_p, input_p]
            
        return None

    def get_decompress_command(self, source, dest, ext):
        """Generates the command to DECOMPRESS a file."""
        source, dest = self._prepare_paths(source, dest)
        out_dir = os.path.dirname(dest)

        if ext in ["7z", "adapt"]:
            return [self.bins["7zip"], "x", source, f"-o{out_dir}", "-aoa", "-spe", "-y"]
            
        elif ext == "zst":
            return [self.bins["zstd"], "-d", source, "-o", dest, "-f"]
            
        elif ext in ["paq", "zpaq"]:
            return [self.bins["paq"], "x", source, "-to", out_dir, "-force"]

        elif ext == "webp":
            dwebp = os.path.join(self.bin, "dwebp.exe")
            return [dwebp, source, "-o", dest]

        elif ext == "mp4":
            # FFmpeg is its own decompressor (not strictly needed, but for completeness)
            return [self.bins["ffmpeg"], "-i", source, "-y", dest]

        elif ext == "tar":
            return ["tar", "-xf", source, "-C", out_dir]
            
        return None

    def get_test_command(self, tool_path, archive_path):
        """Generates the command to VERIFY an archive."""
        archive_path = os.path.normpath(os.path.abspath(archive_path))
        tool_name = os.path.basename(tool_path).lower()

        if "zstd" in tool_name:
            return [tool_path, "-t", archive_path]
        elif "7za" in tool_name or "paq" in tool_name:
            return [tool_path, "t", archive_path]
        return None