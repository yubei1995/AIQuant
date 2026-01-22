import os
import sys
import subprocess
import time
from package_utils import package_all_reports

# Configuration
# service/Unified_Service/run_full_cycle.py -> service/Unified_Service -> service -> AIQuant
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Services to run in order
# Each entry: { "name": Display Name, "script": Relative path to script, "cwd": Relative path to working dir }
SERVICE_SEQUENCE = [
    {
        "name": "Block Analysis",
        "script": "service/Block_Analyse/block_analysis_service.py",
        "cwd": "service/Block_Analyse"
    },
    {
        "name": "LHB Analysis",
        "script": "service/LHB_Analyse/lhb_detailed_analyzer.py",
        "cwd": "service/LHB_Analyse"
    },
    {
        "name": "Daily Monitor",
        "script": "service/Daily_Monitor/run_monitor.py",
        "cwd": "service/Daily_Monitor"
    },
    {
        "name": "30min Analysis",
        "script": "service/30min_Analyse/analyze_30min.py",
        "cwd": "service/30min_Analyse"
    },
    {
        "name": "5min Analysis",
        "script": "service/5min_Analyse/analyze_5min.py",
        "cwd": "service/5min_Analyse"
    }
]

def run_service(service_info):
    name = service_info["name"]
    script_rel_path = service_info["script"]
    cwd_rel_path = service_info["cwd"]
    
    script_path = os.path.join(PROJECT_ROOT, script_rel_path)
    cwd_path = os.path.join(PROJECT_ROOT, cwd_rel_path)
    
    print(f"\n{'='*60}")
    print(f"Starting Service: {name}")
    print(f"Script: {script_path}")
    print(f"Working Dir: {cwd_path}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Use simple subprocess call
        # Using sys.executable to ensure we use the current python interpreter
        
        # We need to make sure pythonpath includes the project root so imports like 'src.xxx' work
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{PROJECT_ROOT}{os.pathsep}{existing_pythonpath}"
        
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=cwd_path,
            env=env, # Pass the modified environment
            check=True
        )
        
        duration = time.time() - start_time
        print(f"\n[SUCCESS] {name} completed in {duration:.2f} seconds.")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] {name} failed with exit code {e.returncode}.")
        return False
    except Exception as e:
        print(f"\n[ERROR] {name} failed with exception: {e}")
        return False

def main():
    print(f"Starting Full AIQuant Workflow at {time.ctime()}")
    print(f"Project Root: {PROJECT_ROOT}")
    
    failed_services = []
    
    for service in SERVICE_SEQUENCE:
        success = run_service(service)
        if not success:
            failed_services.append(service["name"])
            # Decide whether to stop or continue. 
            # Usually if Daily Monitor fails (no data), others might fail too, 
            # but we can try to continue for partial results.
            print("Continuing to next service...")

    print(f"\n{'='*60}")
    print("All Services Execution Cycle Completed.")
    
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
