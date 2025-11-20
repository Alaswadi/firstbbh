import subprocess
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import TOOLS, ENABLE_MULTITHREADING, MAX_WORKERS

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

def run_amass(domain, output_file):
    """Runs amass against the target domain."""
    cmd = [
        TOOLS["amass"],
        "enum",
        "-d", domain,
        "-o", output_file,
        "-silent"
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                return [line.strip() for line in f if line.strip()]
    except subprocess.TimeoutExpired:
        print(f"Amass timed out after 10 minutes")
    except subprocess.CalledProcessError as e:
        print(f"Error running amass: {e}")
    except FileNotFoundError:
        print("Amass not found. Please ensure it is installed and in your PATH.")
    return []

def run_discovery(domain, output_dir):
    """
    Runs all discovery tools and aggregates results.
    Uses multithreading if enabled in config.
    """
    if ENABLE_MULTITHREADING:
        return run_discovery_parallel(domain, output_dir)
    else:
        return run_discovery_sequential(domain, output_dir)

def run_discovery_sequential(domain, output_dir):
    """Sequential execution of discovery tools."""
    subfinder_out = os.path.join(output_dir, f"{domain}_subfinder.txt")
    amass_out = os.path.join(output_dir, f"{domain}_amass.txt")
    
    print(f"[*] Starting sequential discovery for {domain}...")
    
    all_subs = []
    
    # Run Subfinder
    print("[*] Running subfinder...")
    subs = run_subfinder(domain, subfinder_out)
    all_subs.extend(subs)
    
    # Run Amass
    print("[*] Running amass...")
    subs = run_amass(domain, amass_out)
    all_subs.extend(subs)
    
    return list(set(all_subs))

def run_discovery_parallel(domain, output_dir):
    """Parallel execution of discovery tools using ThreadPoolExecutor."""
    print(f"[*] Starting parallel discovery for {domain}...")
    
    tools_to_run = [
        ("subfinder", run_subfinder, os.path.join(output_dir, f"{domain}_subfinder.txt")),
        ("amass", run_amass, os.path.join(output_dir, f"{domain}_amass.txt"))
    ]
    
    all_subs = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tool executions
        future_to_tool = {
            executor.submit(tool_func, domain, output_file): tool_name
            for tool_name, tool_func, output_file in tools_to_run
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_tool):
            tool_name = future_to_tool[future]
            try:
                result = future.result()
                print(f"[+] {tool_name} found {len(result)} subdomains")
                all_subs.extend(result)
            except Exception as e:
                print(f"[-] {tool_name} failed with error: {e}")
    
    # Deduplicate and return
    unique_subs = list(set(all_subs))
    print(f"[+] Total unique subdomains found: {len(unique_subs)}")
    return unique_subs
