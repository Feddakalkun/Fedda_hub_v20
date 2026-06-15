import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from lora_service import _normalize_lora_path


UIAgentLLMFn = Callable[[str, str], str]


class UIAgentPlanningError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class FEDDAMemPalace:
    """Tiny local-first palace adapter for FEDDA UI Agent memory.

    MemPalace upstream can be installed separately later, but FEDDA keeps this
    core path dependency-free and transparent: wings are workflow families,
    rooms are workflow ids, halls are memory kinds, drawers are verbatim notes.
    """

    def __init__(self, root_dir: Path):
        self.path = root_dir / "config" / "ui_agent_mempalace.json"

    def status(self) -> Dict[str, Any]:
        try:
            import importlib.util

            installed = importlib.util.find_spec("mempalace") is not None
        except Exception:
            installed = False
        return {
            "success": True,
            "mode": "fedda-local-palace",
            "upstream_available": installed,
            "path": str(self.path),
            "note": "FEDDA uses a local MemPalace-compatible hierarchy without requiring installer dependencies.",
        }

    def remember(
        self,
        workflow_id: str,
        kind: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        safe_workflow = _safe_workflow_id(workflow_id) or "ui-agent"
        safe_kind = re.sub(r"[^a-z0-9_.-]+", "-", (kind or "note").lower()).strip("-") or "note"
        data = self._load()
        workflow_cfg = V1_WORKFLOW_CONFIG.get(safe_workflow, {})
        wing = str(workflow_cfg.get("kind") or "ui-agent")
        room = safe_workflow
        hall = safe_kind
        palace = data.setdefault("palace", {})
        wing_data = palace.setdefault(wing, {})
        room_data = wing_data.setdefault(room, {})
        drawers = room_data.setdefault(hall, [])
        entry = {
            "id": f"{int(time.time() * 1000)}-{len(drawers) + 1}",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "title": (title or "UI Agent memory").strip()[:160],
            "content": " ".join((content or "").split())[:4000],
            "metadata": metadata or {},
        }
        drawers.insert(0, entry)
        del drawers[40:]
        self._save(data)
        return entry

    def search(self, query: str, workflow_id: str = "", limit: int = 5) -> List[Dict[str, Any]]:
        words = [w for w in _words(query) if w not in STOPWORDS]
        if not words:
            return []
        data = self._load()
        palace = data.get("palace", {}) if isinstance(data, dict) else {}
        scoped_workflow = _safe_workflow_id(workflow_id) if workflow_id else ""
        scored: List[tuple[int, str, str, str, Dict[str, Any]]] = []
        for wing, wing_data in palace.items():
            if not isinstance(wing_data, dict):
                continue
            for room, room_data in wing_data.items():
                if scoped_workflow and room != scoped_workflow:
                    continue
                if not isinstance(room_data, dict):
                    continue
                for hall, drawers in room_data.items():
                    if not isinstance(drawers, list):
                        continue
                    for drawer in drawers:
                        if not isinstance(drawer, dict):
                            continue
                        haystack = f"{drawer.get('title', '')} {drawer.get('content', '')}".lower()
                        score = sum(1 for word in words if word in haystack)
                        if score:
                            scored.append((score, str(wing), str(room), str(hall), drawer))
        scored.sort(key=lambda item: (-item[0], str(item[4].get("created_at", "")), item[2]))
        return [
            {
                "wing": wing,
                "room": room,
                "hall": hall,
                "drawer": drawer,
                "score": score,
            }
            for score, wing, room, hall, drawer in scored[: max(1, min(limit, 20))]
        ]

    def _load(self) -> Dict[str, Any]:
        try:
            if not self.path.exists():
                return {"version": 1, "palace": {}}
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {"version": 1, "palace": {}}
        except Exception:
            return {"version": 1, "palace": {}}

    def _save(self, data: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


V1_WORKFLOW_CONFIG: Dict[str, Dict[str, Any]] = {
    "z-image": {
        "label": "Z-Image Txt2Img",
        "kind": "image",
        "tab": "z-image-txt2img",
        "status": "verified",
        "requires_image": False,
        "defaults": {
            "prompt": "",
            "negative": "blurry, ugly, bad proportions, low quality, artifacts",
            "width": 1024,
            "height": 1024,
            "steps": 11,
            "cfg": 1,
            "seed": -1,
        },
        "lora_prefixes": ["zimage_turbo/", "zimage-turbo/"],
    },
    "flux2klein-txt2img": {
        "label": "FLUX2-KLEIN",
        "kind": "image",
        "tab": "flux-txt2img",
        "status": "lab",
        "requires_image": False,
        "defaults": {
            "prompt": "",
            "negative": "",
            "width": 1024,
            "height": 1024,
            "steps": 8,
            "cfg": 1.2,
            "seed": -1,
            "sampler_name": "euler",
        },
        "lora_prefixes": ["flux2klein/"],
    },
    "firered-image-edit": {
        "label": "FireRed Edit",
        "kind": "image_edit",
        "tab": "firered-image-edit",
        "status": "verified",
        "requires_image": True,
        "defaults": {
            "prompt": "",
            "seed": -1,
            "steps": 8,
            "cfg": 1,
            "use_lightning": True,
        },
        "lora_prefixes": [],
    },
    "qwen-rapid-edit-v23": {
        "label": "Qwen Rapid Edit",
        "kind": "image_edit",
        "tab": "qwen-rapid-edit-v23",
        "status": "verified",
        "requires_image": True,
        "defaults": {
            "prompt": "",
            "negative": "",
            "width": 768,
            "height": 768,
            "seed": -1,
            "steps": 8,
            "cfg": 1,
            "sampler_name": "euler",
        },
        "lora_prefixes": [],
    },
    "ltx-img2vid": {
        "label": "LTX Img2Vid",
        "kind": "video",
        "tab": "ltx-img2vid",
        "status": "verified",
        "requires_image": True,
        "defaults": {
            "prompt": "",
            "negative": "blurry, low quality, deformed, jitter, artifacts",
            "seed": -1,
        },
        "lora_prefixes": [],
    },
}


STOPWORDS = {
    "about",
    "after",
    "agent",
    "animate",
    "clown",
    "costume",
    "create",
    "dress",
    "edit",
    "fashion",
    "fire",
    "firered",
    "flux",
    "generate",
    "image",
    "klein",
    "lora",
    "make",
    "photo",
    "prompt",
    "qwen",
    "rapid",
    "red",
    "using",
    "video",
    "with",
    "zimage",
}


def _safe_workflow_id(workflow_id: str) -> str:
    value = (workflow_id or "").strip().lower()
    value = re.sub(r"[^a-z0-9_.-]+", "-", value).strip("-")
    if not value:
        return ""
    return value[:96]


def _extract_json_object(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass

    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _words(text: str) -> List[str]:
    return [w.lower() for w in re.findall(r"[a-zA-Z0-9]+", text or "") if len(w) >= 3]


def _coerce_number(value: Any, fallback: Any, minimum: Optional[float] = None, maximum: Optional[float] = None) -> Any:
    if value is None or value == "":
        return fallback
    try:
        number = float(value)
    except Exception:
        return fallback
    if isinstance(fallback, int) and not isinstance(fallback, bool):
        number = int(round(number))
    if minimum is not None:
        number = max(number, minimum)
    if maximum is not None:
        number = min(number, maximum)
    return number


class UIAgentService:
    def __init__(
        self,
        root_dir: Path,
        workflow_service: Any,
        module_service: Any,
        lora_service: Any,
        llm_fn: UIAgentLLMFn,
    ):
        self.root_dir = root_dir
        self.workflow_service = workflow_service
        self.module_service = module_service
        self.lora_service = lora_service
        self.llm_fn = llm_fn
        self.workflow_memory_path = root_dir / "config" / "workflow_memory.json"
        self.mem_palace = FEDDAMemPalace(root_dir)

    def list_workflows(self) -> List[Dict[str, Any]]:
        mapping = self.workflow_service.load_mapping()
        workflows: List[Dict[str, Any]] = []
        for workflow_id, cfg in V1_WORKFLOW_CONFIG.items():
            if workflow_id not in mapping:
                continue
            module = self.module_service.module_for_workflow(workflow_id)
            if module and not bool(module.get("enabled", True)):
                continue
            input_map = mapping.get(workflow_id, {}).get("inputs", {})
            workflows.append({
                "workflow_id": workflow_id,
                "label": cfg["label"],
                "kind": cfg["kind"],
                "tab": cfg["tab"],
                "status": cfg["status"],
                "requires_image": bool(cfg["requires_image"]),
                "accepted_params": list(input_map.keys()),
                "defaults": dict(cfg["defaults"]),
                "lora_prefixes": list(cfg["lora_prefixes"]),
            })
        return workflows

    def plan(
        self,
        message: str,
        session_id: str = "",
        current_tab: str = "",
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        clean_message = (message or "").strip()
        if not clean_message:
            raise UIAgentPlanningError(400, "message is required.")

        workflows = self.list_workflows()
        if not workflows:
            raise UIAgentPlanningError(500, "No UI Agent workflows are available.")

        installed_loras = self._installed_loras()
        routed_workflow = self._route_workflow(clean_message, current_tab)
        candidate_loras = self._candidate_loras(clean_message, installed_loras)
        memory_preview = self._memory_lines(routed_workflow, limit=4)
        palace_preview = self._palace_lines(clean_message, routed_workflow, limit=4)
        parsed = self._ask_llm(
            message=clean_message,
            session_id=session_id,
            current_tab=current_tab,
            workflows=workflows,
            candidate_loras=candidate_loras,
            memory_lines=memory_preview + palace_preview,
        )

        workflow_id = _safe_workflow_id(str(parsed.get("workflow_id") or routed_workflow))
        if workflow_id not in V1_WORKFLOW_CONFIG:
            workflow_id = routed_workflow
        if workflow_id not in {w["workflow_id"] for w in workflows}:
            raise UIAgentPlanningError(400, f"Workflow '{workflow_id}' is not available to UI Agent V1.")

        cfg = V1_WORKFLOW_CONFIG[workflow_id]
        mapping = self.workflow_service.load_mapping().get(workflow_id, {})
        accepted_params = set((mapping.get("inputs") or {}).keys())
        defaults = dict(cfg["defaults"])
        warnings: List[str] = []
        params = self._params_from_defaults(defaults, parsed, workflow_id)
        character_prompt = self._character_prompt(clean_message, parsed)

        image_filename = self._attachment_filename(attachments or [])
        if cfg["requires_image"]:
            if image_filename:
                params["image"] = image_filename
            else:
                warnings.append(f"{cfg['label']} needs a source image before this plan can run.")

        selected_lora = self._select_lora(
            workflow_id=workflow_id,
            message=clean_message,
            parsed=parsed,
            installed_loras=installed_loras,
        )
        if selected_lora:
            params["loras"] = [{"name": selected_lora, "strength": 1}]
        elif cfg["lora_prefixes"] and self._message_mentions_lora(clean_message):
            warnings.append(f"No installed {cfg['label']} LoRA matched the request.")

        prompt = str(parsed.get("prompt") or "").strip()
        if not prompt:
            prompt = self._fallback_prompt(clean_message, workflow_id, selected_lora)
        params["prompt"] = prompt

        if workflow_id == "flux2klein-txt2img" and character_prompt:
            params["prompt"] = ", ".join([params["prompt"], character_prompt])

        plan_param_keys = accepted_params | set(defaults.keys()) | {"image", "loras"}
        filtered_params = {k: v for k, v in params.items() if k in plan_param_keys}
        if "negative" in accepted_params and "negative" not in filtered_params and "negative" in defaults:
            filtered_params["negative"] = defaults["negative"]

        memory_used = self._memory_lines(workflow_id, limit=3) + self._palace_lines(clean_message, workflow_id, limit=3)
        confidence = _coerce_number(parsed.get("confidence"), 0.72 if workflow_id == routed_workflow else 0.62, 0, 1)
        if confidence < 0.55:
            warnings.append("Low confidence plan; review the workflow choice and prompt before using it.")

        plan = {
            "intent": str(parsed.get("intent") or self._intent_for_workflow(workflow_id)),
            "workflow_id": workflow_id,
            "workflow_label": cfg["label"],
            "confidence": confidence,
            "reason": str(parsed.get("reason") or self._reason_for_workflow(workflow_id, clean_message)),
            "character_prompt": character_prompt,
            "params": filtered_params,
            "memory_used": memory_used,
            "warnings": warnings,
            "requires_approval": True,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        return {
            "success": True,
            "summary": self._summary(plan),
            "plan": plan,
            "mempalace": self.mem_palace.status(),
        }

    def prepare(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self.validate_plan(plan, strict=False)
        warnings = normalized.get("warnings", [])
        blocked = normalized.get("blocked_reasons", [])
        return {
            "success": True,
            "ready": not blocked,
            "workflow_id": normalized["workflow_id"],
            "workflow_label": normalized["workflow_label"],
            "params": normalized["params"],
            "warnings": warnings,
            "blocked_reasons": blocked,
            "summary": "Plan is ready to generate." if not blocked else "Plan needs attention before generation.",
        }

    def validate_plan(self, plan: Dict[str, Any], strict: bool = True) -> Dict[str, Any]:
        if not isinstance(plan, dict):
            raise UIAgentPlanningError(400, "plan must be an object.")
        workflow_id = _safe_workflow_id(str(plan.get("workflow_id") or ""))
        if workflow_id not in V1_WORKFLOW_CONFIG:
            raise UIAgentPlanningError(400, f"Workflow '{workflow_id}' is not allowed for UI Agent.")
        available_ids = {w["workflow_id"] for w in self.list_workflows()}
        if workflow_id not in available_ids:
            raise UIAgentPlanningError(400, f"Workflow '{workflow_id}' is not available.")

        cfg = V1_WORKFLOW_CONFIG[workflow_id]
        mapping = self.workflow_service.load_mapping().get(workflow_id, {})
        accepted_params = set((mapping.get("inputs") or {}).keys())
        defaults = dict(cfg["defaults"])
        incoming_params = plan.get("params") if isinstance(plan.get("params"), dict) else {}
        params = dict(defaults)
        params.update({k: v for k, v in incoming_params.items() if k in accepted_params or k in defaults or k in {"image", "loras", "client_id"}})

        params = self._params_from_defaults(params, params, workflow_id)
        if "prompt" in accepted_params or "prompt" in defaults:
            params["prompt"] = " ".join(str(params.get("prompt") or "").split())
        if "negative" in params:
            params["negative"] = " ".join(str(params.get("negative") or "").split())

        warnings = [str(item) for item in plan.get("warnings", []) if str(item).strip()] if isinstance(plan.get("warnings"), list) else []
        blocked: List[str] = []
        if cfg["requires_image"] and not str(params.get("image") or "").strip():
            blocked.append(f"{cfg['label']} needs a source image filename.")
            params.pop("image", None)

        params["loras"] = self._validated_loras(workflow_id, params.get("loras"))
        if not params["loras"]:
            params.pop("loras", None)

        plan_param_keys = accepted_params | set(defaults.keys()) | {"image", "loras", "client_id"}
        params = {k: v for k, v in params.items() if k in plan_param_keys}

        if strict and blocked:
            raise UIAgentPlanningError(400, " ".join(blocked))
        return {
            "intent": str(plan.get("intent") or self._intent_for_workflow(workflow_id)),
            "workflow_id": workflow_id,
            "workflow_label": cfg["label"],
            "confidence": _coerce_number(plan.get("confidence"), 0.7, 0, 1),
            "reason": str(plan.get("reason") or self._reason_for_workflow(workflow_id, "")),
            "character_prompt": str(plan.get("character_prompt") or "").strip()[:400],
            "params": params,
            "memory_used": [str(item) for item in plan.get("memory_used", [])] if isinstance(plan.get("memory_used"), list) else [],
            "warnings": warnings,
            "blocked_reasons": blocked,
            "requires_approval": True,
        }

    def remember_run(self, plan: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self.validate_plan(plan, strict=False)
        params = normalized.get("params", {})
        content = json.dumps(
            {
                "workflow_id": normalized["workflow_id"],
                "prompt": params.get("prompt", ""),
                "negative": params.get("negative", ""),
                "settings": {k: params.get(k) for k in ("width", "height", "steps", "cfg", "seed", "sampler_name") if k in params},
                "loras": params.get("loras", []),
                "prompt_id": result.get("prompt_id"),
            },
            ensure_ascii=False,
        )
        return self.mem_palace.remember(
            workflow_id=normalized["workflow_id"],
            kind="approved-run",
            title=f"Approved UI Agent run: {normalized['workflow_label']}",
            content=content,
            metadata={"prompt_id": result.get("prompt_id"), "source": "ui-agent"},
        )

    def mempalace_status(self) -> Dict[str, Any]:
        return self.mem_palace.status()

    def _ask_llm(
        self,
        message: str,
        session_id: str,
        current_tab: str,
        workflows: List[Dict[str, Any]],
        candidate_loras: List[str],
        memory_lines: List[str],
    ) -> Dict[str, Any]:
        system = (
            "You are FEDDA UI Agent planner. Return STRICT JSON only. "
            "Never call tools or generation. Pick only one allowed workflow. "
            "Use only installed LoRA names from the provided list. "
            "Schema: {\"intent\": string, \"workflow_id\": string, \"confidence\": number, "
            "\"reason\": string, \"prompt\": string, \"negative\": string, "
            "\"character_prompt\": string, \"width\": number, \"height\": number, "
            "\"steps\": number, \"cfg\": number, \"seed\": number, "
            "\"sampler_name\": string, \"lora_query\": string}."
        )
        prompt = (
            f"User message: {message}\n"
            f"Session id: {session_id or 'none'}\n"
            f"Current tab: {current_tab or 'none'}\n"
            f"Allowed workflows: {json.dumps(workflows, ensure_ascii=False)}\n"
            f"Installed candidate LoRAs: {json.dumps(candidate_loras[:30], ensure_ascii=False)}\n"
            f"Recent workflow memory: {json.dumps(memory_lines[:6], ensure_ascii=False)}\n"
            "Return JSON only."
        )
        raw = self.llm_fn(system, prompt)
        return _extract_json_object(raw)

    def _installed_loras(self) -> List[str]:
        try:
            names = self.lora_service.list_lora_names()
            return [str(name).replace("\\", "/") for name in names if str(name).strip()]
        except Exception:
            return []

    def _route_workflow(self, message: str, current_tab: str = "") -> str:
        lower = f"{message} {current_tab}".lower()
        if "flux" in lower or "klein" in lower:
            return "flux2klein-txt2img"
        if "ltx" in lower or "img2vid" in lower or "image to video" in lower or "animate" in lower or "motion" in lower:
            return "ltx-img2vid"
        if "qwen" in lower or "rapid" in lower:
            return "qwen-rapid-edit-v23"
        if "firered" in lower or "fire red" in lower:
            return "firered-image-edit"
        if "edit" in lower and "image" in lower:
            return "firered-image-edit"
        return "z-image"

    def _candidate_loras(self, message: str, installed_loras: List[str]) -> List[str]:
        terms = [w for w in _words(message) if w not in STOPWORDS]
        scored: List[tuple[int, str]] = []
        for lora in installed_loras:
            norm = _normalize_lora_path(lora)
            score = sum(1 for term in terms if term in norm)
            if score:
                scored.append((score, lora))
        scored.sort(key=lambda item: (-item[0], item[1].lower()))
        return [item[1] for item in scored]

    def _select_lora(
        self,
        workflow_id: str,
        message: str,
        parsed: Dict[str, Any],
        installed_loras: List[str],
    ) -> str:
        prefixes = V1_WORKFLOW_CONFIG[workflow_id]["lora_prefixes"]
        if not prefixes:
            return ""

        query_parts = [message]
        for key in ("lora_query", "character_prompt", "prompt"):
            value = str(parsed.get(key) or "").strip()
            if value:
                query_parts.append(value)
        query = " ".join(query_parts)
        terms = [w for w in _words(query) if w not in STOPWORDS]

        scored: List[tuple[int, str]] = []
        normalized_prefixes = [_normalize_lora_path(prefix) + ("" if prefix.endswith("/") else "/") for prefix in prefixes]
        for lora in installed_loras:
            norm = _normalize_lora_path(lora)
            if not any(norm.startswith(prefix) for prefix in normalized_prefixes):
                continue
            score = sum(1 for term in terms if term in norm)
            if score:
                scored.append((score, lora))
        scored.sort(key=lambda item: (-item[0], item[1].lower()))
        return scored[0][1] if scored else ""

    def _params_from_defaults(self, defaults: Dict[str, Any], parsed: Dict[str, Any], workflow_id: str) -> Dict[str, Any]:
        params = dict(defaults)
        if "width" in params:
            params["width"] = _coerce_number(parsed.get("width"), params["width"], 512, 2048)
        if "height" in params:
            params["height"] = _coerce_number(parsed.get("height"), params["height"], 512, 2048)
        if "steps" in params:
            max_steps = 20 if workflow_id in {"flux2klein-txt2img", "firered-image-edit"} else 30
            params["steps"] = _coerce_number(parsed.get("steps"), params["steps"], 1, max_steps)
        if "cfg" in params:
            params["cfg"] = _coerce_number(parsed.get("cfg"), params["cfg"], 0, 8)
        if "seed" in params:
            params["seed"] = _coerce_number(parsed.get("seed"), params["seed"], -1, None)
        if "negative" in params and parsed.get("negative") is not None:
            params["negative"] = str(parsed.get("negative") or "").strip()
        if "sampler_name" in params and parsed.get("sampler_name"):
            params["sampler_name"] = str(parsed.get("sampler_name") or params["sampler_name"]).strip()
        return params

    def _memory_lines(self, workflow_id: str, limit: int = 3) -> List[str]:
        safe_id = _safe_workflow_id(workflow_id)
        if not safe_id or not self.workflow_memory_path.exists():
            return []
        try:
            data = json.loads(self.workflow_memory_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        entries = data.get(safe_id, []) if isinstance(data, dict) else []
        if not isinstance(entries, list):
            return []
        try:
            entries = sorted(entries, key=lambda entry: str(entry.get("created_at", "")), reverse=True)
        except Exception:
            pass
        lines = []
        for entry in entries[: max(1, min(limit, 8))]:
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("title") or "Workflow memory").strip()
            content = " ".join(str(entry.get("content") or "").split())
            combined = title if not content else f"{title}: {content}"
            lines.append(combined[:260])
        return lines

    def _palace_lines(self, query: str, workflow_id: str, limit: int = 3) -> List[str]:
        lines = []
        for item in self.mem_palace.search(query, workflow_id=workflow_id, limit=limit):
            drawer = item.get("drawer") or {}
            title = str(drawer.get("title") or "Palace memory").strip()
            content = " ".join(str(drawer.get("content") or "").split())
            lines.append((title if not content else f"{title}: {content}")[:260])
        return lines

    def _validated_loras(self, workflow_id: str, value: Any) -> List[Dict[str, Any]]:
        prefixes = V1_WORKFLOW_CONFIG[workflow_id]["lora_prefixes"]
        if not isinstance(value, list) or not prefixes:
            return []
        installed = {_normalize_lora_path(name): name for name in self._installed_loras()}
        normalized_prefixes = [_normalize_lora_path(prefix) + ("" if prefix.endswith("/") else "/") for prefix in prefixes]
        valid: List[Dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            raw_name = str(item.get("name") or "").strip()
            norm = _normalize_lora_path(raw_name)
            if not norm or norm not in installed:
                continue
            if not any(norm.startswith(prefix) for prefix in normalized_prefixes):
                continue
            strength = _coerce_number(item.get("strength"), 1.0, 0, 2)
            valid.append({"name": installed[norm], "strength": strength})
        return valid[:5]

    def _attachment_filename(self, attachments: List[Dict[str, Any]]) -> str:
        for item in attachments:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or "").lower()
            filename = str(item.get("filename") or "").strip()
            if filename and (not kind or kind == "image"):
                return filename
        return ""

    def _message_mentions_lora(self, message: str) -> bool:
        lower = message.lower()
        return "lora" in lower or "zimage" in lower or "klein" in lower or "flux" in lower

    def _character_prompt(self, message: str, parsed: Dict[str, Any]) -> str:
        explicit = str(parsed.get("character_prompt") or "").strip()
        if explicit:
            return explicit[:400]
        terms = [w for w in _words(message) if w not in STOPWORDS]
        return " ".join(terms[:12])

    def _fallback_prompt(self, message: str, workflow_id: str, selected_lora: str) -> str:
        request = " ".join(message.split())
        if workflow_id == "ltx-img2vid":
            return f"Cinematic image-to-video motion based on the reference image, {request}, stable identity, natural camera movement."
        if workflow_id in {"firered-image-edit", "qwen-rapid-edit-v23"}:
            return f"Edit the source image naturally: {request}. Preserve identity, pose, composition, and lighting."
        identity = ""
        if selected_lora:
            name = Path(selected_lora).stem.replace("_", " ").replace("-", " ")
            identity = f"{name}, "
        return f"{identity}{request}, photorealistic, detailed face, natural lighting, sharp focus"

    def _intent_for_workflow(self, workflow_id: str) -> str:
        if workflow_id == "ltx-img2vid":
            return "create_video"
        if workflow_id in {"firered-image-edit", "qwen-rapid-edit-v23"}:
            return "edit_image"
        return "create_image"

    def _reason_for_workflow(self, workflow_id: str, message: str) -> str:
        if workflow_id == "flux2klein-txt2img":
            return "The request mentions FLUX2-KLEIN or a Klein LoRA."
        if workflow_id == "ltx-img2vid":
            return "The request asks for animation or image-to-video motion."
        if workflow_id in {"firered-image-edit", "qwen-rapid-edit-v23"}:
            return "The request asks for an image edit workflow."
        if "lora" in message.lower():
            return "The request asks for image generation with a character LoRA."
        return "The request is a general image generation prompt."

    def _summary(self, plan: Dict[str, Any]) -> str:
        label = str(plan.get("workflow_label") or "workflow")
        intent = str(plan.get("intent") or "plan").replace("_", " ")
        return f"Prepared a {label} {intent} plan."
