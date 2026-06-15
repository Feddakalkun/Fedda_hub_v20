"""
LoRA Service — catalog browsing, download tracking, install scanning.

Packs are sourced from public HuggingFace dataset repos (pmczip).
Catalog is cached for 10 minutes so browsing is snappy.
Preview images: prefers /lora-previews/<pack_key>/<Basename>.jpg stored in GitHub,
falls back to the HuggingFace-hosted image if not present locally.
"""

import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests


def _normalize_lora_path(path: str) -> str:
    """Normalize a LoRA path for reliable prefix/family comparison.
    - Converts Windows backslashes to forward slashes
    - Lowercases (Windows filesystem is case-insensitive)
    - Strips leading/trailing whitespace and slashes
    """
    if not path:
        return ""
    p = str(path).replace("\\", "/").strip().lower()
    return p.strip("/")


# ─── Pack Registry ─────────────────────────────────────────────────────────────
# hf_type: "dataset" or "model" — determines which HF API endpoint to use
# img_subfolder: optional subfolder within the HF repo where preview .jpg images live
PACKS: Dict[str, Dict[str, str]] = {
    "zimage_turbo": {
        "hf_repo":        "pmczip/Z-Image-Turbo_Models",
        "hf_type":        "model",
        "dest":           "zimage_turbo",
        "img_subfolder":  "ZIT_Images",
    },
    "zimage_nsfw": {
        "hf_repo":       "qqnyanddld/nsfw-z-image-lora",
        "hf_type":       "model",
        "dest":          "zimage_turbo",
    },
    "wan22_nsfw": {
        "hf_repo":       "lkzd7/WAN2.2_LoraSet_NSFW",
        "hf_type":       "model",
        "dest":          "wan22",
    },
    "flux2klein": {
        "hf_repo":       "pmczip/FLUX.2-klein-9B_Models",
        "hf_type":       "model",
        "dest":          "flux2klein",
        "img_subfolder": "klein_images",
    },
    "flux1dev": {
        "hf_repo":       "pmczip/FLUX.1-dev_Models",
        "hf_type":       "model",
        "dest":          "flux1dev",
        "img_subfolder": "Flux1D_Images",
    },
    "flux2klein_realism_engine": {
        "dest": "flux2klein",
        "static_items": [
            {
                "name": "Realism Engine Klein",
                "file": "realism-engine-klein.safetensors",
                "url":  "https://civitai.red/api/download/models/2679241?type=Model&format=SafeTensor",
            }
        ],
    },
    "sd15": {
        "hf_repo":  "pmczip/SD1.5_LoRa_Models",
        "hf_type":  "model",
        "dest":     "sd15",
    },
    "sd15_lycoris": {
        "hf_repo":       "pmczip/SD1.5_LyCORIS_Models",
        "hf_type":       "model",
        "dest":          "sd15-lycoris",
        "img_subfolder": "LYCORIS_Images",
    },
    "sdxl": {
        "hf_repo":       "pmczip/SDXL_Models",
        "hf_type":       "model",
        "dest":          "sdxl",
        "img_subfolder": "SDXL_Images",
    },
}

FREE_LORAS = [
    {
        "id":       "emmy",
        "name":     "Emmy",
        "filename": "emmy.safetensors",
        "url":      "https://huggingface.co/datasets/FeddaKalkun/free-loras/resolve/main/emmy.safetensors",
    },
    {
        "id":       "sana",
        "name":     "Sana",
        "filename": "sana.safetensors",
        "url":      "https://huggingface.co/datasets/FeddaKalkun/free-loras/resolve/main/sana.safetensors",
    },
    {
        "id":       "maya",
        "name":     "Maya",
        "filename": "maya.safetensors",
        "url":      "https://huggingface.co/datasets/FeddaKalkun/free-loras/resolve/main/maya.safetensors",
    },
]


