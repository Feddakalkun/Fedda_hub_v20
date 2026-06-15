# FEDDA v20 Workflow Standard

Same core rules as v18, adapted for the clean v20 bootstrap.

## Core rule

Model-backed workflows should include a `HuggingFaceDownloader` node when they need to fetch weights. Template:

`backend/workflows/HF-downloader/HFdownloadernode.json`

- Backend must not hard-block `/api/generate` before ComfyUI can run the downloader.
- HF token injection is handled in `backend/workflow_service.py`.

## Workflow files

- Prefer API-format JSON under `backend/workflows/<family>/`.
- No absolute local paths (`H:\`, `C:\Users\`, etc.).
- Stable node ids for mapped inputs.
- Explicit output prefixes (`IMAGE/<FAMILY>/0`, `VIDEO/<FAMILY>/0`).

## Mappings

Every app-facing workflow needs an entry in `config/workflow_api.json` with:

- `filename`
- `inputs` map (UI param -> node id + input key)
- Family-prefixed `workflow_id`

## Modules

Each workflow belongs to one module in `config/modules.json`. Core stays small; heavy families are boosters.

v20 starts with `core-shell` only and **empty** `custom_nodes`. Add nodes when you add the first workflow that needs them.

## Frontend

Reuse shared workbench shells as they land in v20. First workflow sets the pattern; later workflows copy it.

## Validation

```powershell
python dev_tools/validate_workflow_standard.py --workflow-id your-id
python dev_tools/validate_workflow_standard.py --all
```