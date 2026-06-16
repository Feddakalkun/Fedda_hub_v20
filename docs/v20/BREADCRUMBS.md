# FEDDA Hub v20 Breadcrumbs

## 2026-06-15 - v20 clean bootstrap

- Created `H:\Fedda-Hub\Fedda_hub_v20` as the new development root and Git target (`https://github.com/Feddakalkun/Fedda_hub_v20`).
- Ported proven infrastructure from v19: installer scripts, `run.bat` orchestration, backend services, `dev_tools`, RunPod helpers.
- Reset content layer: empty `nodes.json`, empty `workflow_api.json`, `core-shell` only in `modules.json`, no workflow families except HF-downloader template.
- Removed personal/unused config (wildcards, prompt library, ltx catalog).
- Built new frontend shell: registry-driven cards, hash routing, header breadcrumb trail, unified design tokens, SystemStrip with UI log panel.
- Documented rules in `docs/v20/UI_STANDARD.md`, `WORKFLOW_STANDARD.md`, `HANDOFF.md`.

## 2026-06-15 - Minimal installer (stop legacy Z-Image bootstrap)

- Fixed `module_nodes.ps1`: empty `custom_nodes` now skips node install instead of falling back to all of `nodes.json`.
- Removed auto Z-Image core model download from `install_lite.ps1` / `install.ps1` / `update_logic.ps1`.
- Trimmed installer Python extras to backend bridge only; workflow deps install with their module later.
- Node compatibility patches only run when that node folder exists.

Add a dated entry here after every meaningful update.