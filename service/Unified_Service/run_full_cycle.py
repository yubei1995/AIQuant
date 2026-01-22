import os
import sys
import subprocess
import time
import concurrent.futures
from package_utils import package_all_reports

# Configuration
# service/Unified_Service/run_full_cycle.py -> service/Unified_Service -> service -> AIQuant
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Defined Services
SERVICES = {
    "Block": {
        "name": "Block Analysis",
        "script": "service/Block_Analyse/block_analysis_service.py",
        "cwd": "service/Block_Analyse"
    },
    "LHB": {
        "name": "LHB Analysis",
        "script": "service/LHB_Analyse/lhb_detailed_analyzer.py",
        "cwd": "service/LHB_Analyse"
    },
    "Daily": {
        "name": "Daily Monitor",
        "script": "service/Daily_Monitor/run_monitor.py",
        "cwd": "service/Daily_Monitor"
    },
    "30min": {
        "name": "30min Analysis",
        "script": "service/30min_Analyse/analyze_30min.py",
        "cwd": "service/30min_Analyse"
    },
    "5min": {
        "name": "5min Analysis",
        "script": "service/5min_Analyse/analyze_5min.py",
        "cwd": "service/5min_Analyse"
    }
}

def run_service(service_info):
    name = service_info["name"]
    script_rel_path = service_info["script"]
    cwd_rel_path = service_info["cwd"]
    
    script_path = os.path.join(PROJECT_ROOT, script_rel_path)
    cwd_path = os.path.join(PROJECT_ROOT, cwd_rel_path)
    
    print(f"\n[START] {name}")
    
    start_time = time.time()
    
    try:
        # Use simple subprocess call
        # Using sys.executable to ensure we use the current python interpreter
        
        # We need to make sure pythonpath includes the project root so imports like 'src.xxx' work
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{PROJECT_ROOT}{os.pathsep}{existing_pythonpath}"
        
        # Capture output to avoid interleaved printing in parallel exec
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=cwd_path,
            env=env, # Pass the modified environment
            capture_output=False, # Let it stream to console for now, though it might be messy
            check=True
        )
        
        duration = time.time() - start_time
        print(f"\n[SUCCESS] {name} completed in {duration:.2f} seconds.")
        return True, name
    
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] {name} failed with exit code {e.returncode}.")
        return False, name
    except Exception as e:
        print(f"\n[ERROR] {name} failed with exception: {e}")
        return False, name

def main():
    print(f"Starting Full AIQuant Workflow at {time.ctime()}")
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Mode: Parallel Execution Optimized")
    
    failed_services = []
    start_total = time.time()

    # Strategy:
    # 1. Start [Block, LHB, 30min, 5min] in parallel.
    # 2. Wait for LHB to finish.
    # 3. Start Daily Monitor (Depends on LHB).
    # 4. Wait for all.

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Submit independent tasks
        future_block = executor.submit(run_service, SERVICES["Block"])
        future_lhb = executor.submit(run_service, SERVICES["LHB"])
        future_30min = executor.submit(run_service, SERVICES["30min"])
        future_5min = executor.submit(run_service, SERVICES["5min"])
        
        independent_futures = [future_block, future_lhb, future_30min, future_5min]
        
        # Wait specifically for BOTH LHB and Block to finish before starting Daily Monitor
        # Daily Monitor needs:
        # 1. LHB data (from LHB Analysis)
        # 2. Block Ranking (from Block Analysis) for sorting
        print("\n[WAIT] Waiting for LHB and Block Analysis to complete before starting Daily Monitor...")
        
        concurrent.futures.wait([future_lhb, future_block])
        
        # Check results
        try:
            success_lhb, _ = future_lhb.result()
        except: 
            success_lhb = False
            
        try:
            success_block, _ = future_block.result()
        except:
            success_block = False
        
        if success_lhb and success_block:
            print("\n[INFO] Dependencies met (LHB & Block). Starting Daily Monitor...")
        else:
            print(f"\n[WARN] Dependencies missing (LHB: {success_lhb}, Block: {success_block}). Daily Monitor might have incomplete data.")
            
        future_daily = executor.submit(run_service, SERVICES["Daily"])
        independent_futures.append(future_daily)

        # Wait for everything else
        for future in concurrent.futures.as_completed(independent_futures):
            success, name = future.result()
            if not success:
                failed_services.append(name)

    print(f"\n{'='*60}")
    print(f"All Services Execution Cycle Completed in {time.time() - start_total:.2f}s.")
    
    if failed_services:
        print(f"Warning: The following services failed: {', '.join(failed_services)}")
    
    print(f"{'='*60}")
    
    # Package Results
    print("\nStarting Report Packaging...")
    try:
        index_path = package_all_reports()
        print(f"\nWorkflow Finished Successfully.")
        print(f"Consolidated Report Available at: {index_path}")
        
        # Open the report on Windows
        if os.name == 'nt':
            os.startfile(index_path)
            
    except Exception as e:
        print(f"Error during packaging: {e}")

if __name__ == "__main__":
    main()
