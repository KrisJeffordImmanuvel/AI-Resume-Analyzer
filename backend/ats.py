"""ATS / recruiter view: what software and a skimming recruiter actually see.

All deterministic and heuristic. Nothing here claims to reproduce a specific
ATS product; the UI labels it as a preview.
"""

import re
from collections import Counter

from resume_quality import _metric, extract_bullets
from skills import _URL_OR_EMAIL, find_mentions, group_by_skill

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_CANDIDATE = re.compile(r"\+?\(?\d[\d\s().-]{7,}\d")


def _has_phone(text: str) -> bool:
    # 10-15 digits, so date ranges like "2020 - 2022" are not mistaken for a phone.
    return any(10 <= sum(ch.isdigit() for ch in m.group(0)) <= 15 for m in _PHONE_CANDIDATE.finditer(text))
_LINKEDIN = re.compile(r"linkedin\.com/in/[\w-]+", re.I)
_GITHUB = re.compile(r"github\.com/[\w-]+", re.I)
_HEADINGS = {
    "Summary": r"summary|profile|objective|about me",
    "Experience": r"(work |professional |relevant )?experience|employment( history)?|work history",
    "Education": r"education|academic background",
    "Skills": r"(technical |core )?skills|technologies|tech stack",
    "Projects": r"projects",
    "Certifications": r"certifications?|licenses",
}
_WORD = re.compile(r"[A-Za-z][A-Za-z+#./-]*[A-Za-z+#]|[A-Za-z]")
STOPWORDS = set("""
a about above across after all also an and any are as at be been being both but by can could do does
during each either etc experience for from has have having how if in including into is it its job just
least less like looking may more most must need needs new no not of on one or other our out over own
per plus preferred prior related required role should so some strong such than that the their them then
there these they this those through to under understanding up us use using very we well what when where
which while who will with within work working would year years you your team teams ability able knowledge
skills skill responsibilities requirements nice have familiarity solid good great excellent across build
building design designing develop developing help helping make making support supporting join own
""".split())

MAX_KEYWORDS = 30
SCAN_LINES = 12  # roughly what fits above the fold of page one


def _headings(text: str) -> list[str]:
    found = []
    for line in text.split("\n"):
        core = line.strip().rstrip(":").strip()
        if not core or len(core.split()) > 4:
            continue
        for name, pattern in _HEADINGS.items():
            if name not in found and re.fullmatch(pattern, core, re.I):
                found.append(name)
    return found


def parse_preview(resume_text: str) -> dict:
    words = len(resume_text.split())
    lines = resume_text.split("\n")
    headings = _headings(resume_text)
    contact = {
        "email": bool(_EMAIL.search(resume_text)),
        "phone": _has_phone(resume_text),
        "linkedin": bool(_LINKEDIN.search(resume_text)),
        "github": bool(_GITHUB.search(resume_text)),
    }
    issues = []
    if words < 150:
        issues.append("Very little text was extracted. If the resume looks full, parts may be images or text boxes "
                      "that software cannot read.")
    if words > 1200:
        issues.append(f"Long resume ({words} words). Recruiters skim; one to two pages is typical.")
    if not contact["email"]:
        issues.append("No email address was found in the extracted text.")
    if not contact["phone"]:
        issues.append("No phone number was found in the extracted text.")
    for section in ("Experience", "Education", "Skills"):
        if section not in headings:
            issues.append(f"No “{section}” heading was recognised. Standard headings help software "
                          "split your resume into sections.")
    table_lines = sum(1 for line in lines if line.count(" | ") >= 1)
    if table_lines >= 3:
        issues.append(f"{table_lines} lines look like table rows. Some ATS read tables out of order; "
                      "plain lines are safer.")
    return {
        "text": resume_text,
        "stats": {"words": words, "lines": len(lines), "characters": len(resume_text)},
        "headings": headings,
        "contact": contact,
        "issues": issues,
    }


def _terms(text: str) -> Counter:
    masked = _URL_OR_EMAIL.sub(" ", text)
    counts: Counter = Counter()
    for m in _WORD.finditer(masked):
        word = m.group(0).lower().strip(".-/")
        if len(word) >= 3 and word not in STOPWORDS and not word.isdigit():
            counts[word] += 1
    return counts


def _present(term: str, text: str) -> bool:
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", text, re.I) is not None


