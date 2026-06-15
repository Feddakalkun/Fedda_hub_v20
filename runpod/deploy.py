#!/usr/bin/env python3
"""
FEDDA AI Studio — RunPod One-Click Deployer

Usage:
    python deploy.py                    # Interactive menu
    python deploy.py --gpu "RTX 4090"   # Direct GPU selection
    python deploy.py --list             # List available GPUs
    python deploy.py --stop <pod_id>    # Stop a running pod
    python deploy.py --terminate <id>   # Terminate (delete) a pod

Requires: RUNPOD_API_KEY environment variable (or prompts for it)
"""

import os
import sys
import json
import argparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# ─── Configuration ───────────────────────────────────────────────────
DOCKER_IMAGE = "ghcr.io/feddakalkun/fedda-runpod:runpod-dev"
POD_NAME = "FEDDA AI Studio"
VOLUME_GB = 75          # Network volume for models + outputs
CONTAINER_DISK_GB = 30  # Container disk for OS + packages
MIN_VCPU = 4
MIN_MEMORY_GB = 16
PORTS = "3000/http,8199/http,8888/http,22/tcp"
VOLUME_MOUNT = "/workspace"

# Minimum VRAM for FEDDA (LTX-2 needs ~20GB, LTX-2.3 needs ~40GB)
MIN_VRAM_GB = 24

API_URL = "https://api.runpod.io/graphql"


# ─── Helpers ─────────────────────────────────────────────────────────

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    print()
    print("  ╔═══════════════════════════════════════════════════╗")
    print("  ║          FEDDA AI Studio — RunPod Manager         ║")
    print("  ╚═══════════════════════════════════════════════════╝")
    print()


def get_api_key():
    """Get RunPod API key from env or prompt."""
    key = os.environ.get("RUNPOD_API_KEY", "").strip()
    if not key:
        print("  No RUNPOD_API_KEY found in environment.")
        print("  Get yours at: https://www.runpod.io/console/user/settings\n")
        key = input("  Enter your RunPod API key: ").strip()
        if not key:
            print("  ERROR: API key is required.")
            sys.exit(1)
    return key


