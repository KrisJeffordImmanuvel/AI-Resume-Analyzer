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

### 2. Run the setup script

```powershell
.\setup.ps1
```

It creates the Python environment (`backend\venv`), installs the Python and
Node.js packages, creates your settings file `backend\.env` from the template,
and builds the web page. The first run downloads PyTorch (used only by the
optional semantic matching); it is large and can take several minutes.

- If PowerShell says *"running scripts is disabled on this system"*, run this
  once, then run `.\setup.ps1` again:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
  ```
- `setup.ps1` is safe to run again at any time. It never overwrites an existing
  `backend\.env`, so your key is kept.

### 3. Optional: turn on AI

Open the settings file and paste your key after `GOOGLE_API_KEY=` (no spaces,
no quotes), then save:

```powershell
notepad backend\.env
```

Check that AI works (one small real Gemini request):

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python check_ai.py
cd ..
```

It ends with `All checks passed.` or explains what failed.

## Running the app every day

In PowerShell, from the project folder:

```powershell
cd $HOME\ai-resume-analyzer-app
.\start.ps1
```

Your browser opens **http://localhost:8000** once the app is ready. Keep this
one window open while you use the app; press **Ctrl+C** in it to stop.

The small label at the top right of the page shows the app's state. Click it
for details:

- **AI on**: AI features are working.
- **AI off**: no key is set (or `DEMO_MODE=true`). Everything still works with
  the built-in rules.
- **Server offline**: the PowerShell window was closed or stopped. Run
  `.\start.ps1` again; the page reconnects by itself.

Options: `.\start.ps1 -Port 8001` uses another port; `.\start.ps1 -NoBrowser`
does not open the browser. After an update, `start.ps1` rebuilds the web page
automatically the first time.

### Development mode (only for changing the code)

Instant reload while editing uses two windows:

```powershell
# Window 1
cd $HOME\ai-resume-analyzer-app\backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

```powershell
# Window 2
cd $HOME\ai-resume-analyzer-app\frontend
npm run dev
```

Then open **http://localhost:5173**.

## Using the app

The switch at the top chooses **Job Seeker** or **Job Provider** mode (the app
remembers your choice).

### Job Seeker mode

New here? Click **Try with sample data** to analyze the fictional sample resume
and job description straight away.

1. Choose your resume (PDF, DOCX or TXT, up to 5 MB).
2. Paste the job description, or upload it as a `.txt` file.
3. Click **Analyze**. While it works you see what it is doing and for how
   long; **Cancel** stops it (nothing is saved). With AI on it usually takes
   under 30 seconds, and never longer than `AI_TIMEOUT_SECONDS` (90 by
   default): after that the app uses its built-in rules instead. The page
   scrolls to the results when they are ready.

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
   **Delete job** removes the selected job and permanently deletes its
   candidates' resumes and reports (you are asked to confirm first).
3. Under **Add candidates**, choose up to 10 resumes at a time and click
   **Add candidates**. Each resume is analysed with exactly the same engine as
   Job Seeker mode. Resumes are analysed one at a time ("Analysing resume 2
   of 5") and appear in the ranking as each finishes; **Cancel the rest**
   stops after the current one (which is then not added). A file that cannot
   be read, or a resume already in the comparison, is reported without
   stopping the others.
4. **Ranking**: candidates by fit score, with the required skills each one is
   missing. **Report** opens that candidate's full seven-tab report; the bin icon
   removes them from the comparison.
5. **Skill matrix**: each job skill against each candidate: ✓ Named (full
   credit), − Related (half credit), ✗ Missing. Click a Named or Related cell
   (or press Enter on it) to see the resume line behind it.
6. **Blind review** hides file names and shows Candidate A, B, C… instead.

### Keyboard and screen readers

- Everything works with the keyboard. **Tab** moves between controls (with a
  visible focus ring); in a row of tabs (mode, report sections, Paste/Upload),
  **Left/Right**, **Home** and **End** switch tabs.
- Screen readers announce when an analysis starts and finishes (with the
  score), and when candidates are added in Job Provider mode.

### Try it with the sample files

The `samples` folder has fictional resumes and a job description.

- **Job Seeker**: **Try with sample data** (or `samples\sample_resume.txt` with
  `samples\sample_job_description.txt`) gives **69/100** without AI: 8 matched
  skills, 5 missing, 18 others. With AI the score can be higher, because
  AI-inferred evidence (e.g. GitHub Actions for CI/CD) earns half credit.
- **Job Provider**: create a job from `sample_job_description.txt` and add
  `sample_resume.txt`, `sample_resume_devops.txt` and
  `sample_resume_frontend.txt`. Without AI they rank **69, 59 and 24**.

## How the score works

- Each skill in the job description gets a priority from where it appears:
  **Required** (3 points) under headings like "Requirements" or "Must have";
  **Nice to have** (1 point) under "Preferred", "Nice to have", "Bonus" or on
  lines saying "is a plus"; **Mentioned** (2 points) everywhere else.
- Skills are recognised from a curated list of 375 skills
  (`backend\data\skills.json`). Ambiguous words are handled carefully: "react
  to incidents" is not React, "R&D" is not R, and text inside links and email
  addresses never counts.
- **Score = points for skills your resume shows ÷ all points × 100.**
  The report explains this under **How is the score calculated?**
- Match labels (explained in the report under **What do the labels mean?**):
  - **Same wording** (full credit): both documents use the same words.
  - **Other wording** (full credit): same skill, written differently ("JS" and
    "JavaScript").
  - **Related (AI)** (half credit): AI judged a resume line to show the skill
    (e.g. "deployed with GitHub Actions" for CI/CD); the line is checked to be in
    your resume.
  - **Similar meaning** (half credit, off by default): the resume line closest in
    meaning, found by local semantic matching.
- AI output is checked, never trusted as-is: items whose quotes are not in the
  resume are discarded (a notice tells you how many), and titles, employers or
  dates not in their quote are removed.
- If the job description has no recognisable skills, no score is given.

## Settings (backend\.env)

Edit with `notepad backend\.env` from the project folder, then **restart the
app** (Ctrl+C in its window, then `.\start.ps1`). Settings are read only when
the app starts.

| Setting | Default | What it does |
|---|---|---|
| `GOOGLE_API_KEY` | *(blank)* | Gemini key. Blank means non-AI fallback mode |
| `DEMO_MODE` | `false` | `true` forces fallback mode even with a key |
| `GEMINI_MODEL` | `gemini-3.6-flash` | Main Gemini model |
| `GEMINI_FALLBACK_MODELS` | *(none)* | Comma-separated backup models, tried when the main one is overloaded (503) or rate-limited (429). `python check_ai.py --models` suggests them |
| `AI_TIMEOUT_SECONDS` | `90` | Most seconds to wait for AI, all retries and backup models included, before using the built-in rules (10–240) |
| `SEMANTIC_MATCHING` | `false` | `true` turns on local semantic matching (see [Known limitations](#known-limitations)) |
| `SEMANTIC_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model for semantic matching |
| `SEMANTIC_THRESHOLD` | `0.6` | Minimum similarity (0–1) for a semantic match |
| `GITHUB_TOKEN` | *(blank)* | Optional token with no scopes; raises the GitHub check's limit from 60 to 5,000 requests per hour |
| `DATABASE_URL` | `backend\app.db` | Where analyses are stored (SQLite) |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Web addresses allowed to call the backend (development mode only) |

