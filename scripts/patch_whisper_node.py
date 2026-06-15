"""
Quick patch script to fix ComfyUI-Whisper compatibility with newer ComfyUI versions.
This script updates the deprecated API call in the Whisper node.
"""

import os
from pathlib import Path

def apply_whisper_patch():
    # Find ComfyUI-Whisper directory
    comfyui_dir = Path(__file__).parent.parent / "ComfyUI"
    whisper_file = comfyui_dir / "custom_nodes" / "ComfyUI-Whisper" / "apply_whisper.py"
    
    if not whisper_file.exists():
        print("⚠️ ComfyUI-Whisper not found, skipping patch...")
        return
    
    # Read current content
    with open(whisper_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Apply patch
    if 'mm.load_model_gpu(patcher)' in content:
        print("🔧 Patching ComfyUI-Whisper for newer ComfyUI API...")
        content = content.replace(
            'mm.load_model_gpu(patcher)',
            'mm.load_models_gpu([patcher])'
        )
        
        # Write back
        with open(whisper_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ ComfyUI-Whisper patched successfully!")
    else:
        print("✅ ComfyUI-Whisper already up to date.")

if __name__ == "__main__":
    apply_whisper_patch()
