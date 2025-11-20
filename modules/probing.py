import subprocess
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import TOOLS, ENABLE_MULTITHREADING, MAX_WORKERS, BATCH_SIZE

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
        "-title", "-tech-detect", "-status-code",
        "-no-color"
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                # Extract just the URL from the line (first item)
                return [line.strip().split(' ')[0] for line in f if line.strip()]
    except subprocess.CalledProcessError as e:
        print(f"Error running httpx: {e}")
    except FileNotFoundError:
        print("httpx not found.")
    return []

def run_httpx_batch(subdomains, output_file):
    """
    Runs httpx on a list of subdomains with batch processing.
    Uses multithreading if enabled for better performance.
    """
    if not subdomains:
        return []
    
    if not ENABLE_MULTITHREADING or len(subdomains) < BATCH_SIZE:
        # For small lists, just run directly
        temp_input = output_file.replace('.txt', '_input.txt')
        with open(temp_input, 'w') as f:
            for sub in subdomains:
                f.write(f"{sub}\n")
        
        results = run_httpx(temp_input, output_file)
        
        # Clean up temp file
        if os.path.exists(temp_input):
            os.remove(temp_input)
        
        return results
    
    # Split into batches and process in parallel
    print(f"[*] Processing {len(subdomains)} subdomains in batches of {BATCH_SIZE}...")
    
    batches = [subdomains[i:i + BATCH_SIZE] for i in range(0, len(subdomains), BATCH_SIZE)]
    all_results = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_batch = {}
        
        for idx, batch in enumerate(batches):
            batch_input = output_file.replace('.txt', f'_batch_{idx}_input.txt')
            batch_output = output_file.replace('.txt', f'_batch_{idx}.txt')
            
            # Write batch to temp file
            with open(batch_input, 'w') as f:
                for sub in batch:
                    f.write(f"{sub}\n")
            
            # Submit batch for processing
            future = executor.submit(run_httpx, batch_input, batch_output)
            future_to_batch[future] = (idx, batch_input, batch_output)
        
        # Collect results
        for future in as_completed(future_to_batch):
            idx, batch_input, batch_output = future_to_batch[future]
            try:
                result = future.result()
                print(f"[+] Batch {idx + 1}/{len(batches)} completed: {len(result)} live hosts")
                all_results.extend(result)
            except Exception as e:
                print(f"[-] Batch {idx + 1} failed: {e}")
            finally:
                # Clean up temp files
                for temp_file in [batch_input, batch_output]:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
    
    # Write all results to final output file
    with open(output_file, 'w') as f:
        for url in all_results:
            f.write(f"{url}\n")
    
    return all_results