The frontend needs no settings. In development mode only, if the backend runs
somewhere other than `http://localhost:8000`, copy `frontend\.env.example` to
`frontend\.env` and set `VITE_API_BASE_URL`.

### Checking AI

From the `backend` folder, with `.\venv\Scripts\Activate.ps1` run first:

```powershell
python check_ai.py            # key, model, one tiny request; semantic model if enabled
python check_ai.py --models   # list the Gemini models your key can use and ping each
```

## Updating to a new version

Stop the app (Ctrl+C in its window), then:

```powershell
cd $HOME\ai-resume-analyzer-app
git checkout main
git pull
.\setup.ps1
.\start.ps1
```

Your `backend\.env` and `backend\app.db` are not touched by updates; new
database tables are added automatically.

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| "running scripts is disabled on this system" | Run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once |
| "setup.ps1 is not digitally signed" | The files came from a downloaded ZIP. Run `Unblock-File .\setup.ps1, .\start.ps1` once |
| "The app is not set up yet" | Run `.\setup.ps1` first |
| "Port 8000 is already in use" | The app is already running in another window. Use that window (or open http://localhost:8000), or close it and run `.\start.ps1` again |
| The page says "The app's web page has not been built yet" | The server was started without `start.ps1`. Stop it and run `.\start.ps1`, which builds the page |
| The label at the top shows **Server offline** | The app's PowerShell window was closed or stopped. Run `.\start.ps1` again |
| You changed `.env` but nothing changed | Restart the app (Ctrl+C in its window, then `.\start.ps1`) |
| The label shows **AI off** although you set a key | Check the key line with `[bool](Select-String -Path backend\.env -Pattern '^GOOGLE_API_KEY=\S')` (prints `True` without showing the key), then restart the app. Make sure only **one** app window is running |
| `python: can't open file ...check_ai.py` | Run it from the `backend` folder, after `.\venv\Scripts\Activate.ps1` |
| `404 NOT_FOUND ... model is no longer available` | Set `GEMINI_MODEL` to a model from `python check_ai.py --models` |
| `503 UNAVAILABLE ... high demand` | Google is busy. The app retries and then falls back; add backups with `GEMINI_FALLBACK_MODELS` |
| A notice says "no answer within 90 seconds" | Gemini was too slow this time, so the built-in rules were used. Try again later, or raise `AI_TIMEOUT_SECONDS` (up to 240) |
| `notepad .env` asks to create a new file | You are in the wrong folder; the settings file is `backend\.env` |
| `git pull` says "Already up to date" but a new version was announced | The pull request has not been merged on GitHub yet, or you are not on `main` (`git checkout main`) |
| ATS view says contact details are missing | The extracted text (shown in the same tab) has no email/phone. If your file shows them, they may be in an image or text box that software cannot read |
| A PDF gives "No text could be extracted" | It is probably a scanned image. Export it from Word as a text-based PDF or upload the DOCX |
| `DLL load failed` when semantic matching loads | Install the latest Microsoft Visual C++ Redistributable (x64), or leave `SEMANTIC_MATCHING=false` |
| A tab says "This section could not be displayed" | A display error in that tab only. Click **Try again**; details are in the browser console (F12) |
| An error mentions "the app's PowerShell window" | The server hit an unexpected error; the details are printed in that window. Try again, or restart the app |

## Privacy and your data

- Everything is stored locally in `backend\app.db` on your computer. Delete an
  analysis from **Recent analyses** to remove its resume text and everything
  generated from it, use **Delete job** in Job Provider mode to remove a job
  and its candidates, or delete `app.db` to reset everything (it is recreated on
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

The suite (234 tests) never makes live AI or network calls. Gemini, the
embedding model and GitHub are replaced by stand-ins, so the tests are fast,
deterministic and free to run. To check that the frontend builds:

```powershell
cd $HOME\ai-resume-analyzer-app\frontend
npm run build
```

## Project structure

```
backend\
  main.py               FastAPI app, /health, error handling, serves the built page
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
setup.ps1               one-time setup (safe to run again)
start.ps1               starts the app at http://localhost:8000
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
