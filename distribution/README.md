# Single-file installer

Distribute **`FEDDA_v20_Installer.bat`** only. Users drop it in any folder and double-click.

On first run it creates:

```
YourFolder/
  FEDDA_v20_Installer.bat   <- the one file you gave them
  run.bat                   <- created automatically
  update.bat                <- created automatically
  app/                      <- cloned from GitHub + full runtime install
  logs/                     <- installer logs
```

## Prerequisite

Git for Windows must be installed: https://git-scm.com/download/win

## Install choice

The installer asks:

| Mode | Best for | System impact |
|------|----------|---------------|
| **FULL** (default) | Distribution, clean machines | Everything in `app\` — portable Python, Git, Node, Ollama |
| **LITE** | Pros with Git + Node 18+ already | Python/ComfyUI/caches still in `app\`; uses system Git/Node only to build frontend |

Neither mode touches system Python or global pip.

## Re-run

Double-click the same installer again to pull latest code and re-run inner setup.

## Source of truth

Edit the parent copy at `Fedda_hub_v20/FEDDA_v20_Installer.bat` (outside `app/`), then sync:

```bat
copy /Y ..\..\FEDDA_v20_Installer.bat distribution\FEDDA_v20_Installer.bat
```