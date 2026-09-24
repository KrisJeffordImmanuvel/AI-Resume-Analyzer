"""Fairness scan (rule-based).

Job description: wording that research and hiring guides associate with putting
some groups off applying (gender-coded, age-coded, exclusionary requirements).
Resume: personal details that are not needed to judge skills and can invite
bias. This app never uses any of these details in scoring.
Every finding quotes the exact line; findings are prompts to review, not verdicts.
"""

import re

from skills import quote_for

JD_RULES = [
    # (category, pattern, suggestion)
    ("Gender-coded", r"rock ?stars?|ninjas?|gurus?|superstars?|wizards?|hackers? mindset|dominant|aggressive(ly)?|"
                     r"fearless|manpower|chairman|salesman|(?<!s)he or she|his or her|brotherhood|guys",
     "Use neutral wording (e.g. 'expert', 'skilled engineer', 'team', 'they')."),
    ("Age-coded", r"young|youthful|recent (college )?grad(uate)?s?|digital natives?|energetic|fresh blood|"
                  r"max(imum)? \d+ years (of )?experience|under \d\d|below \d\d years",
     "Describe the skills needed instead of age or career stage."),
    ("Exclusionary requirement", r"native (english )?speakers?|culture fit|able[- ]bodied|clean[- ]shaven|"
                                 r"must be (male|female)|(male|female) candidates only|unmarried|single candidates",
     "Check it is a genuine job requirement; if so, state the actual skill needed (e.g. 'fluent English')."),
    ("Check if legally required", r"citizens? only|must be a citizen|local candidates only|no visa sponsorship",
     "Fine if legally required for the role; otherwise it may exclude qualified candidates."),
]

RESUME_RULES = [
    ("Date of birth / age", r"date of birth|d\.?o\.?b\.?|\bage\s*[:\-]\s*\d{2}|\b\d{2} years old"),
    # "Married" only as a field value, not in a sentence like "married data and design".
    ("Marital status", r"marital status|^\s*(married|unmarried|single)\s*$|\bspouse('?s)? name\b"),
    ("Gender", r"\bgender\s*[:\-]|\bsex\s*[:\-]"),
    ("Religion / caste", r"\breligion\b|\bcaste\b"),
    ("Nationality", r"\bnationality\b"),
    ("Family details", r"father'?s name|mother'?s name|\bchildren\b|\bkids\b"),
    ("Photo", r"\bphoto(graph)?\b"),
    ("Health", r"\bdisability\b|\bhealth status\b|\bblood group\b"),
]
RESUME_ADVICE = ("Not needed to judge your skills and can invite bias; many employers advise leaving it out "
                 "unless the application explicitly asks for it.")


def _scan(text: str, rules) -> list[dict]:
    """One finding per (category, line), listing every flagged term on that line."""
    findings: dict[tuple[str, str], dict] = {}
    for rule in rules:
        category, pattern = rule[0], rule[1]
        for m in re.finditer(r"(?<![A-Za-z])(?:" + pattern + r")(?![A-Za-z])", text, re.I | re.M):
            quote, offset = quote_for(text, m.start(), m.end())
            key = (category, quote)
            if key in findings:
                if m.group(0) not in findings[key]["terms"]:
                    findings[key]["terms"].append(m.group(0).strip())
                continue
            findings[key] = {"category": category, "terms": [m.group(0).strip()], "quote": quote,
                             "suggestion": rule[2] if len(rule) > 2 else RESUME_ADVICE}
    return list(findings.values())


def fairness_scan(resume_text: str, jd_text: str) -> dict:
    return {
        "method": "rule_based",
        "label": "Word-list checks that flag things to review. A flag is not proof of bias, and no list is complete.",
        "job_description": _scan(jd_text, JD_RULES),
        "resume": _scan(resume_text, RESUME_RULES),
        "scoring_note": "This app's scores never use age, gender, marital status, religion, nationality, "
                        "family details, photos or health information.",
    }
