#!/bin/bash
# Install ComfyUI custom nodes from config/nodes.json
# Modes:
#   --core : install minimal startup set
#   --full : install all nodes (default)
set -e

MODE="full"
if [ "$1" = "--core" ]; then
    MODE="core"
elif [ "$1" = "--full" ]; then
    MODE="full"
fi

NODES_DIR="/workspace/custom_nodes"
CONFIG="/app/config/nodes.json"

mkdir -p "$NODES_DIR"

echo "========================================="
echo "  Installing Custom Nodes ($MODE mode)"
echo "========================================="

python3 << 'PYEOF'
import json, subprocess, os, sys

mode = os.environ.get("NODE_MODE", "full")
install_gguf = os.environ.get("INSTALL_GGUF", "0") == "1"
config_path = "/app/config/nodes.json"
nodes_dir = "/workspace/custom_nodes"

# Core set: enough to bring UI/workflows up quickly.
CORE_FOLDERS = {
    "ComfyUI-Manager",
    "rgthree-comfy",
    "ComfyUI-Studio-nodes",
    "ComfyUI-Impact-Pack",
    "ComfyUI_UltimateSDUpscale",
    "ComfyUI_IPAdapter_plus",
    "ComfyUI_InstantID",
    "ComfyUI-Lotus",
    "comfyui_controlnet_aux",
    "ComfyUI-Impact-Subpack",
    "ComfyUI-AutoCropFaces",
    "ComfyUI-Inpaint-CropAndStitch",
    "comfyui-inpaint-nodes",
    "ComfyUI_LayerStyle",
    "ComfyUI-Styles_CSV_Loader",
    "comfyui-qwenmultiangle",
    "ComfyUI-VideoHelperSuite",
    "ComfyUI-WanVideoWrapper",
    "ComfyUI-WanAnimatePreprocess",
    "ComfyUI-LTXVideo",
    "ComfyUI-GGUF",
    "ComfyMath",
    "RES4LYF",
    "comfy-image-saver",
    "ComfyUI-IF_AI_tools",
    "ComfyUI-Custom-Scripts",
    "ComfyUI_essentials",
    "was-node-suite-comfyui",
    "ComfyUI-KJNodes",
}

with open(config_path, encoding="utf-8") as f:
    nodes = json.load(f)

candidates = [n for n in nodes if not n.get("local")]
if not install_gguf:
    candidates = [n for n in candidates if n.get("folder") != "ComfyUI-GGUF"]
if mode == "core":
    candidates = [n for n in candidates if n.get("folder") in CORE_FOLDERS]

total = len(candidates)
processed = 0

for node in candidates:
    processed += 1
    name = node["name"]
    url = node["url"]
    folder = node["folder"]
    dest = os.path.join(nodes_dir, folder)

    if os.path.exists(dest):
        print(f"  [{processed}/{total}] {name} - already installed")
        continue

    print(f"  [{processed}/{total}] Installing {name}...")
    sys.stdout.flush()
    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--progress", url, dest],
    )

    if result.returncode != 0:
        print(f"    WARNING: Failed to clone {name}")
        continue

    gitmodules_path = os.path.join(dest, ".gitmodules")
    if os.path.exists(gitmodules_path):
        print(f"    Initializing submodules for {name}...")
        sys.stdout.flush()
        subprocess.run(["git", "-C", dest, "submodule", "update", "--init", "--recursive"])

    req_path = os.path.join(dest, "requirements.txt")
    if os.path.exists(req_path):
        print(f"    Installing requirements for {name}...")
        sys.stdout.flush()
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                req_path,
                "--no-warn-script-location",
                "--progress-bar", "on",
            ],
        )

print(f"\nDone: {processed} nodes processed in {mode} mode.")
PYEOF

# Symlink custom_nodes into ComfyUI
rm -rf /app/ComfyUI/custom_nodes
ln -sf "$NODES_DIR" /app/ComfyUI/custom_nodes

echo "[NODES] Custom nodes symlinked to ComfyUI."
