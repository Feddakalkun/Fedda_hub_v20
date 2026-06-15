
import os
import sys
import subprocess
import shutil

# Ensure gdown is installed
try:
    import gdown
except ImportError:
    print("Installing gdown...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "gdown"])
    import gdown

# Configure paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LORA_DIR = os.path.join(ROOT_DIR, "ComfyUI", "models", "loras", "Emmy")
DRIVE_ID = "1x-gdYcmsVpT1ZFTFwPsJaHhm09eRrVll"

def download_emmy_lora():
    print(f"Target Directory: {LORA_DIR}")
    
    # Check if files already exist to save time
    safetensors_path = os.path.join(LORA_DIR, "Emmy.safetensors")
    if os.path.exists(safetensors_path):
        print("Emmy.safetensors already exists. Skipping download.")
        return

    # Ensure directory exists safely
    os.makedirs(LORA_DIR, exist_ok=True)
    
    print(f"Downloading folder from Google Drive (ID: {DRIVE_ID})...")
    try:
        # Use gdown.download_folder with output directory specified
        # Note: quiet=False shows progress bar
        files = gdown.download_folder(id=DRIVE_ID, output=LORA_DIR, quiet=False, use_cookies=False)
        
        if files:
            print("\nDownload complete!")
            print(f"Saved {len(files)} files to {LORA_DIR}")
        else:
            print("\nNo files downloaded (folder might be empty or access denied).")
            
    except Exception as e:
        print(f"\nERROR: Download failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    download_emmy_lora()