class LoRAService:
    def __init__(self, root_dir: Path):
        self.root        = root_dir
        self.lora_dir    = root_dir / "ComfyUI" / "models" / "loras"
        # GitHub-stored previews live under frontend/public
        self.preview_dir = root_dir / "frontend" / "public" / "lora-previews"

        # HF catalog cache: pack_key → (fetch_timestamp, [hf_file_items])
        self._catalog_cache: Dict[str, tuple] = {}
        self._cache_ttl = 600  # 10 minutes

        # Download state: filename → { status, progress, pack_key?, error? }
        self._downloads: Dict[str, Dict[str, Any]] = {}
        # Import jobs: job_id → { status, progress, filename, message? }
        self._import_jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def refresh_cache(self):
        """Force clear any caches so new local files appear immediately."""
        self._catalog_cache.clear()

    def get_dest_for_family(self, family: str) -> Optional[str]:
        """Returns the destination subfolder for a given family/tab."""
        # Map UI family names to pack keys that have a 'dest'
        family_to_pack: Dict[str, str] = {
            "z-image": "zimage_turbo",
            "flux2klein": "flux2klein",
            "sd15": "sd15",
            "sdxl": "sdxl",
            "wan": "wan22_nsfw",
        }

        pack_key = family_to_pack.get(family, family)

        if pack_key in PACKS:
            return PACKS[pack_key].get("dest", pack_key)

        # Fallback: use the family name as folder
        return family

    # ─── Runtime token helpers ─────────────────────────────────────────────

    def _load_runtime_settings(self) -> Dict[str, Any]:
        settings_path = self.root / "config" / "runtime_settings.json"
        try:
            if settings_path.exists():
                import json
                return json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _resolve_download_url(
        self,
        url: str,
        hf_token: Optional[str] = None,
        civitai_token: Optional[str] = None,
    ) -> str:
        """
        Resolve provider-specific URL auth, similar to HF token auto-injection.
        - Civitai: append ?token=<key> when URL host is civitai and token is missing.
        """
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()

        if "civitai.com" in host or "civitai.red" in host:
            token = (civitai_token or "").strip()
            if not token:
                settings = self._load_runtime_settings()
                token = str(settings.get("civitai_api_key") or "").strip()
            if token:
                q = dict(parse_qsl(parsed.query, keep_blank_values=True))
                if "token" not in q:
                    q["token"] = token
                    return urlunparse(parsed._replace(query=urlencode(q, doseq=True)))

        return url

    # ─── HuggingFace helpers ────────────────────────────────────────────────

    def _hf_file_url(self, pack_key: str, filename: str) -> str:
        pack = PACKS[pack_key]
        for item in pack.get("static_items", []):
            if item.get("file") == filename:
                return item.get("url", "")

        repo = pack["hf_repo"]
        if pack["hf_type"] == "dataset":
            return f"https://huggingface.co/datasets/{repo}/resolve/main/{filename}"
        return f"https://huggingface.co/{repo}/resolve/main/{filename}"

    def _preview_url(self, pack_key: str, basename: str) -> Optional[str]:
        """
        Returns the best available preview URL.
        Priority: GitHub-stored static image (.png or .jpg) > HuggingFace subfolder > None.
        """
        for ext in (".png", ".jpg"):
            static = self.preview_dir / pack_key / f"{basename}{ext}"
            if static.exists():
                return f"/lora-previews/{pack_key}/{basename}{ext}"

        pack = PACKS.get(pack_key)
        if not pack:
            return None
        repo = pack["hf_repo"]
        img_subfolder = pack.get("img_subfolder", "")
        img_path = f"{img_subfolder}/{basename}.png" if img_subfolder else f"{basename}.png"
        if pack["hf_type"] == "dataset":
            return f"https://huggingface.co/datasets/{repo}/resolve/main/{img_path}"
        return f"https://huggingface.co/{repo}/resolve/main/{img_path}"

    def _fetch_hf_catalog(self, pack_key: str) -> List[Dict[str, Any]]:
        """Fetch file listing from HuggingFace with cache."""
        pack = PACKS.get(pack_key)
        if not pack:
            return []
        if pack.get("static_items"):
            return []

        now = time.time()
        cached = self._catalog_cache.get(pack_key)
        if cached and (now - cached[0]) < self._cache_ttl:
            return cached[1]

        repo     = pack["hf_repo"]
        hf_type  = pack["hf_type"]
        api_url  = (
            f"https://huggingface.co/api/datasets/{repo}/tree/main"
            if hf_type == "dataset"
            else f"https://huggingface.co/api/models/{repo}/tree/main"
        )

        try:
            resp = requests.get(api_url, timeout=15)
            resp.raise_for_status()
            items = resp.json()
            safetensors = [
                item for item in items
                if isinstance(item, dict) and item.get("path", "").lower().endswith(".safetensors")
            ]
            self._catalog_cache[pack_key] = (now, safetensors)
            return safetensors
        except Exception as exc:
            print(f"[LoRAService] HF fetch failed for '{pack_key}': {exc}")
            # Return stale data if available rather than nothing
            return self._catalog_cache.get(pack_key, (0, []))[1]

    # ─── Install scanning ───────────────────────────────────────────────────

    def get_installed(self) -> Dict[str, Any]:
        """Recursively scan the loras directory and return {filename: info}."""
        result: Dict[str, Any] = {}
        if not self.lora_dir.exists():
            return result
        for f in self.lora_dir.rglob("*.safetensors"):
            try:
                result[f.name] = {
                    "path":    str(f.relative_to(self.lora_dir)),
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 1),
                }
            except Exception:
                pass
        return result

    def list_lora_names(self) -> List[str]:
        """Return relative paths of installed LoRAs for use in ComfyUI (relative to loras dir)."""
        return [info["path"] for info in self.get_installed().values()]

    # ─── Pack catalog & status ──────────────────────────────────────────────

    def get_pack_catalog(self, pack_key: str, limit: int = 1000) -> Dict[str, Any]:
        if pack_key not in PACKS:
            return {"success": False, "error": "Unknown pack"}

        pack = PACKS[pack_key]
        installed = self.get_installed()

        items: List[Dict[str, Any]] = []
        dest_subfolder = pack.get("dest", "") or ""

        if pack.get("static_items"):
            for item in pack.get("static_items", [])[:limit]:
                raw_file = item.get("file", "")
                if not raw_file:
                    continue
                # Ensure the file field includes the correct subfolder for this pack
                filename = f"{dest_subfolder}/{raw_file}" if dest_subfolder and not raw_file.startswith(dest_subfolder + "/") else raw_file
                basename = Path(raw_file).stem
                items.append({
                    "name":        item.get("name") or basename.replace("_", " "),
                    "file":        filename,
                    "installed":   filename in installed or raw_file in installed,
                    "size_mb":     item.get("size_mb"),
                    "preview_url": item.get("preview_url"),
                })
        else:
            hf_files = self._fetch_hf_catalog(pack_key)
            for hf_item in hf_files[:limit]:
                raw_name = Path(hf_item.get("path", "")).name
                if not raw_name:
                    continue
                # Prefix with the destination subfolder so the name matches what ComfyUI reports
                filename = f"{dest_subfolder}/{raw_name}" if dest_subfolder else raw_name
                basename = Path(raw_name).stem
                size_bytes = hf_item.get("size", 0)

                items.append({
                    "name":        basename.replace("_", " "),
                    "file":        filename,
                    "installed":   filename in installed or raw_name in installed,
                    "size_mb":     round(size_bytes / (1024 * 1024), 1) if size_bytes else None,
                    "preview_url": self._preview_url(pack_key, basename),
                })

        # Installed first, then alphabetical
        items.sort(key=lambda x: (not x["installed"], x["name"].lower()))

        return {
            "success":   True,
            "pack_key":  pack_key,
            "total":     len(items),
            "installed": sum(1 for i in items if i["installed"]),
            "items":     items,
        }

    def get_pack_status(self, pack_key: str) -> Dict[str, Any]:
        if pack_key not in PACKS:
            return {"success": False, "error": "Unknown pack"}

        with self._lock:
            active = [
                fn for fn, d in self._downloads.items()
                if d.get("status") == "downloading" and d.get("pack_key") == pack_key
            ]

        catalog = self.get_pack_catalog(pack_key)
        return {
            "success":          True,
            "pack_key":         pack_key,
            "status":           "running" if active else "idle",
            "active_downloads": len(active),
            "installed":        catalog.get("installed", 0),
            "total":            catalog.get("total", 0),
        }

    # ─── Download helpers ───────────────────────────────────────────────────

    def get_download_status(self, filename: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self._downloads.get(filename, {"status": "idle", "progress": 0}))

    def _do_download(
        self,
        url: str,
        dest: Path,
        filename: str,
        pack_key: Optional[str] = None,
        hf_token: Optional[str] = None,
        civitai_token: Optional[str] = None,
    ) -> None:
        with self._lock:
            self._downloads[filename] = {"status": "downloading", "progress": 0, "pack_key": pack_key}
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            headers = {}
            if hf_token:
                headers["Authorization"] = f"Bearer {hf_token}"

            resolved_url = self._resolve_download_url(url, hf_token=hf_token, civitai_token=civitai_token)
            resp = requests.get(resolved_url, stream=True, timeout=60, headers=headers)
            resp.raise_for_status()

            total      = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(dest, "wb") as fh:
                for chunk in resp.iter_content(65536):
                    if chunk:
                        fh.write(chunk)
                        downloaded += len(chunk)
                        if total and downloaded % (1024 * 1024) < 65536:  # ~1 MB intervals
                            prog = int(downloaded / total * 100)
                            with self._lock:
                                self._downloads[filename]["progress"] = prog

            with self._lock:
                self._downloads[filename] = {"status": "completed", "progress": 100, "pack_key": pack_key}

        except Exception as exc:
            with self._lock:
                self._downloads[filename] = {"status": "error", "progress": 0, "error": str(exc), "pack_key": pack_key}
            if dest.exists():
                try:
                    dest.unlink()
                except Exception:
                    pass

    def download_single(self, pack_key: str, filename: str) -> Dict[str, Any]:
        if pack_key not in PACKS:
            return {"success": False, "error": "Unknown pack"}
        pack = PACKS[pack_key]
        dest = self.lora_dir / pack["dest"] / filename
        if dest.exists() and dest.stat().st_size > 10_000:
            return {"success": True, "status": "already_installed"}
        url = self._hf_file_url(pack_key, filename)
        if not url:
            return {"success": False, "error": "No download URL found for item"}
        threading.Thread(
            target=self._do_download,
            args=(url, dest, filename, pack_key),
            daemon=True,
        ).start()
        return {"success": True, "status": "started"}

    def sync_pack(self, pack_key: str) -> Dict[str, Any]:
        """Queue download of every file in a pack that isn't already installed."""
        if pack_key not in PACKS:
            return {"success": False, "error": "Unknown pack"}
        catalog  = self.get_pack_catalog(pack_key)
        pending  = [item for item in catalog.get("items", []) if not item["installed"]]
        pack     = PACKS[pack_key]

        def _task() -> None:
            for item in pending:
                dest = self.lora_dir / pack["dest"] / item["file"]
                url  = self._hf_file_url(pack_key, item["file"])
                if not url:
                    continue
                self._do_download(url, dest, item["file"], pack_key)

        threading.Thread(target=_task, daemon=True).start()
        return {"success": True, "queued": len(pending)}

    # ─── Free starter pack ──────────────────────────────────────────────────

    def install_free_lora(self, filename: str) -> Dict[str, Any]:
        lora = next((l for l in FREE_LORAS if l["filename"] == filename), None)
        if not lora:
            return {"success": False, "error": "Unknown free LoRA"}
        dest = self.lora_dir / "starter" / filename
        if dest.exists() and dest.stat().st_size > 10_000:
            return {"success": True, "status": "already_installed"}
        threading.Thread(
            target=self._do_download,
            args=(lora["url"], dest, filename, "starter"),
            daemon=True,
        ).start()
        return {"success": True, "status": "started"}

    def install_all_free(self) -> Dict[str, Any]:
        installed = self.get_installed()
        queued = 0
        for lora in FREE_LORAS:
            if lora["filename"] not in installed:
                self.install_free_lora(lora["filename"])
                queued += 1
        return {"success": True, "queued": queued}

    # ─── URL import ─────────────────────────────────────────────────────────

    def import_from_url(
        self,
        url: str,
        hf_token: Optional[str] = None,
        civitai_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        raw_name = url.split("?")[0].split("/")[-1]
        filename = raw_name if raw_name.endswith(".safetensors") else raw_name + ".safetensors"
        job_id   = str(uuid.uuid4())[:8]
        dest     = self.lora_dir / "imported" / filename

        with self._lock:
            self._import_jobs[job_id] = {"status": "queued", "progress": 0, "filename": filename}

        def _task() -> None:
            with self._lock:
                self._import_jobs[job_id]["status"] = "downloading"
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                direct = url.replace("/blob/", "/resolve/") if "/blob/" in url else url
                direct = self._resolve_download_url(direct, hf_token=hf_token, civitai_token=civitai_token)
                headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}

                resp  = requests.get(direct, stream=True, timeout=60, headers=headers)
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                done  = 0

                with open(dest, "wb") as fh:
                    for chunk in resp.iter_content(65536):
                        if chunk:
                            fh.write(chunk)
                            done += len(chunk)
                            if total and done % (1024 * 1024) < 65536:
                                with self._lock:
                                    self._import_jobs[job_id]["progress"] = int(done / total * 100)

                with self._lock:
                    self._import_jobs[job_id] = {"status": "completed", "progress": 100, "filename": filename}

            except Exception as exc:
                with self._lock:
                    self._import_jobs[job_id] = {"status": "error", "message": str(exc), "filename": filename}
                if dest.exists():
                    try:
                        dest.unlink()
                    except Exception:
                        pass

        threading.Thread(target=_task, daemon=True).start()
        return {"success": True, "job_id": job_id, "filename": filename}

    def get_import_status(self, job_id: str) -> Dict[str, Any]:
        with self._lock:
            job = self._import_jobs.get(job_id)
        if not job:
            return {"success": False, "error": "Job not found"}
        return {"success": True, **job}


lora_service = LoRAService(Path(__file__).parent.parent)
