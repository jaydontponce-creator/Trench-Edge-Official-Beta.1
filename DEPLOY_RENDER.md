# Deploy Trench Edge Beta on Render

## GitHub
1. Create a GitHub repository, for example `trench-edge-beta`.
2. Upload all files in this folder to the repository root.
3. Make sure the `backend` and `frontend` folders are visible at the top level.
4. Do NOT upload a `.env` file with real API keys.

## Render — easiest method
1. Sign in to Render and choose **New > Blueprint**.
2. Connect the GitHub repository.
3. Render will detect `render.yaml`.
4. Create the service.
5. When prompted for secret environment variables, enter:
   - `CFBD_API_KEY`
   - `ODDS_API_KEY`

## Render — manual method
Create **New > Web Service** and use:
- Name: `trench-edge-beta` (or another available name)
- Branch: `main`
- Runtime: `Python 3`
- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/api/v1/health`
- Plan: `Free`
- Auto-Deploy: `On`

Environment:
- `CFBD_API_KEY`
- `ODDS_API_KEY`

## Updating the public beta
Edit and test locally, then push your approved changes to the GitHub branch Render watches.
Render redeploys the same public URL automatically. You do not need a new URL.

## Local test
From the repository root:
```
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Then open `http://127.0.0.1:8000`.
