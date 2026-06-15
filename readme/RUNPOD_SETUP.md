# RunPod Deployment Setup

## Quick Start

1. Get your RunPod API key: https://www.runpod.io/console/user/settings
2. Run the script to create a pre-configured template:

### Windows
```bash
set RUNPOD_API_KEY=your_key_here
create-runpod-template.bat
```

### Linux/Mac
```bash
chmod +x create-runpod-template.sh
RUNPOD_API_KEY=your_key_here ./create-runpod-template.sh
```

3. Script will output a shareable URL like:
   ```
   https://runpod.io/console/deploy?template=abc123xyz
   ```

4. Share this URL with your users for 1-click deployment!

## Template Configuration

The script creates a template with:
- **Container Image**: `feddahannah/fedda-studio:latest`
- **Container Disk**: 100 GB
- **Volume Disk**: 200 GB (persistent models/outputs)
- **Volume Path**: `/workspace`
- **HTTP Ports**: 3000 (FEDDA UI), 8199 (ComfyUI)
- **Minimum GPU**: RTX 3090 (24GB VRAM)

## Manual Setup (Alternative)

If you prefer to create the template manually in RunPod UI:

1. Go to: https://www.runpod.io/console/templates
2. Click "New Template"
3. Configure:
   - Name: `FEDDA AI Studio`
   - Container Image: `feddahannah/fedda-studio:latest`
   - Container Disk: `100 GB`
   - Volume Disk: `200 GB`
   - Volume Mount Path: `/workspace`
   - Expose HTTP Ports: `3000, 8199`
4. Save and get shareable template URL

## For End Users

When users deploy from your template:
1. Click the template URL
2. Select GPU (RTX 3090 or better recommended)
3. Click "Deploy"
4. Wait ~2 minutes for UI to be available
5. Access FEDDA UI on port 3000, ComfyUI on port 8199

Models download automatically in the background (~15 min for full setup).
