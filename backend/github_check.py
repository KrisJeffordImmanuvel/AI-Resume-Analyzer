"""GitHub evidence check using GitHub's public REST API (public data only).

Only the username is sent to GitHub. Every repo, language and URL shown comes
from GitHub's response. A resume language not seen on GitHub is reported as
"not seen in public repos", never as false: private work is invisible here.
"""

import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Protocol

from skills import find_mentions, group_by_skill, skill_index

USERNAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_GITHUB_LINK = re.compile(r"github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))(?![A-Za-z0-9-])", re.I)
_NOT_USERS = {"orgs", "topics", "features", "about", "pricing", "login", "join", "settings", "marketplace"}
MAX_REPOS = 100
RECENT_DAYS = 365
EXAMPLES_PER_LANGUAGE = 3

# GitHub language names that differ from our skill names.
LANGUAGE_TO_SKILL = {
    "Shell": "Bash",
    "HCL": "Terraform",
    "Dockerfile": "Docker",
    "Vue": "Vue.js",
    "SCSS": "Sass",
    "Jupyter Notebook": "Jupyter",
    "TSQL": "Microsoft SQL Server",
    "PLSQL": "Oracle Database",
    "PLpgSQL": "PostgreSQL",
    "Go": "Go",
    "R": "R",
    "C": "C",
    "Svelte": "Svelte",
    "Astro": None,
    "Makefile": None,
}
# Skill categories where a public repo is meaningful evidence.
CODE_CATEGORIES = {
    "Programming Languages",
    "Web Frontend",
    "Web Backend",
    "Mobile",
    "DevOps & Infrastructure",
    "Data & Analytics",
    "Machine Learning & AI",
    "Databases",
    "Cloud",
    "Testing & QA",
}


class GitHubError(Exception):
    """User-safe GitHub problem (not found, rate limit, network)."""


class GitHubClient(Protocol):
    def user(self, username: str) -> dict: ...
    def repos(self, username: str) -> list[dict]: ...


class HttpGitHubClient:
    BASE = "https://api.github.com"

    def __init__(self, token: str = "", timeout: float = 10.0, transport=None):
        import httpx

        headers = {"Accept": "application/vnd.github+json", "User-Agent": "ai-resume-analyzer"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        # `transport` lets tests supply canned responses (httpx.MockTransport) with no network.
        self._client = httpx.Client(base_url=self.BASE, headers=headers, timeout=timeout, transport=transport)

    def _get(self, path: str, params: dict | None = None):
        import httpx

        try:
            resp = self._client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise GitHubError(
                f"Could not reach GitHub ({type(exc).__name__}). Check your internet connection."
            ) from exc
        if resp.status_code == 404:
            raise GitHubError("No public GitHub user with that username.")
        if resp.status_code in (403, 429) and resp.headers.get("x-ratelimit-remaining") == "0":
            raise GitHubError(
                "GitHub's hourly limit for anonymous requests was reached. Try again later, "
                "or set GITHUB_TOKEN in backend\\.env for a higher limit."
            )
        if resp.status_code >= 400:
            raise GitHubError(f"GitHub returned an error ({resp.status_code}).")
        return resp.json()

    def user(self, username: str) -> dict:
        return self._get(f"/users/{username}")

    def repos(self, username: str) -> list[dict]:
        return self._get(f"/users/{username}/repos", {"per_page": MAX_REPOS, "sort": "pushed", "type": "owner"})


def detect_username(resume_text: str) -> str | None:
    for m in _GITHUB_LINK.finditer(resume_text):
        if m.group(1).lower() not in _NOT_USERS:
            return m.group(1)
    return None


def language_skill(language: str) -> str | None:
    if language in LANGUAGE_TO_SKILL:
        return LANGUAGE_TO_SKILL[language]
    if language in skill_index():
        return language
    found = {m.skill for m in find_mentions(language)}
    return found.pop() if len(found) == 1 else None


@lru_cache(maxsize=1)
def _topic_index() -> dict[str, str]:
    index = {}
    for skill in skill_index().values():
        for term in (skill.name, *skill.terms, *skill.terms_case_sensitive):
            index.setdefault(term.lower(), skill.name)
    return index


def _topic_skill(topic: str) -> str | None:
    topic = topic.lower()
    return _topic_index().get(topic) or _topic_index().get(topic.replace("-", " "))


def _parse_time(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
    except ValueError:
        return None


def github_check(username: str, resume_text: str, client: GitHubClient, now: datetime | None = None) -> dict:
    username = (username or "").strip().lstrip("@")
    if not USERNAME.match(username):
        raise GitHubError("That does not look like a GitHub username (letters, numbers and single hyphens).")
    now = now or datetime.now(UTC)
    user = client.user(username)
    repos = [r for r in client.repos(username) if not r.get("fork") and not r.get("archived")]

    by_language: dict[str, list[dict]] = {}
    counts: Counter = Counter()
    evidence: dict[str, list[dict]] = {}  # skill -> repos showing it
    recent = 0
    for r in repos:
        pushed = _parse_time(r.get("pushed_at"))
        if pushed and now - pushed <= timedelta(days=RECENT_DAYS):
            recent += 1
        repo = {"name": r.get("name"), "url": r.get("html_url"), "pushed_at": r.get("pushed_at")}
        lang = r.get("language")
        if lang:
            counts[lang] += 1
            by_language.setdefault(lang, []).append(repo)
            if language_skill(lang):
                evidence.setdefault(language_skill(lang), []).append({**repo, "via": f"main language: {lang}"})
        # Topics and the description are the repo owner's own words, read from GitHub.
        # Topics are lowercase labels (e.g. "react"), so they are matched exactly and
        # case-insensitively; the description is matched like any other text.
        topic_skills = {_topic_skill(t) for t in r.get("topics") or []} - {None}
        for skill in topic_skills | {m.skill for m in find_mentions(r.get("description") or "")}:
            if not any(e["name"] == repo["name"] for e in evidence.get(skill, [])):
                evidence.setdefault(skill, []).append({**repo, "via": "topics/description"})

    languages = []
    for lang, n in counts.most_common():
        languages.append(
            {
                "language": lang,
                "repos": n,
                "skill": language_skill(lang),
                "examples": by_language[lang][:EXAMPLES_PER_LANGUAGE],
            }
        )

    index = skill_index()
    resume_skills = [s for s in group_by_skill(find_mentions(resume_text)) if index[s].category in CODE_CATEGORIES]
    claims = []
    for skill in resume_skills:
        repos_for = evidence.get(skill, [])
        claims.append(
            {
                "skill": skill,
                "status": "seen" if repos_for else "not_seen",
                "repos": len(repos_for),
                "examples": repos_for[:EXAMPLES_PER_LANGUAGE],
            }
        )
    claims.sort(key=lambda c: (c["status"] != "seen", -c["repos"], c["skill"].lower()))
    only_github = [lang for lang in languages if lang["skill"] and lang["skill"] not in set(resume_skills)]

    return {
        "username": user.get("login", username),
        "profile_url": user.get("html_url") or f"https://github.com/{username}",
        "name": user.get("name"),
        "public_repos": user.get("public_repos", len(repos)),
        "followers": user.get("followers"),
        "account_created_at": user.get("created_at"),
        "repos_analyzed": len(repos),
        "recently_active_repos": recent,
        "languages": languages,
        "resume_claims": claims,
        "not_on_resume": only_github,
        "label": (
            "Based on public, non-fork repositories: GitHub's main language per repo, and the repo's own "
            "topics and description. "
            "Private or company work is not visible, so 'not seen' does not mean untrue."
        ),
    }
