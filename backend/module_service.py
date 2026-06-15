import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class ModuleService:
    """Read the module manifest (core + boosters) and resolve workflow/module ownership."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path(__file__).resolve().parent.parent / "config"
        self.manifest_file = self.config_dir / "modules.json"
        self.workflow_file = self.config_dir / "workflow_api.json"
        self.nodes_file = self.config_dir / "nodes.json"

    def load_manifest(self) -> Dict[str, Any]:
        if not self.manifest_file.exists():
            return {"version": 0, "modules": []}
        with self.manifest_file.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)
        data.setdefault("modules", [])
        return data

    def load_workflow_mapping(self) -> Dict[str, Any]:
        if not self.workflow_file.exists():
            return {}
        with self.workflow_file.open("r", encoding="utf-8-sig") as f:
            return json.load(f)

    def load_node_configs(self) -> Dict[str, Dict[str, Any]]:
        if not self.nodes_file.exists():
            return {}
        with self.nodes_file.open("r", encoding="utf-8-sig") as f:
            nodes = json.load(f)
        return {
            str(node.get("name")): node
            for node in nodes
            if isinstance(node, dict) and node.get("name")
        }

    def list_modules(self, enabled_only: bool = False, include_validation: bool = True) -> List[Dict[str, Any]]:
        manifest = self.load_manifest()
        modules = [
            dict(module)
            for module in manifest.get("modules", [])
            if isinstance(module, dict) and (not enabled_only or module.get("enabled", True))
        ]
        if not include_validation:
            return modules

        workflows = self.load_workflow_mapping()
        nodes = self.load_node_configs()
        for module in modules:
            module["validation"] = self.validate_module(module, workflows, nodes)
        return modules

    def get_module(self, module_id: str, include_validation: bool = True) -> Optional[Dict[str, Any]]:
        for module in self.list_modules(enabled_only=False, include_validation=include_validation):
            if module.get("id") == module_id:
                return module
        return None

    def workflow_index(self) -> Dict[str, Dict[str, Any]]:
        index: Dict[str, Dict[str, Any]] = {}
        for module in self.list_modules(enabled_only=False, include_validation=False):
            for workflow_id in module.get("workflows", []) or []:
                index[str(workflow_id)] = module
        return index

    def module_for_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        return self.workflow_index().get(workflow_id)

    def annotate_workflow(self, workflow_id: str, workflow_info: Dict[str, Any]) -> Dict[str, Any]:
        module = self.module_for_workflow(workflow_id)
        annotated = dict(workflow_info)
        annotated["id"] = workflow_id
        if module:
            annotated["module_id"] = module.get("id")
            annotated["module_label"] = module.get("label")
            annotated["module_pack"] = module.get("pack")
            annotated["module_area"] = module.get("area")
            annotated["module_enabled"] = bool(module.get("enabled", True))
        else:
            annotated["module_id"] = None
            annotated["module_label"] = None
            annotated["module_pack"] = None
            annotated["module_area"] = None
            annotated["module_enabled"] = True
        return annotated

    def validate_module(
        self,
        module: Dict[str, Any],
        workflows: Optional[Dict[str, Any]] = None,
        nodes: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        workflow_map = workflows if workflows is not None else self.load_workflow_mapping()
        node_map = nodes if nodes is not None else self.load_node_configs()
        missing_workflows = [
            workflow_id
            for workflow_id in module.get("workflows", []) or []
            if str(workflow_id) not in workflow_map
        ]
        missing_node_configs = [
            node_name
            for node_name in module.get("custom_nodes", []) or []
            if str(node_name) not in node_map
        ]
        return {
            "ok": not missing_workflows and not missing_node_configs,
            "missing_workflows": missing_workflows,
            "missing_node_configs": missing_node_configs,
        }


module_service = ModuleService()
