#!/usr/bin/env python3
"""Validate FEDDA workflow files against the workflow standard (see docs/v20/WORKFLOW_STANDARD.md)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT / "backend" / "workflows"
MAPPING_FILE = ROOT / "config" / "workflow_api.json"
MODULES_FILE = ROOT / "config" / "modules.json"

KNOWN_MODEL_FOLDERS = {
    "checkpoints",
    "clip",
    "clip_vision",
    "controlnet",
    "detection",
    "diffusion_models",
    "loras",
    "model_patches",
    "sams",
    "text_encoders",
    "ultralytics/bbox",
    "unet",
    "vae",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def is_api_workflow(workflow: Any) -> bool:
    return isinstance(workflow, dict) and all(
        isinstance(node, dict) and "class_type" in node
        for node in workflow.values()
        if isinstance(node, dict)
    )


def iter_api_nodes(workflow: Dict[str, Any]) -> Iterable[Tuple[str, Dict[str, Any]]]:
    for node_id, node in workflow.items():
        if isinstance(node, dict) and "class_type" in node:
            yield str(node_id), node


def parse_download_links(raw: str) -> List[Tuple[str, str, str]]:
    links: List[Tuple[str, str, str]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            links.append((parts[0] if parts else "", "", ""))
            continue
        url = parts[0]
        folder = parts[1].replace("\\", "/")
        filename = parts[2] if len(parts) >= 3 else Path(url.split("?", 1)[0]).name
        links.append((url, folder, filename))
    return links


def workflow_module_index() -> Dict[str, str]:
    if not MODULES_FILE.exists():
        return {}
    manifest = load_json(MODULES_FILE)
    index: Dict[str, str] = {}
    for module in manifest.get("modules", []) or []:
        module_id = str(module.get("id") or "")
        for workflow_id in module.get("workflows", []) or []:
            index[str(workflow_id)] = module_id
    return index


def validate_workflow(
    workflow_id: str,
    mapping: Dict[str, Any],
    module_index: Dict[str, str],
    require_downloader: bool,
) -> List[str]:
    errors: List[str] = []
    info = mapping.get(workflow_id)
    if not isinstance(info, dict):
        return [f"{workflow_id}: missing mapping entry"]

    rel_filename = str(info.get("filename") or "").strip()
    if not rel_filename:
        return [f"{workflow_id}: mapping has no filename"]

    workflow_path = WORKFLOWS_DIR / rel_filename
    if not workflow_path.exists():
        return [f"{workflow_id}: workflow file not found: {workflow_path}"]

    try:
        workflow = load_json(workflow_path)
    except Exception as exc:
        return [f"{workflow_id}: workflow JSON failed to parse: {exc}"]

    serialized = json.dumps(workflow, ensure_ascii=False)
    if re.search(r"\b[A-Za-z]:\\", serialized):
        errors.append(f"{workflow_id}: workflow contains a local absolute Windows path")

    if not is_api_workflow(workflow):
        errors.append(f"{workflow_id}: workflow is not API format")
        return errors

    node_ids = {node_id for node_id, _ in iter_api_nodes(workflow)}
    inputs = info.get("inputs") or {}
    if not isinstance(inputs, dict) or not inputs:
        errors.append(f"{workflow_id}: mapping has no inputs")
    else:
        for param_name, input_info in inputs.items():
            if not isinstance(input_info, dict):
                errors.append(f"{workflow_id}: input '{param_name}' is not an object")
                continue
            if input_info.get("type") == "nsfw_toggle":
                continue
            raw_ids = input_info.get("node_ids") or [input_info.get("node_id")]
            target_ids = [str(node_id) for node_id in raw_ids if node_id is not None]
            if not target_ids:
                errors.append(f"{workflow_id}: input '{param_name}' has no node id")
            for node_id in target_ids:
                if node_id not in node_ids:
                    errors.append(f"{workflow_id}: input '{param_name}' targets missing node {node_id}")
            if input_info.get("type") != "loras" and not (
                input_info.get("input_key") or input_info.get("input_keys")
            ):
                errors.append(f"{workflow_id}: input '{param_name}' has no input_key/input_keys")

    downloader_nodes = [
        (node_id, node)
        for node_id, node in iter_api_nodes(workflow)
        if node.get("class_type") == "HuggingFaceDownloader"
    ]
    if require_downloader and not downloader_nodes:
        errors.append(f"{workflow_id}: expected a HuggingFaceDownloader node")

    for node_id, node in downloader_nodes:
        raw_links = str((node.get("inputs") or {}).get("download_links") or "").strip()
        if not raw_links:
            errors.append(f"{workflow_id}: downloader node {node_id} has empty download_links")
            continue
        for url, folder, filename in parse_download_links(raw_links):
            if not url.startswith("https://huggingface.co/"):
                errors.append(f"{workflow_id}: downloader node {node_id} has non-HF url: {url}")
            if folder not in KNOWN_MODEL_FOLDERS and not folder.startswith("loras/"):
                errors.append(f"{workflow_id}: downloader node {node_id} has unusual target folder: {folder}")
            if not filename:
                errors.append(f"{workflow_id}: downloader node {node_id} has missing filename for {url}")

    output_nodes = [
        node
        for _, node in iter_api_nodes(workflow)
        if node.get("class_type") in {"SaveImage", "VHS_VideoCombine", "SaveAnimatedWEBP", "SaveWEBM"}
    ]
    if not output_nodes:
        errors.append(f"{workflow_id}: no known output/save node found")

    if workflow_id not in module_index:
        errors.append(f"{workflow_id}: no module ownership in config/modules.json")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow-id", action="append", help="Workflow id to validate. Can be passed multiple times.")
    parser.add_argument("--all", action="store_true", help="Validate every workflow in config/workflow_api.json.")
    parser.add_argument("--require-downloader", action="store_true", help="Require a HuggingFaceDownloader node.")
    args = parser.parse_args()

    mapping = load_json(MAPPING_FILE)
    module_index = workflow_module_index()
    workflow_ids = list(mapping.keys()) if args.all else (args.workflow_id or [])
    if not workflow_ids:
        parser.error("pass --workflow-id or --all")

    all_errors: List[str] = []
    for workflow_id in workflow_ids:
        all_errors.extend(validate_workflow(workflow_id, mapping, module_index, args.require_downloader))

    if all_errors:
        print("FEDDA workflow standard validation failed:")
        for error in all_errors:
            print(f"  - {error}")
        return 1

    print(f"FEDDA workflow standard validation passed for {len(workflow_ids)} workflow(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
