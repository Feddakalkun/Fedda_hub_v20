# FEDDA Hub v20 Handoff

## Current state

v20 is a **clean bootstrap**. The installer and ComfyUI bridge are inherited from v19. The UI, cards, workflows, and custom node list are intentionally empty.

What works today:

- Repo layout and git remote target
- Inner installer (`scripts/install.bat` → LITE/FULL)
- Service launcher (`run.bat`: Ollama, ComfyUI :8199, backend :8000, Vite :5173)
- Frontend shell with home cards, image/video section pickers (empty), gallery/library/ollama placeholders
- Registry-driven navigation and breadcrumbs
- UI logging panel in the header

What is intentionally missing:

- Workflow JSON packs (add per `WORKFLOW_STANDARD.md`)
- Card videos and branded poster art (placeholders in `public/cards/placeholders/`)
- Custom nodes in `nodes.json` (add with first workflow module)
- Workflow workspace pages

## Repo layout

```
Fedda_hub_v20/
  FEDDA_v20_Installer.bat
  run.bat
  app/
    run.bat
    scripts/
    frontend/
    backend/
    config/
    docs/v20/
```

Runtime folders (`ComfyUI/`, `python_embeded/`, `cache/`, `logs/`, `node_modules/`) stay local and gitignored.

## Next steps

1. Pick the first workflow family to ship (likely a single image txt2img pack).
2. Add module + nodes + workflow JSON + registry card + page component.
3. Run installer smoke test on a clean folder.
4. Replace placeholder card art with final posters/videos.

## Constraints

- No hardcoded drive paths; everything anchors to install folder.
- No personal prompt libraries in git.
- One registry for UI navigation — no duplicate tab lists.
- Log meaningful changes in `BREADCRUMBS.md`.