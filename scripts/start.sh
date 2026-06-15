#!/bin/bash
set -e

echo "========================================="
echo "  FEDDA AI Studio - Docker Startup"
echo "========================================="
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo 'none detected')"
echo ""

# --- 1. Create network volume directory structure ---
MODELS_DIR="/workspace/models/comfyui"
mkdir -p "$MODELS_DIR"/{checkpoints,diffusion_models,clip,text_encoders,vae,loras,sams,ultralytics/bbox,model_patches}
mkdir -p /workspace/output
mkdir -p /workspace/input

# --- 2. Symlink ComfyUI model directories to network volume ---
echo "[SETUP] Symlinking model directories to /workspace..."
for dir in checkpoints diffusion_models clip text_encoders vae loras sams ultralytics model_patches; do
    rm -rf "/app/ComfyUI/models/$dir"
    ln -sf "$MODELS_DIR/$dir" "/app/ComfyUI/models/$dir"
done

# Symlink output and input directories
rm -rf /app/ComfyUI/output
ln -sf /workspace/output /app/ComfyUI/output

rm -rf /app/ComfyUI/input
ln -sf /workspace/input /app/ComfyUI/input

# --- 3. Copy pre-installed critical nodes to workspace (if missing) ---
mkdir -p /workspace/custom_nodes
echo "[SETUP] Ensuring critical nodes are present..."

for node in ComfyUI-Impact-Pack comfyui-impact-subpack rgthree-comfy ComfyUI-IF_AI_tools; do
    if [ ! -d "/workspace/custom_nodes/$node" ]; then
        echo "[SETUP] Copying $node from base image..."
        cp -r "/app/custom_nodes_base/$node" "/workspace/custom_nodes/"
    fi
done

# Symlink to ComfyUI
rm -rf /app/ComfyUI/custom_nodes
ln -sf /workspace/custom_nodes /app/ComfyUI/custom_nodes

# --- 4. Install core nodes synchronously, then remaining in background ---
CORE_MARKER="/workspace/.nodes_core_installed"
FULL_MARKER="/workspace/.nodes_full_installed"

if [ ! -f "$CORE_MARKER" ]; then
    echo "[NODES] Installing core custom nodes (required for startup)..."
    NODE_MODE=core /app/scripts/install-nodes.sh --core
    touch "$CORE_MARKER"
    echo "[NODES] Core nodes installed."
else
    echo "[NODES] Core nodes already installed."
fi

if [ ! -f "$FULL_MARKER" ]; then
    echo "[NODES] Installing additional custom nodes in background..."
    (
        NODE_MODE=full /app/scripts/install-nodes.sh --full && touch "$FULL_MARKER"
        echo "[NODES] Background node installation complete."
    ) 2>&1 | tee /var/log/node_install_bg.log &
else
    echo "[NODES] All nodes already installed."
fi

# --- 5. Copy bundled assets ---
cp -n /app/assets/styles.csv /app/ComfyUI/styles.csv 2>/dev/null || true

if [ -d "/app/assets/loras" ]; then
    echo "[SETUP] Copying bundled LoRAs..."
    cp -rn /app/assets/loras/* "$MODELS_DIR/loras/" 2>/dev/null || true
fi

# --- 6. Configure ComfyUI-Manager ---
MANAGER_DIR="/app/ComfyUI/custom_nodes/ComfyUI-Manager"
if [ -d "$MANAGER_DIR" ]; then
    mkdir -p "$MANAGER_DIR/user"
    cat > "$MANAGER_DIR/user/config.ini" << 'EOF'
[default]
security_level = weak
network_mode = public
EOF
fi

# --- 7. Model downloads (on-demand via UI) ---
# Models are now downloaded on-demand through the UI
# Essential models (CLIP, VAE) can be pre-downloaded if needed
echo ""
echo "[MODELS] Models available for download via UI"

# --- 8. Launch all services via supervisord ---
echo ""
echo "========================================="
echo "  Starting services..."
echo "  UI will be available on port 3000"
echo "========================================="
exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
