# AI Resume & Career Intelligence Platform

An evidence-grounded resume/job-description analysis platform for job seekers
and recruiters. See [PROJECT_SPEC.md](PROJECT_SPEC.md) for the full feature map
and build plan.

> **Status: Phase 0 (skeleton).** The backend starts, creates its database and
> reports its AI status at `/health`. The frontend shows that status. No
> analysis features yet.

## Requirements (Windows)

- Python 3.11 or newer (from python.org, with "Add python.exe to PATH" ticked)
- Node.js 22 LTS or newer (from nodejs.org)
- PowerShell

All commands below are PowerShell, run from the repository folder.

## Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell refuses to run `Activate.ps1` ("running scripts is disabled on
this system"), run this once and then try activating again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Edit `backend\.env` (for example `notepad .env`) and fill in `GOOGLE_API_KEY`
(get one free, no billing required, at https://aistudio.google.com/apikey) to
enable live AI features. Leaving it blank, or setting `DEMO_MODE=true`, runs the
app fully in its deterministic fallback mode — useful for development without a
key.

```powershell
uvicorn main:app --reload
```

The API serves at `http://localhost:8000`; `/health` reports whether AI is
configured.

## Frontend

Open a **second** PowerShell window:

```powershell
cd frontend
npm install
Copy-Item .env.example .env   # only needed if the backend isn't on localhost:8000
npm run dev
```

Open `http://localhost:5173`.

To check that the frontend builds cleanly:

```powershell
npm run build
```

## Tests

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pytest
```

The test suite never makes live AI or network calls — every AI/network
dependency is mocked so tests are deterministic and free to run.

## Notes

- `backend\app.db` (SQLite) and `backend\.env` are gitignored and local-only —
  delete `app.db` any time to reset to a clean database (it's recreated
  automatically on the next backend start).
- Scores are explicitly labeled as an application-generated estimate, not an
  official ATS or hiring decision.
