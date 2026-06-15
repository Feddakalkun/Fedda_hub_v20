"""
Robust ComfyUI GUI → API format converter.
Handles the newer format where some inputs have a 'widget' key instead of being
tracked purely by index offset. Links are dicts at top level: links[link_id] = [id, from_node, from_slot, to_node, to_slot, type]
"""
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT_DIR / "dev_tools" / "workflow_import"
OUTPUT_DIR = ROOT_DIR / "frontend" / "public" / "workflows"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def is_api_format(data: dict) -> bool:
    if 'nodes' in data or 'links' in data:
        return False
    for v in data.values():
        if isinstance(v, dict) and 'class_type' in v:
            return True
    return False


def convert(data: dict) -> dict:
    # Build link lookup: link_id -> [link_id, from_node, from_slot, to_node, to_slot, type]
    links = {}
    for l in data.get('links', []):
        links[l[0]] = l  # key = link_id

    api = {}

    for node in data.get('nodes', []):
        node_id = str(node['id'])
        class_type = node.get('type', 'Unknown')
        title = node.get('title') or class_type

        # Gather all declared inputs
        node_inputs = node.get('inputs', []) or []
        widget_values = list(node.get('widgets_values', []) or [])

        resolved = {}
        widget_idx = 0

        for inp in node_inputs:
            name = inp.get('name', '')
            link_id = inp.get('link')
            is_widget = 'widget' in inp  # connected widget in newer format

            if link_id is not None:
                # This input is connected to another node's output
                lnk = links.get(link_id)
                if lnk:
                    resolved[name] = [str(lnk[1]), lnk[2]]
                # If it's also a widget type (connected widget), don't consume a widget value
            elif is_widget:
                # It's a widget input that's NOT connected — get from widget_values
                if widget_idx < len(widget_values):
                    resolved[name] = widget_values[widget_idx]
                    widget_idx += 1
            else:
                # Regular unconnected input — consume a widget value
                if widget_idx < len(widget_values):
                    resolved[name] = widget_values[widget_idx]
                    widget_idx += 1

        # Some node types have all values as widget values with zero named inputs
        # e.g. simple loaders like UNETLoader, CLIPLoader, VAELoader
        if not node_inputs and widget_values:
            # We need to know the param names – best effort: use positional keys
            for i, v in enumerate(widget_values):
                resolved[f'_widget_{i}'] = v

        api[node_id] = {
            'inputs': resolved,
            'class_type': class_type,
            '_meta': {'title': title}
        }

    return api


results = []
errors = []

for wf_file in sorted(INPUT_DIR.glob('*.json')):
    try:
        with open(wf_file, encoding='utf-8') as f:
            data = json.load(f)

        if is_api_format(data):
            converted = data
            status = 'ALREADY API format - copied as-is'
        else:
            converted = convert(data)
            status = f'CONVERTED — {len(converted)} nodes'

        clean_name = wf_file.stem.lower().replace(' ', '_') + '_api.json'
        out_path = OUTPUT_DIR / clean_name

        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(converted, f, indent=2, ensure_ascii=False)

        results.append((wf_file.name, clean_name, status))
        print(f"[OK] {wf_file.name}\n     → {clean_name}\n     ({status})\n")

    except Exception as e:
        errors.append((wf_file.name, str(e)))
        print(f"[ERROR] {wf_file.name}: {e}\n")

print(f"{'='*60}")
print(f"Done: {len(results)} converted, {len(errors)} failed")
if errors:
    print("\nFailed:")
    for name, err in errors:
        print(f"  {name}: {err}")
