# AI Resume & Career Intelligence Platform

An evidence-grounded resume/job-description analysis platform for job seekers
and recruiters. See [PROJECT_SPEC.md](PROJECT_SPEC.md) for the full feature map
and build plan.

> **Status: Phase 4.** Upload a resume (PDF, DOCX or TXT) and a job description
> (pasted text or a .txt file) to get a job-fit score with matched and missing
> skills, each backed by a verbatim quote. Skills are matched against a curated
> list of 375 skills (`backend\data\skills.json`). With a Gemini key, AI also
> extracts a resume profile; every AI quote is checked against the resume and
> dropped if it is not there. Results have five tabs: **Fit report**,
> **Learning roadmap**, **Mock interview**, **Resume quality** (bullet checks and
> a rewrite workspace that never adds facts) and **ATS view** (raw parse
> preview, keyword match and a heuristic 6-second scan).

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

The first `pip install` also downloads PyTorch (for the optional semantic
matching), which is large (a few hundred MB) and can take several minutes.

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

This makes one small real Gemini request (if a key is set) and, if semantic
matching is on, loads the semantic model (downloading ~90 MB the first time)
and prints a calibration table. It ends with
`All checks passed.` or explains what failed.

If Gemini often answers `503 UNAVAILABLE` ("high demand"), add backup models:

```powershell
python check_ai.py --models
```

This lists the Gemini models your key can use, sends each one tiny request,
and prints suggested `GEMINI_FALLBACK_MODELS=...` line(s) for `backend\.env`.
When the main model is still busy after retries, the app tries the backups in
order; results name the model that actually answered. Restart uvicorn after changing
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
   With a Gemini key, the score can be higher: AI-inferred evidence (for
   example GitHub Actions for CI/CD) earns half credit.

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
  - **Semantic** (half credit, off by default): the most similar resume line by
    local embeddings, at or above `SEMANTIC_THRESHOLD` (default 0.6). The
    similarity is shown.
- Why semantic matching is off by default: on the sample files, the default
  model (all-MiniLM-L6-v2) matched every skill the resume does not name to a
  wrong line (best wrong match 0.41, e.g. Terraform to a Docker line), while
  true matches scored 0.36–0.60. No threshold separates them, so it would
  either award wrong credit or never fire. AI-inferred evidence covers the
  useful case (e.g. GitHub Actions for CI/CD) with a verified quote.
- AI output is never trusted as-is: items whose quotes are not in the resume
  are discarded, and titles/employers/dates not in their quote are removed.
- If AI or the semantic model is unavailable, the result says so and uses the
  pattern-based fallback; the analysis never fails because of it.
- Text inside links and email addresses is never counted as evidence.
- If the job description has no recognizable skills, no score is given.

## Learning roadmap and mock interview

- **Roadmap**: one entry per missing skill ("Learn") and per skill with only
  half-credit evidence ("Strengthen"), Required first. Each has study steps, a
  project idea and a YouTube search link. The link is always built by the app
  from the skill name, never written by AI. With AI, Gemini writes the steps
  (labelled AI-generated); without it, category templates are used.
- **Questions**: questions about your skills, gaps or experience always show
  the resume or job-description line they are based on. AI questions whose
  line cannot be found in either document are discarded, so no question rests
  on an invented premise. Behavioral questions need no source line.
- **Feedback**: type an answer and click **Get feedback**. With AI you get a
  1-5 rating (an estimate), strengths, improvements and one follow-up question;
  any words it quotes from your answer are checked against what you typed.
  Without AI you get rule-based checks (length, your own actions, numbers,
  outcome, mentioning the skill) and no rating.
- Roadmaps and question sets are saved per analysis; **Regenerate** / **New
  questions** makes a fresh one. Answers and feedback are saved too.

## Resume quality and ATS view

- **Bullet checks** (rule-based, no AI): each bullet (a line starting with -, *,
  • or 1.) is checked for a number (years like 2021 do not count; written
  numbers like "two" do), a strong opening verb vs a weak opener such as
  "Responsible for", length, first-person words and filler phrases.
- **Rewrite workspace**: click **Rewrite** on a bullet (or paste one) and
  **Suggest rewrites** for a before/after view. AI suggestions that add a number
  or a skill not in your bullet or resume are rejected (a notice says why); gaps
  are shown as highlighted [placeholders] for your real figures. Without AI, a
  rule-based rewrite fixes weak openers and adds a result placeholder.
- **ATS view** (heuristic, not any specific ATS product):
  - *Raw parse preview*: the exact text the app extracted, word count, detected
    headings, contact details found, and warnings (thin text, missing standard
    headings, table-like lines).
  - *Keyword match*: each job-description skill (and repeated or title terms)
    with whether the exact wording is in the resume and whether the skill is
    there under different wording (e.g. "JS" for "JavaScript").
  - *6-second scan*: checks on the top of page one: headline vs job title,
    job skills visible early, most recent role, and numbers in achievements.

## Notes

- `backend\app.db` (SQLite) and `backend\.env` are gitignored and local-only —
  delete `app.db` any time to reset to a clean database (it's recreated
  automatically on the next backend start).
- Scores are explicitly labeled as an application-generated estimate, not an
  official ATS or hiring decision.
