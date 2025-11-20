import subprocess
import os
from config import TOOLS

def run_naabu(host_list_file, output_file):
    """Runs naabu to find open ports."""
    cmd = [
        TOOLS["naabu"],
        "-list", host_list_file,
        "-o", output_file,
        "-silent"
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                return [line.strip() for line in f if line.strip()]
    except subprocess.CalledProcessError as e:
        print(f"Error running naabu: {e}")
    except FileNotFoundError:
        print("Naabu not found.")
    return []

def run_httpx(host_list_file, output_file):
    """Runs httpx to find live web servers."""
    cmd = [
        TOOLS["httpx"],
        "-l", host_list_file,
        "-o", output_file,
        "-silent",
        "-title", "-tech-detect", "-status-code"
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                return [line.strip() for line in f if line.strip()]
    except subprocess.CalledProcessError as e:
        print(f"Error running httpx: {e}")
    except FileNotFoundError:
        print("httpx not found.")
    return []