def keyword_diff(resume_text: str, jd_text: str) -> dict:
    """Exact-term comparison, the way a simple ATS keyword filter works."""
    jd_skills = group_by_skill(find_mentions(jd_text))
    resume_skill_names = set(group_by_skill(find_mentions(resume_text)))
    rows = []
    for name, mentions in jd_skills.items():
        wording = mentions[0].term
        rows.append({
            "keyword": wording,
            "kind": "skill",
            "skill": name,
            "jd_count": len(mentions),
            "exact_in_resume": _present(wording, resume_text),
            "skill_in_resume": name in resume_skill_names,
        })
    skill_words = {w.lower() for m in find_mentions(jd_text) for w in m.term.split()}
    title = next((line for line in jd_text.split("\n") if line.strip()), "")
    title_terms = set(_terms(title))
    for word, count in _terms(jd_text).most_common():
        if word in skill_words or any(r["keyword"].lower() == word for r in rows):
            continue
        if count < 2 and word not in title_terms:
            continue  # one-off words are rarely what a keyword filter is set up for
        rows.append({
            "keyword": word,
            "kind": "term",
            "skill": None,
            "jd_count": count,
            "exact_in_resume": _present(word, resume_text),
            "skill_in_resume": None,
        })
    rows.sort(key=lambda r: (r["kind"] != "skill", -r["jd_count"], r["keyword"].lower()))
    rows = rows[:MAX_KEYWORDS]
    return {
        "keywords": rows,
        "summary": {
            "total": len(rows),
            "exact_in_resume": sum(r["exact_in_resume"] for r in rows),
            # Skill named differently: a human (or this app) sees it, a literal keyword filter may not.
            "different_wording": sum(1 for r in rows if r["kind"] == "skill" and r["skill_in_resume"]
                                     and not r["exact_in_resume"]),
        },
    }


def six_second_scan(resume_text: str, jd_text: str, profile: dict) -> dict:
    """Heuristic: what a recruiter likely takes in from the top of page one."""
    lines = [line.strip() for line in resume_text.split("\n") if line.strip()]
    top = lines[:SCAN_LINES]
    top_text = _URL_OR_EMAIL.sub(" ", "\n".join(top))  # "example.com" is not a headline word
    jd_title = next((line.strip() for line in jd_text.split("\n") if line.strip()), "")
    title_words = {w.lower() for w in _WORD.findall(jd_title) if w.lower() not in STOPWORDS and len(w) > 2}
    headline = top[1] if len(top) > 1 else (top[0] if top else "")
    headline_hits = sorted(w for w in title_words if _present(w, top_text))

    jd_skills = set(group_by_skill(find_mentions(jd_text)))
    top_skills = [name for name in group_by_skill(find_mentions(top_text)) if name in jd_skills]

    experience = profile.get("experience") or []
    if not experience:  # e.g. AI returned no roles: fall back to the first dated line
        from profile_extraction import _fallback_profile

        experience = _fallback_profile(resume_text)["experience"]
    recent = experience[0]["evidence"]["quote"] if experience else None
    bullets = extract_bullets(resume_text)
    quantified = [b for b in bullets if _metric(b)]

    checks = [
        {"label": "Headline echoes the job title",
         "passed": bool(headline_hits),
         "detail": (f"Top of the resume mentions: {', '.join(headline_hits)}" if headline_hits
                    else f"None of the words in “{jd_title[:80]}” appear near the top.")},
        {"label": "Job's skills visible near the top",
         "passed": len(top_skills) >= 3,
         "detail": (", ".join(top_skills) if top_skills else "No skills from the job description in the first lines.")},
        {"label": "Most recent role easy to find",
         "passed": recent is not None,
         "detail": recent or "No dated role was detected."},
        {"label": "Achievements have numbers",
         "passed": len(quantified) >= max(2, len(bullets) // 3) if bullets else False,
         "detail": f"{len(quantified)} of {len(bullets)} bullets include a number."},
    ]
    return {"top_lines": top, "headline": headline, "checks": checks}


def ats_view(resume_text: str, jd_text: str, profile: dict) -> dict:
    return {
        "label": "Preview based on the text this app extracted. Real ATS products differ; this is a heuristic guide.",
        "parse": parse_preview(resume_text),
        "keywords": keyword_diff(resume_text, jd_text),
        "scan": six_second_scan(resume_text, jd_text, profile),
    }
