# Auto Docker Build Setup

This workflow automatically triggers a Docker image rebuild when you push changes to the main repo.

## One-Time Setup

1. Create a GitHub Personal Access Token (PAT):
   - Go to: https://github.com/settings/tokens/new
   - Name: `Docker Repo Trigger`
   - Expiration: `No expiration` (or 1 year)
   - Scopes: Select **only** `repo` (Full control of private repositories)
   - Click `Generate token`
   - **Copy the token** (you won't see it again!)

2. Add the token as a secret to THIS repo (comfyuifeddafront):
   - Go to: https://github.com/Feddakalkun/comfyuifeddafront/settings/secrets/actions
   - Click `New repository secret`
   - Name: `DOCKER_REPO_PAT`
   - Value: Paste the token you copied
   - Click `Add secret`

## How It Works

1. You make changes in `comfyuifeddafrontclean` (local dev)
2. Test locally with `start.bat`
3. Push to GitHub main branch
4. **GitHub Actions automatically**:
   - Detects changes in frontend/backend/config/assets
   - Triggers Docker repo to rebuild
   - New image pushed to Docker Hub (~3-4 min)
5. RunPod users get updated image on next deployment

## Manual Trigger (if needed)

If auto-trigger fails, manually trigger Docker build:
```bash
cd /path/to/your/comfyuifeddafront
git commit --allow-empty -m "Trigger rebuild"
git push
```
