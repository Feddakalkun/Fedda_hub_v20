# Hugging Face Token Setup (for WAN/LTX Models)

## Why do I need this?

Some AI models (like WAN for Lipsync) are hosted in **gated repositories** on Hugging Face that require authentication. Without a token, downloads will fail with a 1-byte file.

## Quick Setup (3 steps)

### 1. Get your Hugging Face token

1. Go to: **https://huggingface.co/settings/tokens**
2. Click **"New token"**
3. Name: `FEDDA` (or whatever you like)
4. Type: **Read** (default)
5. Click **"Generate"**
6. **Copy the token** (starts with `hf_...`)

### 2. Accept model license agreements

For WAN models, you may need to accept the license:
- Visit: **https://huggingface.co/Comfy-Org/WAN-22-repackaged**
- Click **"Agree and access repository"**

### 3. Set the environment variable

**On Windows:**

```cmd
# Temporary (until you close the terminal):
set HF_TOKEN=hf_YourTokenHere

# Permanent (recommended):
setx HF_TOKEN "hf_YourTokenHere"
```

**On Linux/Docker/RunPod:**

```bash
# Add to your .env file or set directly:
export HF_TOKEN=hf_YourTokenHere

# Or in Docker:
docker run -e HF_TOKEN=hf_YourTokenHere ...
```

**In RunPod:**
1. Go to your pod settings
2. Add environment variable: `HF_TOKEN=hf_YourTokenHere`
3. Restart the pod

### 4. Restart and download

1. **Restart your FEDDA app** (close and reopen `run.bat`)
2. Go to **Video → Lipsync**
3. Click **"Download All Models"**
4. The WAN model should now download correctly! ✅

## Troubleshooting

**Token not working?**
- Make sure you copied the entire token (starts with `hf_`)
- Check you accepted the model license on Hugging Face
- Restart the backend after setting the token

**Still getting 1-byte files?**
- Backend logs should show: `[DOWNLOAD] Using HF_TOKEN for authentication`
- If you don't see this, the token isn't set correctly

**Check if token is set:**
```cmd
echo %HF_TOKEN%
```

Should print: `hf_YourTokenHere` (not blank)

## Security Note

⚠️ **Keep your token private!** Don't share it or commit it to GitHub.
- The token gives read access to your Hugging Face account
- Store it securely as an environment variable
- Never hardcode it in your code

---

**Need help?** Check logs in Console Logs page or terminal output for detailed error messages.