def graphql(api_key: str, query: str, variables: dict = None):
    """Execute a GraphQL query against RunPod API."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    req = Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "FEDDA-Deploy/1.0",
        },
    )

    try:
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        print(f"\n  API Error {e.code}: {body}")
        return None
    except URLError as e:
        print(f"\n  Connection error: {e.reason}")
        return None

    if "errors" in result:
        for err in result["errors"]:
            print(f"\n  API Error: {err.get('message', err)}")
        return None

    return result.get("data", {})


# ─── GPU Queries ─────────────────────────────────────────────────────

def fetch_gpus_with_stock(api_key: str) -> list:
    """Fetch all GPU types with availability info from RunPod."""
    query = """
    query GpuTypes {
        gpuTypes {
            id
            displayName
            memoryInGb
            communityPrice
            securePrice
            communitySpotPrice
            lowestPrice(input: { gpuCount: 1 }) {
                minimumBidPrice
                uninterruptablePrice
            }
        }
    }
    """
    data = graphql(api_key, query)
    if not data:
        return []
    return data.get("gpuTypes", [])


def check_stock(api_key: str, gpu_id: str) -> dict:
    """Check real-time stock for a specific GPU type."""
    query = """
    query GpuTypes($id: String!) {
        gpuTypes(input: { id: $id }) {
            id
            displayName
            memoryInGb
            communityCloud
            secureCloud
            lowestPrice(input: { gpuCount: 1 }) {
                minimumBidPrice
                uninterruptablePrice
            }
        }
    }
    """
    data = graphql(api_key, query, {"id": gpu_id})
    if not data:
        return {}
    types = data.get("gpuTypes", [])
    return types[0] if types else {}


def get_stock_label(gpu_detail: dict) -> str:
    """Get a human-readable stock label from GPU detail."""
    # communityCloud and secureCloud are booleans indicating availability
    community = gpu_detail.get("communityCloud", False)
    secure = gpu_detail.get("secureCloud", False)

    if community and secure:
        return "IN STOCK"
    elif community:
        return "COMMUNITY"
    elif secure:
        return "SECURE"
    else:
        return "SOLD OUT"


# ─── Core Operations ────────────────────────────────────────────────

def fetch_pods(api_key: str) -> list:
    """Fetch current pods from RunPod."""
    query = """
    query {
        myself {
            pods {
                id
                name
                desiredStatus
                costPerHr
                runtime {
                    uptimeInSeconds
                    ports {
                        ip
                        isIpPublic
                        privatePort
                        publicPort
                        type
                    }
                    gpus {
                        id
                        gpuUtilPercent
                        memoryUtilPercent
                    }
                }
                machine {
                    podHostId
                    gpuDisplayName
                }
                imageName
                gpuCount
            }
        }
    }
    """
    data = graphql(api_key, query)
    if not data:
        return []
    return data.get("myself", {}).get("pods", [])


def show_pods(api_key: str):
    """Display current pods with status and URLs."""
    pods = fetch_pods(api_key)

    if not pods:
        print("  No pods found.\n")
        return

    for p in pods:
        pod_id = p["id"]
        status = p.get("desiredStatus", "?")
        name = p.get("name", "Unnamed")
        gpu = p.get("machine", {}).get("gpuDisplayName", "?")
        cost = p.get("costPerHr", "?")

        if status == "RUNNING":
            indicator = "●"
        elif status == "EXITED":
            indicator = "○"
        else:
            indicator = "◌"

        runtime = p.get("runtime")
        uptime_str = ""
        if runtime and runtime.get("uptimeInSeconds"):
            secs = runtime["uptimeInSeconds"]
            hours = secs // 3600
            mins = (secs % 3600) // 60
            uptime_str = f" (up {hours}h {mins}m)"

        print(f"  {indicator} {name}")
        print(f"    ID:     {pod_id}")
        print(f"    GPU:    {gpu}  |  ${cost}/hr  |  {status}{uptime_str}")

        if status == "RUNNING":
            print(f"    ────────────────────────────────────────")
            print(f"    Frontend:  https://{pod_id}-3000.proxy.runpod.net")
            print(f"    ComfyUI:   https://{pod_id}-8199.proxy.runpod.net")
            print(f"    Jupyter:   https://{pod_id}-8888.proxy.runpod.net")

            if runtime and runtime.get("gpus"):
                for g in runtime["gpus"]:
                    gpu_util = g.get("gpuUtilPercent", 0)
                    mem_util = g.get("memoryUtilPercent", 0)
                    print(f"    GPU Load:  {gpu_util}%  |  VRAM: {mem_util}%")

        print()


def deploy_pod(api_key: str, gpu_type_id: str, volume_gb: int = VOLUME_GB, container_disk_gb: int = CONTAINER_DISK_GB):
    """Deploy a new pod on RunPod."""

    # Show what we're deploying
    print(f"  GPU:    {gpu_type_id}")
    print(f"  Image:  {DOCKER_IMAGE}")
    print(f"  Volume: {volume_gb} GB  |  Disk: {container_disk_gb} GB")
    print(f"  Ports:  3000 (Frontend) · 8199 (ComfyUI) · 8888 (Jupyter) · 22 (SSH)")
    print()

    query = """
    mutation($input: PodFindAndDeployOnDemandInput!) {
        podFindAndDeployOnDemand(input: $input) {
            id
            name
            desiredStatus
            imageName
            machineId
            costPerHr
        }
    }
    """
    variables = {
        "input": {
            "name": POD_NAME,
            "imageName": DOCKER_IMAGE,
            "gpuTypeId": gpu_type_id,
            "cloudType": "ALL",
            "volumeInGb": volume_gb,
            "containerDiskInGb": container_disk_gb,
            "minVcpuCount": MIN_VCPU,
            "minMemoryInGb": MIN_MEMORY_GB,
            "ports": PORTS,
            "volumeMountPath": VOLUME_MOUNT,
            "startJupyter": False,
            "startSsh": True,
            "dockerArgs": "",
            "env": [],
        }
    }

    print("  Deploying...", end="", flush=True)
    data = graphql(api_key, query, variables)

    if not data:
        print(" FAILED")
        print("\n  Could not deploy. The GPU may be sold out.")
        print("  Try a different GPU or wait a few minutes.\n")
        return None

    pod = data.get("podFindAndDeployOnDemand", {})

    if not pod or not pod.get("id"):
        print(" FAILED")
        print("\n  No instances available for this GPU type.")
        print("  Try a different GPU or check RunPod console.\n")
        return None

    pod_id = pod["id"]
    cost = pod.get("costPerHr", "?")

    print(" OK!")
    print()
    print("  ╔═══════════════════════════════════════════════════╗")
    print("  ║              Pod Deployed Successfully            ║")
    print("  ╠═══════════════════════════════════════════════════╣")
    print(f"  ║  Pod ID:   {pod_id:<39} ║")
    print(f"  ║  Cost:     ${cost}/hr{' ' * max(0, 36 - len(str(cost)))} ║")
    print("  ╠═══════════════════════════════════════════════════╣")
    print("  ║  URLs (ready in ~2-3 min):                       ║")
    print(f"  ║  Frontend: https://{pod_id}-3000.proxy.runpod.net  ║")
    print(f"  ║  ComfyUI:  https://{pod_id}-8199.proxy.runpod.net  ║")
    print(f"  ║  Jupyter:  https://{pod_id}-8888.proxy.runpod.net  ║")
    print("  ╚═══════════════════════════════════════════════════╝")
    print()
    print(f"  Manage:  https://www.runpod.io/console/pods")
    print()

    return pod_id


def stop_pod(api_key: str, pod_id: str):
    """Stop a pod (keeps volume, stops billing for GPU)."""
    query = """
    mutation($input: PodStopInput!) {
        podStop(input: $input) {
            id
            desiredStatus
        }
    }
    """
    data = graphql(api_key, query, {"input": {"podId": pod_id}})
    if data:
        pod = data.get("podStop", {})
        print(f"\n  Pod {pod.get('id', pod_id)} stopped.")
        print(f"  Volume preserved — resume anytime.\n")


def resume_pod(api_key: str, pod_id: str, gpu_type_id: str = None):
    """Resume a stopped pod."""
    query = """
    mutation($input: PodResumeInput!) {
        podResume(input: $input) {
            id
            desiredStatus
            costPerHr
        }
    }
    """
    inp = {"podId": pod_id}
    if gpu_type_id:
        inp["gpuTypeId"] = gpu_type_id

    data = graphql(api_key, query, {"input": inp})
    if data:
        pod = data.get("podResume", {})
        print(f"\n  Pod {pod.get('id', pod_id)} resuming...")
        print(f"  Cost: ${pod.get('costPerHr', '?')}/hr")
        print(f"  URLs will be available in ~1 min.\n")


def terminate_pod(api_key: str, pod_id: str):
    """Terminate a pod (deletes everything including volume)."""
    confirm = input(f"\n  WARNING: This will DELETE pod {pod_id} and its volume.\n  Type 'yes' to confirm: ")
    if confirm.strip().lower() != "yes":
        print("  Cancelled.\n")
        return

    query = """
    mutation($input: PodTerminateInput!) {
        podTerminate(input: $input)
    }
    """
    graphql(api_key, query, {"input": {"podId": pod_id}})
    print(f"\n  Pod {pod_id} terminated and deleted.\n")


def list_gpus(api_key: str, show_all: bool = False):
    """List GPU types with pricing and live stock status."""
    print("  Fetching GPU list with availability...\n")

    gpus = fetch_gpus_with_stock(api_key)
    if not gpus:
        print("  Could not fetch GPU list.\n")
        return

    # Filter to GPUs with enough VRAM (unless show_all)
    if not show_all:
        gpus = [g for g in gpus if (g.get("memoryInGb") or 0) >= MIN_VRAM_GB]

    # Sort by VRAM descending, then price
    gpus.sort(key=lambda g: (-(g.get("memoryInGb") or 0), g.get("communityPrice") or 999))

    print(f"  {'#':<4} {'GPU':<35} {'VRAM':<8} {'$/hr':<8} {'ID (for --gpu flag)'}")
    print(f"  {'─' * 4} {'─' * 35} {'─' * 8} {'─' * 8} {'─' * 35}")

    for i, g in enumerate(gpus, 1):
        name = g.get("displayName", g.get("id", "?"))
        mem = f"{g.get('memoryInGb', '?')} GB"
        price = g.get("communityPrice") or g.get("securePrice") or "?"
        price_str = f"${price}" if price != "?" else "N/A"
        gid = g.get("id", "?")
        print(f"  {i:<4} {name:<35} {mem:<8} {price_str:<8} {gid}")

    print(f"\n  Showing {len(gpus)} GPUs with >= {MIN_VRAM_GB} GB VRAM")
    if not show_all:
        print(f"  (Use --list --all to see ALL GPUs)")
    print()

    return gpus


# ─── Interactive Menu ────────────────────────────────────────────────

def interactive_menu(api_key: str, volume_gb: int, container_disk_gb: int):
    """Main interactive menu loop."""
    while True:
        clear_screen()
        print_header()

        # Show active pods summary
        pods = fetch_pods(api_key)
        running = [p for p in pods if p.get("desiredStatus") == "RUNNING"]
        stopped = [p for p in pods if p.get("desiredStatus") == "EXITED"]

        if running:
            print(f"  Active pods: {len(running)} running, {len(stopped)} stopped")
            for p in running:
                pid = p["id"]
                gpu = p.get("machine", {}).get("gpuDisplayName", "?")
                cost = p.get("costPerHr", "?")
                print(f"    ● {p.get('name', 'Unnamed')} — {gpu} — ${cost}/hr")
                print(f"      https://{pid}-3000.proxy.runpod.net")
            print()
        elif stopped:
            print(f"  {len(stopped)} stopped pod(s) available to resume.")
            print()
        else:
            print("  No active pods.")
            print()

        # Menu
        print("  ─── Actions ─────────────────────────────────────")
        print("  [D]  Deploy new pod (live GPU list)")
        print("  [P]  View all pods (detailed)")
        print("  [R]  Resume a stopped pod")
        print("  [S]  Stop a running pod")
        print("  [T]  Terminate (delete) a pod")
        print("  [G]  List all GPU types + pricing")
        print("  [Q]  Quit")
        print()

        choice = input("  > ").strip().upper()

        if choice == "D":
            clear_screen()
            print_header()
            gpu_id = live_gpu_picker(api_key)
            if gpu_id:
                print()
                deploy_pod(api_key, gpu_id, volume_gb, container_disk_gb)
            input("  Press Enter to continue...")

        elif choice == "P":
            clear_screen()
            print_header()
            print("  ─── Your Pods ───────────────────────────────────\n")
            show_pods(api_key)
            input("  Press Enter to continue...")

        elif choice == "R":
            clear_screen()
            print_header()
            stopped_pods = [p for p in fetch_pods(api_key) if p.get("desiredStatus") == "EXITED"]
            if not stopped_pods:
                print("  No stopped pods to resume.\n")
            else:
                print("  Stopped pods:\n")
                for i, p in enumerate(stopped_pods, 1):
                    print(f"  [{i}] {p.get('name', 'Unnamed')} — {p['id']}")
                print()
                idx = input("  Select pod to resume [number]: ").strip()
                try:
                    pod = stopped_pods[int(idx) - 1]
                    resume_pod(api_key, pod["id"])
                except (ValueError, IndexError):
                    print("  Invalid selection.")
            input("  Press Enter to continue...")

        elif choice == "S":
            clear_screen()
            print_header()
            running_pods = [p for p in fetch_pods(api_key) if p.get("desiredStatus") == "RUNNING"]
            if not running_pods:
                print("  No running pods to stop.\n")
            else:
                print("  Running pods:\n")
                for i, p in enumerate(running_pods, 1):
                    gpu = p.get("machine", {}).get("gpuDisplayName", "?")
                    print(f"  [{i}] {p.get('name', 'Unnamed')} — {gpu} — {p['id']}")
                print()
                idx = input("  Select pod to stop [number]: ").strip()
                try:
                    pod = running_pods[int(idx) - 1]
                    stop_pod(api_key, pod["id"])
                except (ValueError, IndexError):
                    print("  Invalid selection.")
            input("  Press Enter to continue...")

        elif choice == "T":
            clear_screen()
            print_header()
            all_pods = fetch_pods(api_key)
            if not all_pods:
                print("  No pods to terminate.\n")
            else:
                print("  All pods:\n")
                for i, p in enumerate(all_pods, 1):
                    status = p.get("desiredStatus", "?")
                    print(f"  [{i}] {p.get('name', 'Unnamed')} — {status} — {p['id']}")
                print()
                idx = input("  Select pod to terminate [number]: ").strip()
                try:
                    pod = all_pods[int(idx) - 1]
                    terminate_pod(api_key, pod["id"])
                except (ValueError, IndexError):
                    print("  Invalid selection.")
            input("  Press Enter to continue...")

        elif choice == "G":
            clear_screen()
            print_header()
            list_gpus(api_key)
            input("  Press Enter to continue...")

        elif choice == "Q":
            print("\n  Bye!\n")
            break

        else:
            pass


def live_gpu_picker(api_key: str) -> str:
    """Fetch live GPU list and let user pick one by number."""
    print("  ─── Available GPUs ──────────────────────────────\n")
    print("  Fetching live GPU data...\n")

    gpus = fetch_gpus_with_stock(api_key)
    if not gpus:
        print("  Could not fetch GPU list.\n")
        return None

    # Filter to suitable GPUs (>= MIN_VRAM_GB)
    suitable = [g for g in gpus if (g.get("memoryInGb") or 0) >= MIN_VRAM_GB]

    # Sort: price ascending (cheapest first that can run our workloads)
    suitable.sort(key=lambda g: g.get("communityPrice") or g.get("securePrice") or 999)

    if not suitable:
        print(f"  No GPUs found with >= {MIN_VRAM_GB} GB VRAM.\n")
        return None

    # Check stock for each GPU and display
    print(f"  {'#':<4} {'GPU':<32} {'VRAM':<8} {'$/hr':<8} {'Stock'}")
    print(f"  {'─' * 4} {'─' * 32} {'─' * 8} {'─' * 8} {'─' * 10}")

    gpu_stock = []
    for i, g in enumerate(suitable, 1):
        name = g.get("displayName", g.get("id", "?"))
        mem = f"{g.get('memoryInGb', '?')} GB"
        price = g.get("communityPrice") or g.get("securePrice") or "?"
        price_str = f"${price}" if price != "?" else "N/A"
        gid = g.get("id", "?")

        # Check stock for this GPU
        detail = check_stock(api_key, gid)
        stock = get_stock_label(detail) if detail else "?"
        gpu_stock.append((g, stock))

        # Color coding via symbols
        if stock in ("IN STOCK", "COMMUNITY", "SECURE"):
            marker = "  ✓"
        elif stock == "SOLD OUT":
            marker = "  ✗"
        else:
            marker = "  ?"

        print(f"  {i:<4} {name:<32} {mem:<8} {price_str:<8} {stock}{marker}")

    print()
    print(f"  ✓ = available   ✗ = sold out")
    print()

    choice = input("  Select GPU [number, or Q to cancel]: ").strip().upper()

    if choice == "Q":
        return None

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(suitable):
            selected = suitable[idx]
            gpu_id = selected.get("id", "?")
            print(f"\n  Selected: {selected.get('displayName', gpu_id)} ({gpu_id})")
            return gpu_id
        else:
            print("  Invalid number.")
            return None
    except ValueError:
        # Maybe they typed a GPU ID directly
        for g in gpus:
            if choice.lower() in (g.get("id", "").lower(), g.get("displayName", "").lower()):
                return g["id"]
        print("  Invalid selection.")
        return None


# ─── CLI Entry Point ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="FEDDA AI Studio — RunPod Deployer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deploy.py                      Interactive menu with live GPU stock
  python deploy.py --gpu "RTX A6000"    Deploy with specific GPU (use ID from --list)
  python deploy.py --list               List all GPUs with pricing
  python deploy.py --pods               List your running pods
  python deploy.py --stop <pod_id>      Stop pod (preserves volume)
  python deploy.py --resume <pod_id>    Resume a stopped pod
  python deploy.py --terminate <pod_id> Delete pod and volume

Environment:
  RUNPOD_API_KEY    Your RunPod API key (or will be prompted)
        """,
    )
    parser.add_argument("--gpu", type=str, help="GPU type ID — deploy directly (use exact ID from --list)")
    parser.add_argument("--list", action="store_true", help="List available GPU types")
    parser.add_argument("--pods", action="store_true", help="List your current pods")
    parser.add_argument("--stop", type=str, metavar="POD_ID", help="Stop a pod")
    parser.add_argument("--resume", type=str, metavar="POD_ID", help="Resume a stopped pod")
    parser.add_argument("--terminate", type=str, metavar="POD_ID", help="Terminate a pod")
    parser.add_argument("--volume", type=int, default=VOLUME_GB, help=f"Volume size in GB (default: {VOLUME_GB})")
    parser.add_argument("--disk", type=int, default=CONTAINER_DISK_GB, help=f"Container disk in GB (default: {CONTAINER_DISK_GB})")

    args = parser.parse_args()

    volume_gb = args.volume
    container_disk_gb = args.disk

    api_key = get_api_key()

    if args.list:
        print_header()
        list_gpus(api_key)
    elif args.pods:
        print_header()
        show_pods(api_key)
    elif args.stop:
        stop_pod(api_key, args.stop)
    elif args.resume:
        resume_pod(api_key, args.resume)
    elif args.terminate:
        terminate_pod(api_key, args.terminate)
    elif args.gpu:
        print_header()
        deploy_pod(api_key, args.gpu, volume_gb, container_disk_gb)
    else:
        interactive_menu(api_key, volume_gb, container_disk_gb)


if __name__ == "__main__":
    main()
