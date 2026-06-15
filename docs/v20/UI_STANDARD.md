# FEDDA Hub v20 UI Standard

v20 resets the frontend from a clean shell. Every new submenu, card, and workflow page should follow these rules so the app stays consistent as you add modules.

## Single source of truth

`frontend/src/modules/registry.ts` owns:

- Home cards and section cards
- Tab ids, labels, descriptions, status badges
- Which page component renders each workspace tab
- Card poster/video paths

Do not add parallel navigation config files. If the header or quick links need data, derive it from the registry.

Backend/installer ownership stays in:

- `config/modules.json` — module packs, custom nodes, workflow ids
- `config/workflow_api.json` — ComfyUI input mappings
- `config/nodes.json` — full custom node catalog

## View hierarchy

```
Home
  -> Image Studio (section cards)
      -> Workflow workspace page
  -> Video Studio (section cards)
      -> Workflow workspace page
  -> Gallery / LoRA Library / Ollama (direct workspace tabs)
```

Hash routes:

| Hash | View |
|------|------|
| `#/home` | Home cards |
| `#/image` | Image workflow picker |
| `#/video` | Video workflow picker |
| `#/tab/{tabId}` | Workspace page |

Breadcrumbs are rendered in the header from the active view. Do not hand-roll breadcrumb strings inside workflow pages.

## Layout primitives

Use the shared building blocks:

| Primitive | Path | Use for |
|-----------|------|---------|
| `WorkflowCard` | `components/cards/WorkflowCard.tsx` | Home + section pickers |
| `CardGrid` | `components/layout/CardGrid.tsx` | All card grids |
| `Panel` | `ui/primitives.tsx` | Page sections and forms |
| `EmptyState` | `ui/primitives.tsx` | Zero-workflow or not-wired states |
| `SystemStrip` | `components/shell/SystemStrip.tsx` | Service status + UI logs |

Workflow pages should open inside a `Panel` or a dedicated workbench shell added later — not ad-hoc full-width layouts.

## Styling rules

- Use CSS variables from `index.css` (`--fedda-*`). No one-off hex colors in components unless promoting a new token.
- Spacing: 8px grid (`8`, `16`, `24`, `32`).
- Radius: `var(--fedda-radius)` for panels/cards, `var(--fedda-radius-sm)` for buttons.
- Typography: Inter only. Page titles via `.fedda-page-hero`, panel titles via `Panel`.
- Motion: subtle `framer-motion` on cards only; avoid animating form controls.

## Adding a workflow (checklist)

1. Add workflow JSON under `backend/workflows/<family>/`.
2. Add mapping entry in `config/workflow_api.json`.
3. Add module entry in `config/modules.json` with `custom_nodes` and `workflows`.
4. Append node definitions to `config/nodes.json` when new packs are needed.
5. Register a card + tab in `registry.ts` with `workflows: ['your-id']` and `area: 'image' | 'video'`.
6. Create `pages/<family>/YourPage.tsx` using shared workbench components.
7. Point `Page` in the registry module to your component.
8. Add poster (and optional hover video) under `frontend/public/cards/`.
9. Run `python dev_tools/validate_workflow_standard.py --workflow-id your-id`.

## Logging

- UI events: `services/uiLogger.ts` (`fedda_v20_ui_logs` in localStorage).
- Dev handoffs: dated entries in `docs/v20/BREADCRUMBS.md`.
- Installer/runtime: `app/logs/` (gitignored).

Wire meaningful UI actions (generate, download, settings save) through `addUiLog()` so the SystemStrip log panel stays useful.

## What not to copy from older versions

- Legacy CSS layers (`v14`, `v15`, `v16` class names)
- Duplicate `navigation.ts` tab lists
- Personal prompt libraries, wildcards, unused catalogs
- Per-workflow one-off submenu markup

Keep older versions as reference only. Port patterns, not files wholesale.