# AI Resume & Career Intelligence Platform

An evidence-grounded resume/job-description analysis platform for two audiences:

- **Job Seekers**: upload a resume and a job description to get a job-fit score,
  matched and missing skills with evidence, a learning roadmap and a mock
  interview with feedback, plus career intelligence across common roles, resume
  quality checks, an ATS/recruiter preview, and external evidence checks
  (GitHub, LinkedIn).
- **Job Providers / Recruiters**: set a job description once, then upload and
  compare many candidate resumes against it, using exactly the same analysis
  engine.

**Every score and claim is grounded in real extracted text.** Each quote shown is
copied from your documents; AI output whose quote cannot be found in them is
discarded, never shown. When AI is unavailable (no key, `DEMO_MODE`, or a
provider failure), every feature falls back to a clearly labelled non-AI
version instead of guessing.

Scores are an application-generated estimate, not an official ATS result or a
hiring decision.

## Contents

- [Requirements](#requirements)
- [Setup](#setup)
- [Running the app every day](#running-the-app-every-day)
- [Using the app](#using-the-app)
- [How the score works](#how-the-score-works)
- [Settings (backend\.env)](#settings-backendenv)
- [Updating to a new version](#updating-to-a-new-version)
- [Troubleshooting](#troubleshooting)
- [Privacy and your data](#privacy-and-your-data)
- [Tests](#tests)
- [Project structure](#project-structure)
- [Known limitations](#known-limitations)

## Requirements

Windows with PowerShell, plus:

- **Python 3.11 or newer** from python.org. Tick **"Add python.exe to PATH"**
  during installation.
- **Node.js 22 LTS or newer** from nodejs.org.
- **Git** from git-scm.com.
- Optional: a free **Google Gemini API key** from
  https://aistudio.google.com/apikey (no billing required) for the AI features.

## Setup

Do this once. All commands are PowerShell.

### 1. Get the code

```powershell
cd $HOME
git clone https://github.com/KrisJeffordImmanuvel/AI-Resume-Analyzer.git ai-resume-analyzer-app
cd ai-resume-analyzer-app
```

### 2. Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

- If PowerShell says *"running scripts is disabled on this system"*, run this
  once, then run `.\venv\Scripts\Activate.ps1` again:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
  ```
- After activating, the prompt starts with `(venv)`.
- `pip install` also downloads PyTorch (used only by the optional semantic
  matching). It is large and can take several minutes.
- Run `Copy-Item .env.example .env` **only once**. Running it again replaces
  your settings (including your key) with the blank template.

To turn on AI, open the settings file and paste your key after
`GOOGLE_API_KEY=` (no spaces, no quotes), then save:

```powershell
notepad .env
```

Check that AI works (one small real Gemini request):

```powershell
python check_ai.py
```

It ends with `All checks passed.` or explains what failed.

### 3. Frontend

Open a **second** PowerShell window:

```powershell
cd $HOME\ai-resume-analyzer-app\frontend
npm install
```

## Running the app every day

Use two PowerShell windows.

**Window 1: backend**

```powershell
cd $HOME\ai-resume-analyzer-app\backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

Wait for `Application startup complete.`

**Window 2: frontend**

```powershell
cd $HOME\ai-resume-analyzer-app\frontend
npm run dev
```

Open **http://localhost:5173**. The System status card should show
**Backend: Connected (v1.0.0)**, **Database: OK**, and **AI: Live** (with a key)
or **Fallback mode** (without one).

To stop, press **Ctrl+C** in each window.

## Using the app

The switch at the top chooses **Job Seeker** or **Job Provider** mode (the app
remembers your choice).

### Job Seeker mode

1. Choose your resume (PDF, DOCX or TXT, up to 5 MB).
2. Paste the job description, or upload it as a `.txt` file.
3. Click **Analyze**. With AI on, this can take up to a minute.

Past analyses appear under **Recent analyses**: **Open** shows one again;
the bin icon deletes it permanently.

The results have seven tabs:

| Tab | What it shows |
|---|---|
| **Fit report** | Job-fit score, priority breakdown, matched and missing skills with highlighted quotes from both documents, the resume profile (experience, education), other resume skills |
| **Learning roadmap** | One entry per missing skill (and per skill with only half-credit evidence): study steps, a project idea and a YouTube search link. The link is always built by the app, never written by AI |
| **Mock interview** | 6–8 questions, each showing the resume or job-description line it is based on. Type an answer and click **Get feedback** for strengths, improvements and one follow-up question |
| **Resume quality** | Checks for each bullet (numbers, action verbs, length, first person, filler) and a rewrite workspace with before/after. Rewrites that add a number or skill not in your resume are rejected; unknown figures become `[placeholders]` |
| **ATS view** | The exact text the app extracted, contact details and headings found, a keyword match against the job description, and a heuristic "6-second scan" of the top of page one |
| **Career** | A radar chart and table of fit across 10 common roles (same scoring engine), and a timeline built only from dated entries in your resume |
| **Evidence** | GitHub check (your public repos that support your resume skills, with links), LinkedIn consistency check (paste your profile's Experience section; nothing is fetched from LinkedIn), and a fairness scan of the job description's wording and of personal details on your resume |

### Job Provider mode

1. Click **Job Provider**.
2. Create a job: paste the job description (or upload a `.txt`) and optionally
   give it a title. Saved jobs can be picked again from the dropdown.
3. Under **Add candidates**, choose up to 10 resumes at a time and click
   **Add candidates**. Each resume is analysed with exactly the same engine as
   Job Seeker mode. A file that cannot be read, or a resume already in the
   comparison, is reported without stopping the others.
4. **Ranking**: candidates by fit score, with the required skills each one is
   missing. **Report** opens that candidate's full seven-tab report; the bin icon
   removes them from the comparison.
5. **Skill matrix**: each job skill against each candidate: ✓ Named,
   ½ Related, ✗ Missing. Hover a cell to see the resume line behind it.
6. **Blind review** hides file names and shows Candidate A, B, C… instead.

### Try it with the sample files

The `samples` folder has fictional resumes and a job description.

- **Job Seeker**: `samples\sample_resume.txt` with
  `samples\sample_job_description.txt` gives **69/100** without AI: 8 matched
  skills, 5 missing, 18 others. With AI the score can be higher, because
  AI-inferred evidence (e.g. GitHub Actions for CI/CD) earns half credit.
- **Job Provider**: create a job from `sample_job_description.txt` and add
  `sample_resume.txt`, `sample_resume_devops.txt` and
  `sample_resume_frontend.txt`. Without AI they rank **69, 59 and 24**.

## How the score works

- Each skill in the job description gets a priority from where it appears:
  **Required** (weight 3) under headings like "Requirements" or "Must have";
  **Nice to have** (weight 1) under "Preferred", "Nice to have", "Bonus" or on
  lines saying "is a plus"; **Mentioned** (weight 2) everywhere else.
- Skills are recognised from a curated list of 375 skills
  (`backend\data\skills.json`). Ambiguous words are handled carefully: "react
  to incidents" is not React, "R&D" is not R, and text inside links and email
  addresses never counts.
- **Score = matched weight ÷ total weight × 100.**
- Match types:
  - **Exact** (full credit): both documents use the same wording.
  - **Literal** (full credit): same skill, different wording ("JS" and "JavaScript").
  - **AI-inferred** (half credit): AI judged a resume line to show the skill
    (e.g. "deployed with GitHub Actions" for CI/CD); the line is verified.
  - **Semantic** (half credit, off by default): the most similar resume line by
    local embeddings.
- AI output is checked, never trusted as-is: items whose quotes are not in the
  resume are discarded (a notice tells you how many), and titles, employers or
  dates not in their quote are removed.
- If the job description has no recognisable skills, no score is given.

## Settings (backend\.env)

Edit with `notepad .env` in the `backend` folder, then **restart the backend**
(Ctrl+C, then `uvicorn main:app --reload`). The backend reads `.env` only when
it starts.

| Setting | Default | What it does |
|---|---|---|
| `GOOGLE_API_KEY` | *(blank)* | Gemini key. Blank means non-AI fallback mode |
| `DEMO_MODE` | `false` | `true` forces fallback mode even with a key |
| `GEMINI_MODEL` | `gemini-3.6-flash` | Main Gemini model |
| `GEMINI_FALLBACK_MODELS` | *(none)* | Comma-separated backup models, tried when the main one is overloaded (503) or rate-limited (429). `python check_ai.py --models` suggests them |
| `AI_TIMEOUT_SECONDS` | `60` | How long to wait for an AI answer before falling back |
| `SEMANTIC_MATCHING` | `false` | `true` turns on local semantic matching (see [Known limitations](#known-limitations)) |
| `SEMANTIC_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model for semantic matching |
| `SEMANTIC_THRESHOLD` | `0.6` | Minimum similarity (0–1) for a semantic match |
| `GITHUB_TOKEN` | *(blank)* | Optional token with no scopes; raises the GitHub check's limit from 60 to 5,000 requests per hour |
| `DATABASE_URL` | `backend\app.db` | Where analyses are stored (SQLite) |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Web addresses allowed to call the backend |

The frontend needs no settings unless the backend runs somewhere other than
`http://localhost:8000`. In that case copy `frontend\.env.example` to
`frontend\.env` and set `VITE_API_BASE_URL`.

### Checking AI

```powershell
python check_ai.py            # key, model, one tiny request; semantic model if enabled
python check_ai.py --models   # list the Gemini models your key can use and ping each
```

## Updating to a new version

Stop the backend and frontend (Ctrl+C), then:

```powershell
cd $HOME\ai-resume-analyzer-app
git checkout main
git pull
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..\frontend
npm install
```

Then start both again. Your `backend\.env`, `backend\app.db`, `venv` and
`node_modules` are not touched by updates; new database tables are added
automatically.

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| `Error loading ASGI app. Could not import module "main"` | uvicorn was started outside the `backend` folder. Run `cd $HOME\ai-resume-analyzer-app\backend` first |
| `python: can't open file ...check_ai.py` | Same: run it from the `backend` folder |
| Prompt does not start with `(venv)` | Run `.\venv\Scripts\Activate.ps1` in the `backend` folder |
| "running scripts is disabled on this system" | Run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once |
| Page says **Backend: Not reachable** | The backend is not running. Start it in window 1, then click **Recheck** |
| You changed `.env` but nothing changed | Restart the backend (Ctrl+C, then `uvicorn main:app --reload`) |
| AI shows **Fallback mode** although you set a key | Check the key line with `[bool](Select-String -Path .env -Pattern '^GOOGLE_API_KEY=\S')` (prints `True` without showing the key), then restart the backend. Make sure only **one** backend window is running: an old one can keep answering on port 8000 |
| `404 NOT_FOUND ... model is no longer available` | Set `GEMINI_MODEL` to a model from `python check_ai.py --models` |
| `503 UNAVAILABLE ... high demand` | Google is busy. The app retries and then falls back; add backups with `GEMINI_FALLBACK_MODELS` |
| `notepad .env` asks to create a new file | You are in the wrong folder; the settings file is `backend\.env` |
| `git pull` says "Already up to date" but a new version was announced | The pull request has not been merged on GitHub yet, or you are not on `main` (`git checkout main`) |
| ATS view says contact details are missing | The extracted text (shown in the same tab) has no email/phone. If your file shows them, they may be in an image or text box that software cannot read |
| A PDF gives "No text could be extracted" | It is probably a scanned image. Export it from Word as a text-based PDF or upload the DOCX |
| `DLL load failed` when semantic matching loads | Install the latest Microsoft Visual C++ Redistributable (x64), or leave `SEMANTIC_MATCHING=false` |
| A tab says "This section could not be displayed" | A display error in that tab only. Click **Try again**; details are in the browser console (F12) |
| An error mentions "the backend window" | The backend hit an unexpected error; the details are printed in window 1. Restart the backend and try again |

## Privacy and your data

- Everything is stored locally in `backend\app.db` on your computer. Delete an
  analysis from **Recent analyses** to remove its resume text and everything
  generated from it, or delete `app.db` to reset everything (it is recreated on
  the next start).
- With a Gemini key, resume and job-description text is sent to Google's Gemini
  API for the AI features. Without a key (or with `DEMO_MODE=true`), nothing is
  sent to any AI service.
- The GitHub check sends only the username you enter to GitHub's public API.
  Nothing is ever fetched from LinkedIn; you paste the text yourself.
- `backend\.env` (your key) and `backend\app.db` are ignored by git and are
  never committed.
- Scores never use age, gender, marital status, religion, nationality, family
  details, photos or health information.

## Tests

```powershell
cd $HOME\ai-resume-analyzer-app\backend
.\venv\Scripts\Activate.ps1
pytest
```

The suite (215 tests) never makes live AI or network calls. Gemini, the
embedding model and GitHub are replaced by stand-ins, so the tests are fast,
deterministic and free to run. To check that the frontend builds:

```powershell
cd $HOME\ai-resume-analyzer-app\frontend
npm run build
```

## Project structure

```
backend\
  main.py               FastAPI app, /health, error handling
  config.py             settings from backend\.env
  parsing.py            PDF / DOCX / TXT text extraction and limits
  skills.py             skill recognition against data\skills.json
  matching.py           the scoring engine (used by every mode)
  analysis_service.py   one full analysis: AI or fallback profile + matching
  ai_provider.py        Gemini wrapper (retries, backup models, safe errors)
  evidence.py           verification that quotes exist in the source text
  profile_extraction.py resume profile (AI with verified quotes, or pattern-based)
  semantic.py           optional Sentence Transformers matching
  roadmap.py, interview.py, resume_quality.py, ats.py, career.py
  github_check.py, linkedin_check.py, fairness.py, comparison.py
  routers\              API endpoints
  data\                 skills.json (375 skills), role_profiles.json (10 roles)
  check_ai.py           manual check of Gemini and the semantic model
  tests\                pytest suite
frontend\src\           React + Vite user interface
samples\                fictional resumes and a job description
PROJECT_SPEC.md         feature map, derived requirements and build phases
```

## Known limitations

- **Skill recognition uses a fixed list** of 375 skills. Skills not on the list
  are only picked up by AI (as profile skills). Company names can occasionally
  match a skill (e.g. "Example Fintech Pvt Ltd" counts as FinTech).
- **Semantic matching is off by default.** In calibration on the sample files
  the default model matched every skill the resume does not name to a wrong
  line (best wrong match 0.41, e.g. Terraform to a Docker line) while true
  matches scored 0.36–0.60, so no threshold separates them. AI-inferred evidence
  covers the useful case with verified quotes.
- **The ATS view is a heuristic preview**, not a reproduction of any specific
  applicant-tracking product.
- **The GitHub check sees public repositories only**; "not seen" does not mean a
  skill is untrue.
- **The LinkedIn check compares two documents you provide**; it does not verify
  either one.
- **Fairness checks are word lists**: a flag is a prompt to review, not proof of
  bias, and no list is complete.
- Job descriptions are accepted as `.txt` files or pasted text only.
