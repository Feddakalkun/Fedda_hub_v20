import json
import urllib.request
import sys
import random

SERVER_ADDRESS = "127.0.0.1:8188"

# You will need to change this to the exact name of an SDXL or Z-Image model you have installed.
MODEL_NAME = "z-image-turbo.safetensors"  

def queue_prompt(prompt):
    p = {"prompt": prompt}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{SERVER_ADDRESS}/prompt", data=data)
    try:
        urllib.request.urlopen(req)
        print("Prompt queued successfully for background generation!")
    except Exception as e:
        print(f"Failed to queue prompt: {e}")
        print("Is ComfyUI running?")

def build_workflow(theme, colors):
    return {
      "3": {
        "inputs": {
          "seed": random.randint(1, 100000000),
          "steps": 25,
          "cfg": 3.0,
          "sampler_name": "euler_ancestral",
          "scheduler": "karras",
          "denoise": 1,
          "model": ["4", 0],
          "positive": ["6", 0],
          "negative": ["7", 0],
          "latent_image": ["5", 0]
        },
        "class_type": "KSampler"
      },
      "4": {
        "inputs": {
          "ckpt_name": MODEL_NAME
        },
        "class_type": "CheckpointLoaderSimple"
      },
      "5": {
        "inputs": {
          "width": 1920, # Desktop HD
          "height": 1080,
          "batch_size": 4  # Generate 4 options at once
        },
        "class_type": "EmptyLatentImage"
      },
      "6": {
        "inputs": {
          "text": f"Premium {theme} UI background, aesthetic photography, out of focus, bokeh, frosted glassmorphism, subtle {colors} glowing light leaks, 8k resolution, elegant minimalism, dark mode ui wallpaper, smooth volumetric lighting, empty space in center",
          "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode"
      },
      "7": {
        "inputs": {
          "text": "ugly, low quality, noisy, text, watermark, busy, sharp objects, people, faces, structured objects",
          "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode"
      },
      "8": {
        "inputs": {
          "samples": ["3", 0],
          "vae": ["4", 2]
        },
        "class_type": "VAEDecode"
      },
      "9": {
        "inputs": {
          "filename_prefix": f"FeddaUI_BG_{theme.replace(' ', '_')}",
          "images": ["8", 0]
        },
        "class_type": "SaveImage"
      }
    }

if __name__ == "__main__":
    print("Sending generation task to ComfyUI...")
    
    # Generate some SFW "Safe" backgrounds
    sfw_workflow = build_workflow("clean dark tech", "cyan and deep blue")
    queue_prompt(sfw_workflow)
    
    # Generate some NSFW "Unlocked" backgrounds (harder, deeper colors)
    nsfw_workflow = build_workflow("seductive dark sensual", "magenta and deep purple")
    queue_prompt(nsfw_workflow)
    
    print("Done! Check your ComfyUI/output folder in approx 1 minute.")
