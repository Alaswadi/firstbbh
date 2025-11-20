import subprocess
import os
from config import TOOLS

def run_subfinder(domain, output_file):
    """Runs subfinder against the target domain."""
    cmd = [
        TOOLS["subfinder"],
        "-d", domain,
        "-o", output_file,
        "-silent"
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                return [line.strip() for line in f if line.strip()]
    except subprocess.CalledProcessError as e:
        print(f"Error running subfinder: {e}")
    except FileNotFoundError:
        print("Subfinder not found. Please ensure it is installed and in your PATH.")
    return []

def run_discovery(domain, output_dir):
    """
    Runs all discovery tools and aggregates results.
    """
    subfinder_out = os.path.join(output_dir, f"{domain}_subfinder.txt")
    
    print(f"[*] Starting discovery for {domain}...")
    
    # Run Passive Discovery
    subs = run_subfinder(domain, subfinder_out)
    
    # Future: Add Amass, Puredns here
    
    return list(set(subs))
