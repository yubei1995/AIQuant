import os
import shutil
import glob
from datetime import datetime
import urllib.request

# Configuration
# service/Unified_Service/package_utils.py -> service/Unified_Service -> service -> AIQuant
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEST_DIR = os.path.join(PROJECT_ROOT, "share_reports")
ECHARTS_URL = "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"

SERVICES = [
    {
        "name": "5min Analysis",
        "output_dir": os.path.join(PROJECT_ROOT, "service", "5min_Analyse", "output"),
        "report_pattern": "5min_analysis.html"
    },
    {
        "name": "30min Analysis",
        "output_dir": os.path.join(PROJECT_ROOT, "service", "30min_Analyse", "output"),
        "report_pattern": "30min_analysis.html"
    },
    {
        "name": "Block Analysis",
        "output_dir": os.path.join(PROJECT_ROOT, "service", "Block_Analyse", "output"),
        "report_pattern": "global_analysis_report.html"
    },
    {
        "name": "Daily Monitor",
        "output_dir": os.path.join(PROJECT_ROOT, "service", "Daily_Monitor", "output"),
        "report_pattern": "daily_report.html"
    },
    {
        "name": "LHB Analysis",
        "output_dir": os.path.join(PROJECT_ROOT, "service", "LHB_Analyse", "output"),
        "report_pattern": "lhb_analysis_report.html"
    }
]

def find_latest_file(directory, pattern):
    search_path = os.path.join(directory, pattern)
    files = glob.glob(search_path)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def download_assets():
    print("Downloading assets...")
    echarts_path = os.path.join(DEST_DIR, "echarts.min.js")
    try:
        urllib.request.urlretrieve(ECHARTS_URL, echarts_path)
        print(f"Downloaded: echarts.min.js")
    except Exception as e:
        print(f"Error downloading assets: {e}")

def generate_index_html(files):
    links_html = ""
    for file in files:
        links_html += f'''
        <div class="card">
            <h3>{file['name']}</h3>
            <p>Report: {file['filename']}</p>
            <a href="{file['filename']}" target="content-frame" class="btn">View Report</a>
        </div>
        '''
        
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIQuant Analysis Reports</title>
    <style>
        body {{ margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5; height: 100vh; display: flex; flex-direction: column; }}
        header {{ background-color: #2c3e50; color: white; padding: 1rem; text-align: center; }}
        .container {{ display: flex; flex: 1; overflow: hidden; }}
        .sidebar {{ width: 250px; background-color: #fff; border-right: 1px solid #ddd; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }}
        .main {{ flex: 1; background-color: #ecf0f1; position: relative; }}
        iframe {{ width: 100%; height: 100%; border: none; }}
        
        .card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .card h3 {{ margin: 0 0 10px 0; font-size: 16px; color: #2c3e50; }}
        .card p {{ margin: 0 0 15px 0; font-size: 12px; color: #7f8c8d; word-break: break-all; }}
        .btn {{ display: block; text-align: center; background-color: #3498db; color: white; text-decoration: none; padding: 8px; border-radius: 4px; font-size: 14px; transition: background 0.3s; }}
        .btn:hover {{ background-color: #2980b9; }}
    </style>
</head>
<body>
    <header>
        <h1>AIQuant Analysis Reports</h1>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </header>
    <div class="container">
        <div class="sidebar">
            {links_html}
        </div>
        <div class="main">
            <iframe name="content-frame" src="{files[0]['filename'] if files else ''}"></iframe>
        </div>
    </div>
</body>
</html>
    """
    
    with open(os.path.join(DEST_DIR, "index.html"), 'w', encoding='utf-8') as f:
        f.write(html_content)

def package_all_reports():
    print(f"Packaging reports to {DEST_DIR}...")
    
    # Create or clean destination directory
    if os.path.exists(DEST_DIR):
        try:
            shutil.rmtree(DEST_DIR)
        except Exception as e:
            print(f"Warning: Could not delete {DEST_DIR}: {e}")
            
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)
    
    download_assets()
    
    copied_files = []
    
    for service in SERVICES:
        if not os.path.exists(service['output_dir']):
             print(f"Warning: Output directory not found: {service['output_dir']}")
             continue

        latest_file = find_latest_file(service['output_dir'], service['report_pattern'])
        if latest_file:
            filename = os.path.basename(latest_file)
            dest_path = os.path.join(DEST_DIR, filename)
            
            # Read and modify content for offline use
            try:
                with open(latest_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Ensure we use CDN for echarts to avoid issues with missing local files or zip blocking
                # If the content already uses ECHARTS_URL, this does nothing
                # If it used local references, we replace them
                content = content.replace("echarts.min.js", ECHARTS_URL)
                # Fix double replacement if any (e.g. if filename was complex path ending in echarts.min.js)
                # Just to be safe, if we accidentally created "https://.../https://...", fix it? 
                # Actually, simpler logic:
                # 1. First remove known local relative paths
                content = content.replace("../../../share_reports/echarts.min.js", ECHARTS_URL)
                content = content.replace("./echarts.min.js", ECHARTS_URL)
                
                # 2. If we just have bare "echarts.min.js" (from previous replace or origin), replace it
                # Be careful not to replace the end of the CDN URL itself!
                if f'src="{ECHARTS_URL}"' not in content and f"src='{ECHARTS_URL}'" not in content:
                     content = content.replace('src="echarts.min.js"', f'src="{ECHARTS_URL}"')
                     content = content.replace("src='echarts.min.js'", f"src='{ECHARTS_URL}'")
                
                with open(dest_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                print(f"Processed and Copied: {filename}")
                copied_files.append({
                    "name": service["name"],
                    "filename": filename,
                    "path": dest_path
                })
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                # Fallback to simple copy if processing fails
                shutil.copy2(latest_file, dest_path)
        else:
            print(f"Warning: No report found for {service['name']}")
            
    # Generate index.html for the friend
    generate_index_html(copied_files)
    
    # Create Zip archive
    zip_name = os.path.join(PROJECT_ROOT, f"AIQuant_Reports_{datetime.now().strftime('%Y%m%d')}")
    shutil.make_archive(zip_name, 'zip', DEST_DIR)
    
    print(f"Packaging complete.")
    print(f"Folder: {DEST_DIR}")
    print(f"Zip File: {zip_name}.zip")
    
    # Return the path to index.html for auto-opening
    return os.path.join(DEST_DIR, "index.html")

if __name__ == "__main__":
    package_all_reports()
