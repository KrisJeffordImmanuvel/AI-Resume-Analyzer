# AI Resume & Career Intelligence Platform

An evidence-grounded resume/job-description analysis platform for job seekers
and recruiters. See [PROJECT_SPEC.md](PROJECT_SPEC.md) for the full feature map
and build plan.

> **Status: Phase 2.** Upload a resume (PDF, DOCX or TXT) and a job description
> (pasted text or a .txt file) to get a job-fit score with matched and missing
> skills, each backed by a verbatim quote. Skills are matched against a curated
> list of 375 skills (`backend\data\skills.json`). With a Gemini key, AI also
> extracts a resume profile (experience, education, skills); every AI quote is
> checked against the resume and dropped if it is not there. Local semantic
> matching (Sentence Transformers) finds related evidence for skills the resume
> does not name.

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

The first `pip install` also downloads PyTorch for semantic matching, which is
large (a few hundred MB) and can take several minutes.

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

### Check AI and semantic matching

With the venv active, from the `backend` folder:

```powershell
python check_ai.py
```

This makes one small real Gemini request (if a key is set) and loads the
semantic model, downloading it (~90 MB) the first time. It ends with
`All checks passed.` or explains what failed. Restart uvicorn after changing
`backend\.env`; the backend reads it only at startup.

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
3. Click **Analyze**. Without AI or semantic matching you should see a score of
   **69/100**, 8 matched skills, 5 missing skills and 18 other resume skills.
   With them on, the score can be higher: related evidence (for example GitHub
   Actions for CI/CD) earns half credit.

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
- Match types and credit:
  - **Exact** (full credit): both documents use the same wording.
  - **Literal** (full credit): same skill, different wording ("JS" and "JavaScript").
  - **AI-inferred** (half credit): AI judged a resume quote to show the skill
    (for example "deployed with GitHub Actions" for CI/CD). The quote is verified.
  - **Semantic** (half credit): the most similar resume line by local embeddings,
    at or above `SEMANTIC_THRESHOLD` (default 0.6). The similarity is shown.
- AI output is never trusted as-is: items whose quotes are not in the resume
  are discarded, and titles/employers/dates not in their quote are removed.
- If AI or the semantic model is unavailable, the result says so and uses the
  pattern-based fallback; the analysis never fails because of it.
- Text inside links and email addresses is never counted as evidence.
- If the job description has no recognizable skills, no score is given.

## Notes

- `backend\app.db` (SQLite) and `backend\.env` are gitignored and local-only —
  delete `app.db` any time to reset to a clean database (it's recreated
  automatically on the next backend start).
- Scores are explicitly labeled as an application-generated estimate, not an
  official ATS or hiring decision.
