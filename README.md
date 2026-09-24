# AI Resume & Career Intelligence Platform

An evidence-grounded resume/job-description analysis platform for job seekers
and recruiters. See [PROJECT_SPEC.md](PROJECT_SPEC.md) for the full feature map
and build plan.

> **Status: Phase 1.** Upload a resume (PDF, DOCX or TXT) and a job description
> (pasted text or a .txt file) to get a job-fit score with matched and missing
> skills, each backed by a verbatim quote. Matching is deterministic (no AI yet)
> against a curated list of 375 skills in `backend\data\skills.json`.

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

### Try it with the sample files

The `samples` folder has a fictional resume and job description:

1. Under **Resume**, click **Choose File** and pick `samples\sample_resume.txt`.
2. Under **Job description**, click **Upload .txt** and pick
   `samples\sample_job_description.txt` (or paste its text into the box).
3. Click **Analyze**. You should see a score of **69/100**, 8 matched skills,
   5 missing skills and 18 other resume skills.

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

## How the score works

- Each skill in the job description gets a priority from the section it
  appears in: **Required** (weight 3) under headings like "Requirements" or
  "Must have"; **Nice to have** (weight 1) under "Preferred", "Nice to have",
  "Bonus" or on lines saying "is a plus"; **Mentioned** (weight 2) everywhere
  else.
- Score = matched weight ÷ total weight × 100.
- **Exact** means both documents use the same wording; **Literal** means the
  same skill in different wording (for example "JS" and "JavaScript").
- Text inside links and email addresses is never counted as evidence.
- If the job description has no recognizable skills, no score is given.

## Notes

- `backend\app.db` (SQLite) and `backend\.env` are gitignored and local-only —
  delete `app.db` any time to reset to a clean database (it's recreated
  automatically on the next backend start).
- Scores are explicitly labeled as an application-generated estimate, not an
  official ATS or hiring decision.
