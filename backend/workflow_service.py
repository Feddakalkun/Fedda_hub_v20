import json
import os
import sys
import uuid
from typing import Any, Dict, Optional

from lora_service import _normalize_lora_path  # robust path normalization for LoRA prefix checks (Windows \ vs /)

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8-sig")
        sys.stderr.reconfigure(encoding="utf-8-sig")
    except Exception:
        pass

class WorkflowService:
    def __init__(self, workflows_dir: str):
        self.workflows_dir = workflows_dir
        self.mapping_file = os.path.join(os.path.dirname(__file__), "..", "config", "workflow_api.json")

    def load_mapping(self) -> Dict[str, Any]:
        if not os.path.exists(self.mapping_file):
            return {}
        with open(self.mapping_file, "r", encoding="utf-8-sig") as f:
            return json.load(f)

    def load_runtime_settings(self) -> Dict[str, Any]:
        settings_path = os.path.join(os.path.dirname(__file__), "..", "config", "runtime_settings.json")
        if not os.path.exists(settings_path):
            return {}
        try:
            with open(settings_path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            return {}

    def get_workflow_path(self, filename: str) -> str:
        # 1. Try direct path from workflows_dir
        direct_path = os.path.join(self.workflows_dir, filename)
        if os.path.exists(direct_path):
            return direct_path
        
        # 2. Recursive search for just the basename if direct fails
        basename = os.path.basename(filename)
        for root, _, files in os.walk(self.workflows_dir):
            if basename in files:
                return os.path.join(root, basename)
        return ""

    def is_api_format(self, data: dict) -> bool:
        if 'nodes' in data or 'links' in data:
            return False
        for v in data.values():
            if isinstance(v, dict) and 'class_type' in v:
                return True
        return False

    def convert_ui_to_api(self, data: dict) -> dict:
        """
        Robust ComfyUI GUI Ã¢â€ â€™ API format converter.
        Ported from dev_tools/convert_workflows.py
        """
        links = {}
        for l in data.get('links', []):
            links[l[0]] = l

        api = {}
        for node in data.get('nodes', []):
            node_id = str(node['id'])
            class_type = node.get('type', 'Unknown')
            node_inputs = node.get('inputs', []) or []
            widget_values = list(node.get('widgets_values', []) or [])
            
            resolved = {}
            widget_idx = 0

            for inp in node_inputs:
                name = inp.get('name', '')
                link_id = inp.get('link')
                is_widget = 'widget' in inp

                if link_id is not None:
                    lnk = links.get(link_id)
                    if lnk:
                        resolved[name] = [str(lnk[1]), lnk[2]]
                elif is_widget:
                    if widget_idx < len(widget_values):
                        resolved[name] = widget_values[widget_idx]
                        widget_idx += 1
                else:
                    if widget_idx < len(widget_values):
                        resolved[name] = widget_values[widget_idx]
                        widget_idx += 1

            if not node_inputs and widget_values:
                for i, v in enumerate(widget_values):
                    resolved[f'_widget_{i}'] = v

            api[node_id] = {
                'inputs': resolved,
                'class_type': class_type
            }
        return api

    def prepare_payload(self, workflow_id: str, user_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Loads workflow, injects params into UI structure, then converts to API structure.
        """
        mappings = self.load_mapping()
        if workflow_id not in mappings:
            return None

        mapping = mappings[workflow_id]
        path = self.get_workflow_path(mapping.get("filename"))
        if not path or not os.path.exists(path):
            return None

        with open(path, "r", encoding="utf-8-sig") as f:
            workflow = json.load(f)

        is_api = self.is_api_format(workflow)

        # Convert to API format early for reliable LoRA injection (especially rgthree)
        if not is_api:
            print("[WorkflowService] Converting full workflow format to API format before injection")
            workflow = self.convert_ui_to_api(workflow)
            is_api = True

        # Special sanitization for workflows saved with user-specific local files
        if workflow_id == "flux2klein-txt2img":
            self._sanitize_flux2klein_workflow(workflow)

        # 1. Inject parameters
        print(f"[WorkflowService] Preparing payload. is_api={is_api}")

        # Ensure LoRA placeholders are handled even when frontend sends no `loras`.
        # Without this, workflows with a baked-in default LoRA name can fail validation
        # on machines that don't have that specific file installed.
        effective_params = dict(user_params or {})

        if workflow_id == "flux2klein-txt2img":
            print("========== FLUX2-KLEIN PAYLOAD PREP (v2api) ==========")
            print(f"  loras param received: {effective_params.get('loras', 'NOT PRESENT')}")
            print("  >>> LOOK FOR THIS IN BACKEND LOGS - RGTHREE INJECTION SHOULD FOLLOW <<<")
        for input_key, input_info in mapping.get("inputs", {}).items():
            if input_info.get("type") == "loras" and input_key not in effective_params:
                effective_params[input_key] = []

        for param_key, param_value in effective_params.items():
            if param_key in mapping["inputs"]:
                input_info = mapping["inputs"][param_key]
                node_ids_raw = input_info.get("node_ids")
                if isinstance(node_ids_raw, list) and node_ids_raw:
                    target_node_ids = [str(n) for n in node_ids_raw]
                else:
                    target_node_ids = [str(input_info["node_id"])]
                
                print(f"  > Injecting '{param_key}' -> Nodes {target_node_ids} (value: {param_value})")

                if input_info.get("type") == "nsfw_toggle":
                    # When NSFW is disabled, turn off all non-base LoRA slots in every
                    # Power Lora Loader node (lora_1 is always the base WAN model LoRA).
                    if not param_value:
                        for wf_node in workflow.values():
                            if not isinstance(wf_node, dict):
                                continue
                            if wf_node.get("class_type") != "Power Lora Loader (rgthree)":
                                continue
                            for slot_key, slot_val in wf_node.get("inputs", {}).items():
                                if slot_key.startswith("lora_") and slot_key != "lora_1" and isinstance(slot_val, dict):
                                    slot_val["on"] = False
                        print(f"  [OK] NSFW disabled Ã¢â‚¬â€ all non-base LoRA slots turned off")
                    else:
                        print(f"  [OK] NSFW enabled Ã¢â‚¬â€ workflow LoRA slots unchanged")
                    continue

                if input_info.get("type") == "loras" and isinstance(param_value, list):
                    # Safety filter for FLUX2-Klein: only allow LoRAs trained for this specific model
                    # FLUX.1-dev LoRAs have different dimensions and cause matmul errors.
                    if workflow_id == "flux2klein-txt2img":
                        print(f"  [FLUX2-KLEIN] Raw loras from UI: {[l.get('name') for l in param_value]}")
                        before = len(param_value)
                        # Use robust normalization to avoid Windows backslash vs forward slash issues
                        param_value = [
                            l for l in param_value
                            if _normalize_lora_path(l.get("name", "")).startswith("flux2klein/")
                        ]
                        filtered = before - len(param_value)
                        if filtered > 0:
                            print(f"  [FLUX2-Klein] Blocked {filtered} incompatible LoRA(s) Ã¢â‚¬â€ only flux2klein/ prefix allowed on this model")

                    node_id = target_node_ids[0]
                    if node_id not in workflow:
                        print(f"  [WARN] LoRA placeholder node {node_id} not found")
                        continue

                    placeholder = workflow[node_id]
                    class_type = placeholder.get("class_type", "")

                    # Special handling for rgthree Power Lora Loader (used by FLUX2-Klein and some Qwen flows)
                    if workflow_id == "flux2klein-txt2img":
                        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                        print("!!! FLUX2-KLEIN RGTHREE LORA INJECTION PATH HIT !!!")
                        print(f"!!! Node ID from mapping: {node_id}")
                        print(f"!!! Class type of node: {class_type}")
                        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

                    if class_type == "Power Lora Loader (rgthree)":
                        active_loras = [l for l in param_value if l.get("name")]
                        inputs = placeholder.setdefault("inputs", {})
                        # Remove any pre-existing lora_N slots
                        for k in list(inputs.keys()):
                            if k.startswith("lora_"):
                                del inputs[k]
                        if active_loras:
                            for i, lora_data in enumerate(active_loras[:10]):
                                slot = f"lora_{i + 1}"
                                # rgthree serializes nested LoRA names with platform-style
                                # separators. On Windows, matching native ComfyUI exports
                                # avoids silent dropdown mismatch with some custom loaders.
                                lora_path = (
                                    lora_data["name"].replace("/", "\\")
                                    if os.name == "nt"
                                    else lora_data["name"].replace("\\", "/")
                                )
                                slot_data = {
                                    "on": True,
                                    "lora": lora_path,
                                    "strength": float(lora_data.get("strength", 1.0)),
                                    "strengthTwo": None,
                                }
                                inputs[slot] = slot_data
                                if workflow_id == "flux2klein-txt2img":
                                    print(f"    -> Writing to {slot}: {slot_data}")
                            print(f"  [OK] Injected {len(active_loras)} LoRA(s) into rgthree Power Lora Loader {node_id}: {[l['name'] for l in active_loras]}")
                            if workflow_id == "flux2klein-txt2img":
                                print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                                print(f"  [FLUX2-KLEIN LORA INJECTION SUCCESS] Node: {node_id}")
                                print(f"  LoRAs injected: {[l['name'] for l in active_loras]}")
                                print(f"  Final keys on node: {list(inputs.keys())}")
                                print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                        else:
                            print(f"  [OK] No LoRAs sent Ã¢â‚¬â€ cleared lora slots on rgthree node {node_id}")
                        continue

                    # Classic path: Dynamic LoRA chain for standard LoraLoader / LoraLoaderModelOnly
                    # replace the placeholder node with a chain of loaders, then rewire downstream refs.
                    model_source  = placeholder["inputs"].get("model", ["16", 0])
                    clip_source   = placeholder["inputs"].get("clip")          # None for ModelOnly
                    model_only    = clip_source is None

                    del workflow[node_id]

                    active_loras = [l for l in param_value if l.get("name")]

                    if not active_loras:
                        # No LoRAs Ã¢â‚¬â€ bypass: rewire all downstream refs to upstream sources
                        for nid, node in workflow.items():
                            for key, val in list(node.get("inputs", {}).items()):
                                if isinstance(val, list) and len(val) == 2 and str(val[0]) == node_id:
                                    node["inputs"][key] = model_source if val[1] == 0 else (clip_source or ["18", 0])
                    else:
                        curr_model = model_source
                        curr_clip  = clip_source
                        last_id    = None

                        for i, lora_data in enumerate(active_loras[:5]):
                            lid = f"_lora_{i}"
                            if model_only:
                                workflow[lid] = {
                                    "inputs": {
                                        "lora_name":      lora_data["name"],
                                        "strength_model": float(lora_data.get("strength", 1.0)),
                                        "model":          curr_model,
                                    },
                                    "class_type": "LoraLoaderModelOnly",
                                }
                            else:
                                workflow[lid] = {
                                    "inputs": {
                                        "lora_name":      lora_data["name"],
                                        "strength_model": float(lora_data.get("strength", 1.0)),
                                        "strength_clip":  float(lora_data.get("strength", 1.0)),
                                        "model":          curr_model,
                                        "clip":           curr_clip,
                                    },
                                    "class_type": "LoraLoader",
                                }
                                curr_clip = [lid, 1]
                            curr_model = [lid, 0]
                            last_id    = lid

                        # Rewire every downstream ref that pointed at the old placeholder
                        for nid, node in workflow.items():
                            if nid.startswith("_lora_"):
                                continue
                            for key, val in list(node.get("inputs", {}).items()):
                                if isinstance(val, list) and len(val) == 2 and str(val[0]) == node_id:
                                    node["inputs"][key] = [last_id, val[1]]

                        print(f"  [OK] Injected {len(active_loras)} LoRA(s): {[l['name'] for l in active_loras]}")
                    continue

                if input_info.get("type") == "seed_sequence":
                    input_key = input_info.get("input_key") or param_key
                    try:
                        base_seed = int(param_value)
                    except Exception:
                        base_seed = 0
                    for idx, node_id in enumerate(target_node_ids):
                        if node_id in workflow:
                            if "inputs" not in workflow[node_id]:
                                workflow[node_id]["inputs"] = {}
                            workflow[node_id]["inputs"][input_key] = base_seed + idx
                        else:
                            print(f"    [WARN] Node {node_id} NOT FOUND in workflow!")
                    continue

                per_node_values = None
                if (
                    isinstance(param_value, list)
                    and len(target_node_ids) > 1
                    and len(param_value) == len(target_node_ids)
                    and input_info.get("type") not in ("loras", "nsfw_toggle")
                ):
                    per_node_values = param_value

                if is_api:
                    # API Format Injection
                    input_keys = input_info.get("input_keys")
                    if isinstance(input_keys, list) and input_keys:
                        target_input_keys = [str(k) for k in input_keys if str(k).strip()]
                    else:
                        target_input_keys = [input_info.get("input_key") or param_key]
                    for idx, node_id in enumerate(target_node_ids):
                        if node_id in workflow:
                            if "inputs" not in workflow[node_id]:
                                workflow[node_id]["inputs"] = {}
                            for input_key in target_input_keys:
                                workflow[node_id]["inputs"][input_key] = per_node_values[idx] if per_node_values is not None else param_value
                        else:
                            print(f"    [WARN] Node {node_id} NOT FOUND in workflow!")
                else:
                    # UI Format Injection
                    w_idx = input_info.get("widget_index")
                    for node_id in target_node_ids:
                        found = False
                        for node in workflow.get("nodes", []):
                            if str(node["id"]) == node_id:
                                found = True
                                if "widgets_values" in node and w_idx is not None:
                                    if w_idx < len(node["widgets_values"]):
                                        node["widgets_values"][w_idx] = param_value
                                        print(f"    [OK] Updated widget[{w_idx}]")
                                break
                        if not found:
                            print(f"    [WARN] Node {node_id} NOT FOUND in UI nodes!")
        
        # 2. Convert to final API format for ComfyUI if needed
        if not is_api:
            workflow = self.convert_ui_to_api(workflow)

        if workflow_id == "qwen-multi-angles":
            self._trim_qwen_multi_angle_outputs(workflow, user_params)

        # 3. Auto-inject Hugging Face token into downloader nodes when configured
        hf_token = str(self.load_runtime_settings().get("hf_token") or "").strip()
        if hf_token:
            for wf_node in workflow.values():
                if not isinstance(wf_node, dict):
                    continue
                if wf_node.get("class_type") != "HuggingFaceDownloader":
                    continue
                inputs = wf_node.setdefault("inputs", {})
                inputs["hf_token"] = hf_token
            
        return workflow

    def verify_wan21_payload(self, workflow: Dict[str, Any], user_params: Dict[str, Any]) -> Dict[str, Any]:
        """Confirm the WAN Steady Dancer input nodes reflect the filenames requested by the UI."""
        expected_image = str((user_params or {}).get("image") or "").strip()
        expected_video = str((user_params or {}).get("reference_video") or "").strip()
        actual_image = str((workflow.get("76") or {}).get("inputs", {}).get("image") or "").strip()
        actual_video = str((workflow.get("75") or {}).get("inputs", {}).get("video") or "").strip()
        errors = []
        if not expected_image:
            errors.append("Missing Steady Dancer subject image parameter")
        elif actual_image != expected_image:
            errors.append(f"Node 76 image mismatch: expected '{expected_image}', got '{actual_image}'")
        if not expected_video:
            errors.append("Missing Steady Dancer reference video parameter")
        elif actual_video != expected_video:
            errors.append(f"Node 75 video mismatch: expected '{expected_video}', got '{actual_video}'")
        debug = {
            "node_76_image": actual_image,
            "node_75_video": actual_video,
            "expected_image": expected_image,
            "expected_video": expected_video,
            "ok": not errors,
            "errors": errors,
        }
        print(f"[WorkflowService] WAN21 payload verification: {debug}")
        return debug

    def verify_zimage_controlnet_payload(self, workflow: Dict[str, Any], user_params: Dict[str, Any]) -> Dict[str, Any]:
        """Confirm the Z-Image pose stage uses the captured frame and requested character LoRA."""
        expected_image = str((user_params or {}).get("image") or "").strip()
        actual_image = str((workflow.get("99") or {}).get("inputs", {}).get("image") or "").strip()
        requested_loras = [
            str(item.get("name") or "").replace("\\", "/")
            for item in ((user_params or {}).get("loras") or [])
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        ]
        node_129_inputs = (workflow.get("129") or {}).get("inputs", {}) or {}
        injected_loras = [
            str(value.get("lora") or "").replace("\\", "/")
            for key, value in node_129_inputs.items()
            if str(key).startswith("lora_") and isinstance(value, dict) and value.get("on") and str(value.get("lora") or "").strip()
        ]
        errors = []
        if not expected_image:
            errors.append("Missing Z-Image pose frame parameter")
        elif actual_image != expected_image:
            errors.append(f"Node 99 image mismatch: expected '{expected_image}', got '{actual_image}'")
        missing_loras = [name for name in requested_loras if name not in injected_loras]
        if missing_loras:
            errors.append(f"LoRA injection mismatch: missing {missing_loras}, injected {injected_loras}")
        debug = {
            "node_99_image": actual_image,
            "expected_image": expected_image,
            "requested_loras": requested_loras,
            "node_129_loras": injected_loras,
            "ok": not errors,
            "errors": errors,
        }
        print(f"[WorkflowService] Z-Image ControlNet payload verification: {debug}")
        return debug

    def verify_flux2klein_payload(self, workflow: Dict[str, Any], user_params: Dict[str, Any]) -> Dict[str, Any]:
        """Confirm FLUX2-KLEIN rgthree LoRA slots reflect the LoRAs selected in FEDDA."""
        requested_loras = [
            str(item.get("name") or "").replace("\\", "/")
            for item in ((user_params or {}).get("loras") or [])
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        ]
        node = workflow.get("205:522") or {}
        node_inputs = node.get("inputs", {}) or {}
        injected_loras = [
            str(value.get("lora") or "").replace("\\", "/")
            for key, value in node_inputs.items()
            if str(key).startswith("lora_") and isinstance(value, dict) and value.get("on") and str(value.get("lora") or "").strip()
        ]
        missing_loras = [name for name in requested_loras if name not in injected_loras]
        errors = []
        if requested_loras and node.get("class_type") != "Power Lora Loader (rgthree)":
            errors.append(f"Expected rgthree node 205:522, got {node.get('class_type')}")
        if missing_loras:
            errors.append(f"FLUX2-KLEIN LoRA injection mismatch: missing {missing_loras}, injected {injected_loras}")
        debug = {
            "node_id": "205:522",
            "requested_loras": requested_loras,
            "injected_loras": injected_loras,
            "ok": not errors,
            "errors": errors,
        }
        print(f"[WorkflowService] FLUX2-KLEIN payload verification: {debug}")
        return debug

    def _trim_qwen_multi_angle_outputs(self, workflow: dict, user_params: Dict[str, Any]) -> None:
        """Keep only the requested Qwen multi-angle output branches active."""
        try:
            shot_count = int(user_params.get("shot_count") or 6)
        except Exception:
            shot_count = 6
        shot_count = max(1, min(6, shot_count))
        save_nodes = ["259", "260", "261", "262", "263", "264"]
        for node_id in save_nodes[shot_count:]:
            if node_id in workflow:
                workflow.pop(node_id, None)
        print(f"  [Qwen Multiangle] Active output shots: {shot_count}")

    def _sanitize_flux2klein_workflow(self, workflow: dict) -> None:
        """
        Force safe defaults on the Flux2-Klein txt2img workflow so it works
        reliably even if the user had custom styles selected when exporting.
        """
        # Fix Load Styles CSV (node 202)
        if "202" in workflow:
            node = workflow["202"]
            if "inputs" not in node:
                node["inputs"] = {}
            node["inputs"]["styles"] = "No Style"
            print("  [FLUX2-Klein] Sanitized Load Styles CSV -> 'No Style'")

        # Fix Text Concatenate node 201 (was losing delimiter/clean_whitespace after UIÃ¢â€ â€™API conversion)
        if "201" in workflow:
            node = workflow["201"]
            if "inputs" not in node:
                node["inputs"] = {}
            if "delimiter" not in node["inputs"] or not node["inputs"].get("delimiter"):
                node["inputs"]["delimiter"] = ", "
            if "clean_whitespace" not in node["inputs"]:
                node["inputs"]["clean_whitespace"] = "true"
            print("  [FLUX2-Klein] Ensured Text Concatenate 201 has delimiter and clean_whitespace")

    def _ensure_flux2klein_placeholder(self) -> str:
        """Create (or reuse) a tiny safe placeholder image in ComfyUI/input/."""
        try:
            # ComfyUI always has PIL available
            from PIL import Image
            import os

            # ComfyUI/input is the standard place
            # We go up from backend/ to find ComfyUI/
            script_dir = os.path.dirname(os.path.abspath(__file__))
            comfy_root = os.path.abspath(os.path.join(script_dir, "..", "..", "ComfyUI"))
            input_dir = os.path.join(comfy_root, "input")
            os.makedirs(input_dir, exist_ok=True)

            filename = "flux2klein_placeholder.png"
            full_path = os.path.join(input_dir, filename)

            if not os.path.exists(full_path):
                # Create a small neutral gray image (safe for any pipeline)
                img = Image.new("RGB", (512, 512), color=(80, 80, 85))
                img.save(full_path, "PNG")
                print(f"  [FLUX2-Klein] Created safe placeholder image: {full_path}")

            return filename
        except Exception as e:
            print(f"  [FLUX2-Klein] Could not create placeholder image: {e}")
            # Fallback to something that might exist or will at least not crash hard
            return "example.png"

# Initialize service with dynamic path relative to this file
script_dir = os.path.dirname(os.path.abspath(__file__))
default_workflows = os.path.join(script_dir, "workflows")
workflow_service = WorkflowService(workflows_dir=default_workflows)
