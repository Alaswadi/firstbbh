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

def run_discovery(domain, output_dir, tools=None):
    """
    Runs discovery tools and aggregates results.
    Uses multithreading if enabled in config.
    
    Args:
        domain: Target domain
        output_dir: Directory to save output files
        tools: List of tools to run (e.g., ['subfinder', 'amass']). If None, runs all.
    """
    if ENABLE_MULTITHREADING:
        return run_discovery_parallel(domain, output_dir, tools)
    else:
        return run_discovery_sequential(domain, output_dir, tools)

def run_discovery_sequential(domain, output_dir, tools=None):
    """Sequential execution of discovery tools."""
    if tools is None:
        tools = ['subfinder', 'amass']
    
    print(f"[*] Starting sequential discovery for {domain}...")
    print(f"[*] Selected tools: {', '.join(tools)}")
    
    all_subs = []
    
    # Run Subfinder if selected
    if 'subfinder' in tools:
        subfinder_out = os.path.join(output_dir, f"{domain}_subfinder.txt")
        print("[*] Running subfinder...")
        subs = run_subfinder(domain, subfinder_out)
        all_subs.extend(subs)
    
    # Run Amass if selected
    if 'amass' in tools:
        amass_out = os.path.join(output_dir, f"{domain}_amass.txt")
        print("[*] Running amass...")
        subs = run_amass(domain, amass_out)
        all_subs.extend(subs)
    
    return list(set(all_subs))

def run_discovery_parallel(domain, output_dir, tools=None):
    """Parallel execution of discovery tools using ThreadPoolExecutor."""
    if tools is None:
        tools = ['subfinder', 'amass']
    
    print(f"[*] Starting parallel discovery for {domain}...")
    print(f"[*] Selected tools: {', '.join(tools)}")
    
    # Build list of tools to run based on selection
    available_tools = {
        'subfinder': (run_subfinder, os.path.join(output_dir, f"{domain}_subfinder.txt")),
        'amass': (run_amass, os.path.join(output_dir, f"{domain}_amass.txt"))
    }
    
    tools_to_run = []
    for tool_name in tools:
        if tool_name in available_tools:
            tool_func, output_file = available_tools[tool_name]
            tools_to_run.append((tool_name, tool_func, output_file))
    
    if not tools_to_run:
        print("[!] No valid discovery tools selected")
        return []
    
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
