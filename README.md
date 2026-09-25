# AI Resume & Career Intelligence Platform

An evidence-grounded resume/job-description analysis platform for job seekers
and recruiters. See [PROJECT_SPEC.md](PROJECT_SPEC.md) for the full feature map
and build plan.

> **Status: Phase 7.** Two modes, switched at the top of the page.
> **Job Seeker**: upload a resume (PDF, DOCX or TXT) and a job description
> (pasted text or a .txt file) for an evidence-backed fit report with seven
> tabs: Fit report, Learning roadmap, Mock interview, Resume quality, ATS view,
> Career and Evidence. **Job Provider**: save a job description once, upload
> several candidate resumes, and compare them in a ranking and a skill matrix,
> using exactly the same analysis engine. Every quote shown is copied from the
> source documents, and AI output that cannot be found there is discarded.

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

The `samples` folder has fictional resumes and a job description.

For **Job Seeker** mode:

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

## Career intelligence

- **Fit across common roles**: a radar chart and a sorted table of fit against
  10 generic role profiles (`backend\data\role_profiles.json`: Backend,
  Frontend, Full-stack, Data analyst, Data engineer, ML engineer, DevOps/SRE,
  Mobile, QA/Test, Product manager). Each profile is scored by the same engine
  as the job-fit score (required skills x3, nice-to-have x1), including verified
  AI-inferred skills. Hover a point for details; the table lists missing
  required skills per role. You can edit the profiles file to add roles; skill
  names must match `skills.json` (a test checks this).
- **Career timeline**: roles and education in date order, newest first, built
  only from entries whose dates can be read ("Jan 2020 - Mar 2022",
  "2022 - Present", "2020"). Each shows its resume quote and duration. Gaps of
  6 months or more between roles are noted; year-only dates are flagged as
  approximate. Entries without dates are left out, never estimated.

## External evidence

- **GitHub check**: enter a username (pre-filled when the resume links to
  github.com/you). The app reads public data from GitHub's API; only the
  username is sent. For each technical skill on the resume it shows public,
  non-fork repos that support it, either by the repo's main language or by the
  repo's own topics/description, with links. Skills not seen are listed as
  "not seen in public repos", which is normal for private or company work.
  Anonymous requests are limited to 60 per hour; set `GITHUB_TOKEN` in
  `backend\.env` (a token with no scopes) for 5,000.
- **LinkedIn consistency check**: nothing is fetched from LinkedIn. Copy your
  profile's Experience (and Skills) section and paste it. Roles are matched
  with the resume and date differences are shown with both texts quoted;
  roles and skills that appear on only one side are listed. It checks that
  the two documents agree, not that either is true.
- **Fairness scan** (rule-based): flags job-description wording that can put
  some applicants off (gender-coded words such as "rockstar", age-coded words
  such as "young" or "digital native", exclusionary requirements such as
  "native English speaker") and personal details on the resume that are not
  needed to judge skills (date of birth, marital status, religion, family
  details, photo). Each flag quotes the exact line. The app's scores never use
  any of these details.

## Job Provider mode

1. Click **Job Provider** at the top. (The app remembers the last mode.)
2. Create a job: paste the job description (or upload a .txt) and optionally
   give it a title; it defaults to the description's first line. Saved jobs
   can be chosen again from the dropdown later.
3. Under **Add candidates**, choose up to 10 resumes at a time (PDF, DOCX or
   TXT) and click **Add candidates**. Each resume is analysed with exactly the
   same engine as Job Seeker mode. A file that cannot be read, or a resume
   already in the comparison, is reported without stopping the others.
4. **Ranking**: candidates by fit score, with required skills matched and the
   required skills each one is missing. **Report** opens that candidate's full
   report (all seven tabs); the bin icon removes a candidate from the
   comparison (the analysis itself is kept).
5. **Skill matrix**: every job skill against every candidate: Named (named in
   the resume), Related (½ credit, e.g. AI-inferred) or Missing. Hover a cell
   to see the resume line behind it.
6. **Blind review** hides file names and shows Candidate A, B, C… (letters
   follow upload order, so they do not change when the ranking does).

To try it, create a job from `samples\sample_job_description.txt` and add
`sample_resume.txt`, `sample_resume_devops.txt` and
`sample_resume_frontend.txt`. They rank 69, 59 and 24 without AI.

Scores support human review; they are not a hiring decision.

## Notes

- `backend\app.db` (SQLite) and `backend\.env` are gitignored and local-only —
  delete `app.db` any time to reset to a clean database (it's recreated
  automatically on the next backend start).
- Scores are explicitly labeled as an application-generated estimate, not an
  official ATS or hiring decision.
