import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


AgentLLMFn = Callable[[str, List[Dict[str, Any]], Optional[str]], str]


@dataclass
class AgentPolicy:
    sandbox_root: Path
    permission_mode: str = "per_action"
    model_profile: str = "balanced"
    agent_mode: str = "plan_confirm_execute"
    blocked_roots: Optional[List[Path]] = None


class AgentRuntime:
    def __init__(self, root_dir: Path, db_path: Path, llm_fn: AgentLLMFn):
        self.root_dir = root_dir.resolve()
        self.db_path = db_path
        self.snapshots_root = self.root_dir / ".agent_snapshots"
        self.llm_fn = llm_fn
        self.snapshots_root.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_runs (
                  run_id TEXT PRIMARY KEY,
                  session_id TEXT NOT NULL,
                  user_message TEXT NOT NULL,
                  status TEXT NOT NULL,
                  model_profile TEXT NOT NULL,
                  permission_mode TEXT NOT NULL,
                  sandbox_root TEXT NOT NULL,
                  interpretation TEXT NOT NULL DEFAULT '',
                  plan_text TEXT NOT NULL DEFAULT '',
                  risk_summary TEXT NOT NULL DEFAULT '',
                  snapshot_path TEXT NOT NULL DEFAULT '',
                  rollback_ready INTEGER NOT NULL DEFAULT 0,
                  created_at REAL NOT NULL,
                  updated_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_actions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  run_id TEXT NOT NULL,
                  action_index INTEGER NOT NULL,
                  tool_name TEXT NOT NULL,
                  args_json TEXT NOT NULL,
                  preview_text TEXT NOT NULL DEFAULT '',
                  status TEXT NOT NULL,
                  result_json TEXT NOT NULL DEFAULT '',
                  error_text TEXT NOT NULL DEFAULT '',
                  created_at REAL NOT NULL,
                  updated_at REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_actions_run ON agent_actions(run_id, action_index)")
            conn.commit()

    def get_default_settings(self) -> Dict[str, Any]:
        return {
            "agent_mode": "plan_confirm_execute",
            "permission_mode": "per_action",
            "sandbox_root": str(self.root_dir),
            "model_profile": "balanced",
        }

    def _normalize_policy(self, settings: Dict[str, Any]) -> AgentPolicy:
        sandbox_root = Path(str(settings.get("sandbox_root") or self.root_dir)).resolve()
        if not str(sandbox_root):
            sandbox_root = self.root_dir
        permission_mode = str(settings.get("permission_mode") or "per_action").strip().lower()
        if permission_mode not in {"per_action", "session_trust"}:
            permission_mode = "per_action"
        model_profile = str(settings.get("model_profile") or "balanced").strip().lower()
        if model_profile not in {"fast", "balanced", "max_reasoning"}:
            model_profile = "balanced"
        agent_mode = str(settings.get("agent_mode") or "plan_confirm_execute").strip().lower()
        if agent_mode not in {"plan_confirm_execute"}:
            agent_mode = "plan_confirm_execute"

        blocked_roots = []
        drive = os.path.splitdrive(str(sandbox_root))[0] or "C:"
        protected = [
            Path(f"{drive}\\Windows"),
            Path(f"{drive}\\Program Files"),
            Path(f"{drive}\\Program Files (x86)"),
            Path(f"{drive}\\Users\\Default"),
            Path(f"{drive}\\Users\\Public"),
        ]
        blocked_roots.extend([p.resolve() for p in protected])
        return AgentPolicy(
            sandbox_root=sandbox_root,
            permission_mode=permission_mode,
            model_profile=model_profile,
            agent_mode=agent_mode,
            blocked_roots=blocked_roots,
        )

    def create_run(
        self,
        session_id: str,
        user_message: str,
        settings: Dict[str, Any],
        history: List[Dict[str, Any]],
        auto_execute: bool = False,
    ) -> Dict[str, Any]:
        policy = self._normalize_policy(settings)
        run_id = str(uuid.uuid4())
        now = time.time()

        interpreted, plan_text, risk_summary, actions = self._interpret_and_plan(
            user_message=user_message.strip(),
            history=history,
            profile=policy.model_profile,
        )
        if not actions:
            status = "completed"
        elif policy.permission_mode == "session_trust" and auto_execute:
            status = "executing"
        else:
            status = "awaiting_approval"

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_runs(
                  run_id, session_id, user_message, status, model_profile, permission_mode, sandbox_root,
                  interpretation, plan_text, risk_summary, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    session_id,
                    user_message.strip(),
                    status,
                    policy.model_profile,
                    policy.permission_mode,
                    str(policy.sandbox_root),
                    interpreted,
                    plan_text,
                    risk_summary,
                    now,
                    now,
                ),
            )
            for idx, action in enumerate(actions):
                preview = self._preview_action(action)
                conn.execute(
                    """
                    INSERT INTO agent_actions(
                      run_id, action_index, tool_name, args_json, preview_text, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        idx,
                        str(action.get("tool_name") or "").strip(),
                        json.dumps(action.get("args") or {}, ensure_ascii=False),
                        preview,
                        "pending_approval",
                        now,
                        now,
                    ),
                )
            conn.commit()

        if status == "executing":
            self.execute_run(run_id=run_id, settings=settings, approved_action_ids=None, auto_all=True)

        return self.get_run(run_id)

    def _extract_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        raw = (text or "").strip()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            pass
        m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except Exception:
            return None

    def _fallback_actions(self, user_message: str) -> Tuple[str, str, str, List[Dict[str, Any]]]:
        lower = user_message.lower()
        actions: List[Dict[str, Any]] = []
        plan = "Analyze request and execute minimal safe actions inside sandbox."
        interpreted = "General task request."
        risk = "Low risk."
        if "workflow" in lower and ".json" in lower:
            interpreted = "User likely wants workflow JSON assistance."
            actions.append(
                {
                    "tool_name": "search_text",
                    "args": {"query": "workflow", "path": "."},
                }
            )
            risk = "Medium: may propose file updates."
        elif any(k in lower for k in ["fix", "error", "bug", "why"]):
            interpreted = "User likely wants debugging."
            actions.append({"tool_name": "search_text", "args": {"query": "error", "path": "."}})
            risk = "Low: read-only first."
        else:
            actions.append({"tool_name": "list_dir", "args": {"path": "."}})
        return interpreted, plan, risk, actions

    def _interpret_and_plan(
        self,
        user_message: str,
        history: List[Dict[str, Any]],
        profile: str,
    ) -> Tuple[str, str, str, List[Dict[str, Any]]]:
        system = (
            "You are FEDDA Agent Brain planner. Output STRICT JSON only.\n"
            "Schema: {"
            "\"interpretation\": string,"
            "\"plan_text\": string,"
            "\"risk_summary\": string,"
            "\"actions\": [{\"tool_name\": string, \"args\": object}]"
            "}.\n"
            "Allowed tool_name values: read_file, list_dir, search_text, write_file, apply_patch, run_command, workflow_create_or_update.\n"
            "Prefer read/search first unless task clearly asks execution. Keep actions concise."
        )
        user = (
            f"User request:\n{user_message}\n\n"
            "Return 1-8 actions max. Use relative sandbox paths. No markdown."
        )
        try:
            raw = self.llm_fn(user, history[-24:], profile)
            parsed = self._extract_json_object(raw)
            if not parsed:
                return self._fallback_actions(user_message)
            actions = parsed.get("actions")
            if not isinstance(actions, list):
                actions = []
            normalized: List[Dict[str, Any]] = []
            allowed = {
                "read_file",
                "list_dir",
                "search_text",
                "write_file",
                "apply_patch",
                "run_command",
                "workflow_create_or_update",
            }
            for a in actions[:8]:
                if not isinstance(a, dict):
                    continue
                tool = str(a.get("tool_name") or "").strip()
                if tool not in allowed:
                    continue
                args = a.get("args")
                if not isinstance(args, dict):
                    args = {}
                normalized.append({"tool_name": tool, "args": args})
            if not normalized:
                return self._fallback_actions(user_message)
            return (
                str(parsed.get("interpretation") or "Task interpretation unavailable."),
                str(parsed.get("plan_text") or "Execute planned actions safely."),
                str(parsed.get("risk_summary") or "Unknown risk."),
                normalized,
            )
        except Exception:
            return self._fallback_actions(user_message)

    def _safe_path(self, path_value: str, policy: AgentPolicy) -> Path:
        raw = str(path_value or "").strip()
        if not raw:
            raise RuntimeError("Path is required.")
        path = Path(raw)
        if not path.is_absolute():
            path = (policy.sandbox_root / raw).resolve()
        else:
            path = path.resolve()
        sandbox = policy.sandbox_root.resolve()
        if not str(path).lower().startswith(str(sandbox).lower()):
            raise RuntimeError("Path outside sandbox root is blocked.")
        for blocked in policy.blocked_roots or []:
            if str(path).lower().startswith(str(blocked).lower()):
                raise RuntimeError(f"Blocked system path: {blocked}")
        return path

    def _is_destructive_command(self, command: str) -> bool:
        c = command.lower()
        patterns = [
            "rm -rf",
            "remove-item -recurse -force",
            "del /f /s /q",
            "format ",
            "diskpart",
            "shutdown ",
            "reg delete",
            "cipher /w",
        ]
        return any(p in c for p in patterns)

    def _preview_action(self, action: Dict[str, Any]) -> str:
        tool = str(action.get("tool_name") or "")
        args = action.get("args") or {}
        if tool == "run_command":
            return f"run_command: {str(args.get('command') or '')[:240]}"
        if tool in {"write_file", "apply_patch", "read_file", "list_dir", "search_text", "workflow_create_or_update"}:
            target = args.get("path") or args.get("target_path") or args.get("workflow_path") or args.get("query") or ""
            return f"{tool}: {str(target)[:240]}"
        return f"{tool}"

    def _snapshot_before_mutation(self, run_id: str, actions: List[sqlite3.Row], policy: AgentPolicy) -> str:
        run_dir = self.snapshots_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        files_dir = run_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        manifest: Dict[str, Any] = {"run_id": run_id, "created_at": time.time(), "files": []}
        seen = set()
        for row in actions:
            tool = str(row["tool_name"])
            args = json.loads(str(row["args_json"] or "{}"))
            target = None
            if tool in {"write_file", "apply_patch"}:
                target = args.get("path")
            elif tool == "workflow_create_or_update":
                target = args.get("workflow_path")
            if not target:
                continue
            try:
                p = self._safe_path(str(target), policy)
            except Exception:
                continue
            key = str(p).lower()
            if key in seen:
                continue
            seen.add(key)
            rel = f"files/{len(manifest['files'])}.bak"
            backup_path = run_dir / rel
            existed = p.exists()
            if existed and p.is_file():
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, backup_path)
            manifest["files"].append({"target": str(p), "backup_rel": rel if existed else "", "existed": existed})
        (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(run_dir)

    def _execute_action(self, tool_name: str, args: Dict[str, Any], policy: AgentPolicy) -> Dict[str, Any]:
        if tool_name == "list_dir":
            p = self._safe_path(str(args.get("path") or "."), policy)
            if not p.exists():
                return {"success": False, "error": "Path does not exist."}
            items = []
            for entry in sorted(list(p.iterdir()))[:500]:
                items.append({"name": entry.name, "is_dir": entry.is_dir(), "size": entry.stat().st_size if entry.is_file() else 0})
            return {"success": True, "path": str(p), "items": items}

        if tool_name == "read_file":
            p = self._safe_path(str(args.get("path") or ""), policy)
            if not p.exists() or not p.is_file():
                return {"success": False, "error": "File not found."}
            max_chars = int(args.get("max_chars") or 12000)
            text = p.read_text(encoding="utf-8", errors="ignore")
            return {"success": True, "path": str(p), "content": text[:max_chars]}

        if tool_name == "search_text":
            query = str(args.get("query") or "").strip()
            if not query:
                return {"success": False, "error": "query is required."}
            base = self._safe_path(str(args.get("path") or "."), policy)
            if not base.exists():
                return {"success": False, "error": "path not found."}
            max_hits = int(args.get("max_hits") or 80)
            hits = []
            for file in base.rglob("*"):
                if len(hits) >= max_hits:
                    break
                if not file.is_file():
                    continue
                if file.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".mp4", ".webm", ".avi", ".safetensors", ".onnx", ".pth"}:
                    continue
                try:
                    content = file.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                for idx, line in enumerate(content.splitlines(), start=1):
                    if query.lower() in line.lower():
                        hits.append({"path": str(file), "line": idx, "text": line[:400]})
                        if len(hits) >= max_hits:
                            break
            return {"success": True, "query": query, "hits": hits}

        if tool_name == "write_file":
            p = self._safe_path(str(args.get("path") or ""), policy)
            content = str(args.get("content") or "")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"success": True, "path": str(p), "bytes": len(content.encode("utf-8"))}

        if tool_name == "apply_patch":
            p = self._safe_path(str(args.get("path") or ""), policy)
            mode = str(args.get("mode") or "append").lower()
            content = str(args.get("content") or "")
            if mode == "replace":
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                with p.open("a", encoding="utf-8") as fh:
                    fh.write(content)
            return {"success": True, "path": str(p), "mode": mode}

        if tool_name == "workflow_create_or_update":
            wf_path = self._safe_path(str(args.get("workflow_path") or ""), policy)
            workflow_obj = args.get("workflow")
            if isinstance(workflow_obj, str):
                try:
                    workflow_obj = json.loads(workflow_obj)
                except Exception:
                    return {"success": False, "error": "workflow must be valid JSON."}
            if not isinstance(workflow_obj, dict):
                return {"success": False, "error": "workflow object is required."}
            wf_path.parent.mkdir(parents=True, exist_ok=True)
            wf_path.write_text(json.dumps(workflow_obj, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"success": True, "workflow_path": str(wf_path)}

        if tool_name == "run_command":
            command = str(args.get("command") or "").strip()
            cwd = self._safe_path(str(args.get("cwd") or "."), policy)
            if not command:
                return {"success": False, "error": "command is required."}
            if self._is_destructive_command(command):
                return {"success": False, "error": "Destructive command blocked by policy."}
            timeout_s = int(args.get("timeout_s") or 120)
            proc = subprocess.run(
                command,
                cwd=str(cwd),
                shell=True,
                capture_output=True,
                text=True,
                timeout=max(5, min(timeout_s, 1800)),
            )
            return {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "")[:16000],
                "stderr": (proc.stderr or "")[:16000],
            }

        return {"success": False, "error": f"Unsupported tool: {tool_name}"}

    def get_run(self, run_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            run = conn.execute("SELECT * FROM agent_runs WHERE run_id = ?", (run_id,)).fetchone()
            if run is None:
                raise RuntimeError("Run not found.")
            rows = conn.execute(
                "SELECT * FROM agent_actions WHERE run_id = ? ORDER BY action_index ASC",
                (run_id,),
            ).fetchall()
        actions = []
        for row in rows:
            actions.append(
                {
                    "id": int(row["id"]),
                    "index": int(row["action_index"]),
                    "tool_name": str(row["tool_name"]),
                    "args": json.loads(str(row["args_json"] or "{}")),
                    "preview_text": str(row["preview_text"] or ""),
                    "status": str(row["status"]),
                    "result": json.loads(str(row["result_json"] or "{}")) if str(row["result_json"] or "").strip() else {},
                    "error_text": str(row["error_text"] or ""),
                }
            )
        return {
            "success": True,
            "run": {
                "run_id": str(run["run_id"]),
                "session_id": str(run["session_id"]),
                "user_message": str(run["user_message"]),
                "status": str(run["status"]),
                "interpretation": str(run["interpretation"]),
                "plan_text": str(run["plan_text"]),
                "risk_summary": str(run["risk_summary"]),
                "permission_mode": str(run["permission_mode"]),
                "model_profile": str(run["model_profile"]),
                "sandbox_root": str(run["sandbox_root"]),
                "snapshot_path": str(run["snapshot_path"] or ""),
                "rollback_ready": bool(int(run["rollback_ready"] or 0)),
                "created_at": float(run["created_at"]),
                "updated_at": float(run["updated_at"]),
                "actions": actions,
            },
        }

    def execute_run(
        self,
        run_id: str,
        settings: Dict[str, Any],
        approved_action_ids: Optional[List[int]],
        auto_all: bool = False,
    ) -> Dict[str, Any]:
        policy = self._normalize_policy(settings)
        now = time.time()
        with self._connect() as conn:
            run = conn.execute("SELECT * FROM agent_runs WHERE run_id = ?", (run_id,)).fetchone()
            if run is None:
                raise RuntimeError("Run not found.")
            actions = conn.execute("SELECT * FROM agent_actions WHERE run_id = ? ORDER BY action_index ASC", (run_id,)).fetchall()
            if not actions:
                conn.execute(
                    "UPDATE agent_runs SET status = ?, updated_at = ? WHERE run_id = ?",
                    ("completed", now, run_id),
                )
                conn.commit()
                return self.get_run(run_id)

            if auto_all:
                to_exec = list(actions)
                conn.execute("UPDATE agent_actions SET status = ?, updated_at = ? WHERE run_id = ? AND status = ?", ("approved", now, run_id, "pending_approval"))
            else:
                wanted = set(int(x) for x in (approved_action_ids or []))
                to_exec = [a for a in actions if int(a["id"]) in wanted]
                if not to_exec:
                    return self.get_run(run_id)
                conn.execute(
                    f"UPDATE agent_actions SET status = ?, updated_at = ? WHERE run_id = ? AND id IN ({','.join(['?'] * len(wanted))})",
                    tuple(["approved", now, run_id, *wanted]),
                )
            conn.execute("UPDATE agent_runs SET status = ?, updated_at = ? WHERE run_id = ?", ("executing", now, run_id))
            conn.commit()

        mutating = [a for a in to_exec if str(a["tool_name"]) in {"write_file", "apply_patch", "workflow_create_or_update"}]
        snapshot_path = str(run["snapshot_path"] or "").strip()
        if mutating and not snapshot_path:
            snapshot_path = self._snapshot_before_mutation(run_id, mutating, policy)
            with self._connect() as conn:
                conn.execute(
                    "UPDATE agent_runs SET snapshot_path = ?, rollback_ready = 1, updated_at = ? WHERE run_id = ?",
                    (snapshot_path, time.time(), run_id),
                )
                conn.commit()

        failed = False
        for row in to_exec:
            action_id = int(row["id"])
            tool_name = str(row["tool_name"])
            args = json.loads(str(row["args_json"] or "{}"))
            try:
                result = self._execute_action(tool_name, args, policy)
                status = "executed" if bool(result.get("success")) else "failed"
                error_text = "" if status == "executed" else str(result.get("error") or "Execution failed.")
            except Exception as exc:
                result = {"success": False, "error": str(exc)}
                status = "failed"
                error_text = str(exc)
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE agent_actions
                    SET status = ?, result_json = ?, error_text = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (status, json.dumps(result, ensure_ascii=False), error_text, time.time(), action_id),
                )
                conn.commit()
            if status == "failed":
                failed = True
                break

        with self._connect() as conn:
            pending = conn.execute(
                "SELECT COUNT(*) AS c FROM agent_actions WHERE run_id = ? AND status = 'pending_approval'",
                (run_id,),
            ).fetchone()
            if failed:
                final_status = "failed"
            elif int(pending["c"] or 0) > 0:
                final_status = "awaiting_approval"
            else:
                final_status = "completed"
            conn.execute("UPDATE agent_runs SET status = ?, updated_at = ? WHERE run_id = ?", (final_status, time.time(), run_id))
            conn.commit()
        return self.get_run(run_id)

    def deny_actions(self, run_id: str, action_ids: Optional[List[int]]) -> Dict[str, Any]:
        now = time.time()
        with self._connect() as conn:
            if action_ids:
                wanted = [int(x) for x in action_ids]
                conn.execute(
                    f"UPDATE agent_actions SET status = ?, updated_at = ? WHERE run_id = ? AND id IN ({','.join(['?'] * len(wanted))}) AND status = 'pending_approval'",
                    tuple(["denied", now, run_id, *wanted]),
                )
            else:
                conn.execute(
                    "UPDATE agent_actions SET status = ?, updated_at = ? WHERE run_id = ? AND status = 'pending_approval'",
                    ("denied", now, run_id),
                )
            pending = conn.execute(
                "SELECT COUNT(*) AS c FROM agent_actions WHERE run_id = ? AND status = 'pending_approval'",
                (run_id,),
            ).fetchone()
            if int(pending["c"] or 0) == 0:
                conn.execute("UPDATE agent_runs SET status = ?, updated_at = ? WHERE run_id = ?", ("completed", now, run_id))
            conn.commit()
        return self.get_run(run_id)

    def rollback_run(self, run_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            run = conn.execute("SELECT * FROM agent_runs WHERE run_id = ?", (run_id,)).fetchone()
            if run is None:
                raise RuntimeError("Run not found.")
            snapshot_path = str(run["snapshot_path"] or "").strip()
            if not snapshot_path:
                raise RuntimeError("No snapshot exists for this run.")
            manifest_file = Path(snapshot_path) / "manifest.json"
            if not manifest_file.exists():
                raise RuntimeError("Snapshot manifest missing.")
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            restored = []
            for item in manifest.get("files", []):
                target = Path(str(item.get("target") or ""))
                existed = bool(item.get("existed"))
                backup_rel = str(item.get("backup_rel") or "")
                backup = Path(snapshot_path) / backup_rel if backup_rel else None
                if existed:
                    if backup and backup.exists():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(backup, target)
                        restored.append(str(target))
                else:
                    if target.exists():
                        target.unlink()
                        restored.append(str(target))
            conn.execute("UPDATE agent_runs SET status = ?, updated_at = ? WHERE run_id = ?", ("rolled_back", time.time(), run_id))
            conn.commit()
        return {"success": True, "run_id": run_id, "restored_files": restored}
