import json
from pathlib import Path
from collections import defaultdict

ROOT_DIR = Path(__file__).resolve().parents[1]
wf_dir = ROOT_DIR / "frontend" / "public" / "workflows"

KNOWN_CORE = {
    'UNETLoader','CLIPLoader','VAELoader','CLIPTextEncode','KSamplerAdvanced',
    'KSampler','ModelSamplingSD3','VAEDecode','SaveImage','LoadImage',
    'ImageSelector','ImageScale','EmptyLatentImage','SetNode','GetNode',
    'WanImageToVideo','VHS_VideoCombine','Note','CheckpointLoaderSimple',
    'ConditioningCombine','ConditioningAverage','LoraLoader','CLIPSetLastLayer',
}

all_classes = defaultdict(set)

for f in sorted(wf_dir.glob('*_api.json')):
    data = json.loads(f.read_text(encoding='utf-8'))
    for node in data.values():
        if isinstance(node, dict) and 'class_type' in node:
            ct = node['class_type']
            if ct not in KNOWN_CORE:
                all_classes[ct].add(f.stem.replace('_api',''))

print('=== CUSTOM NODES REQUIRED ===\n')
for ct in sorted(all_classes.keys()):
    wfs = ', '.join(sorted(all_classes[ct]))
    print(f'  {ct}')
    print(f'    workflows: {wfs}')
    print()
