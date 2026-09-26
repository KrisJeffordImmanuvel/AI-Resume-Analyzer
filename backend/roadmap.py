"""Learning roadmap: one entry per skill gap, most important first.

Gaps are the analysis's missing skills ("learn") and skills with only related,
half-credit evidence ("strengthen"). The YouTube link is always built here from
the skill name, never taken from AI output, so it is a real search URL.
With AI, Gemini writes the study steps and project idea (labelled as AI advice);
without it, category templates are used.
"""

from urllib.parse import quote_plus

from pydantic import BaseModel, Field

from ai_provider import AIError, AIProvider

MAX_ITEMS = 15
_PRIORITY_RANK = {"required": 0, "standard": 1, "preferred": 2}

# First step and project idea per skill category; {skill} is filled in.
_CATEGORY_TEMPLATES = {
    "Programming Languages": (
        "Learn {skill} syntax, core data types and the standard library with an introductory course.",
        "Rewrite a small tool you already use (a CLI, a script) in {skill}.",
    ),
    "Web Frontend": (
        "Follow the official {skill} tutorial and build its example app end to end.",
        "Build a small single-page app with {skill} that calls a public API.",
    ),
    "Web Backend": (
        "Work through the official {skill} getting-started guide and run its examples locally.",
        "Use {skill} in a small backend project of your own, with tests and a README.",
    ),
    "Databases": (
        "Learn {skill} basics: schema design, queries, indexes and transactions.",
        "Model a small real dataset in {skill} and write the queries a report would need.",
    ),
    "Cloud": (
        "Create a free-tier {skill} account and follow a beginner deployment tutorial.",
        "Deploy one of your existing projects on {skill} and document the setup.",
    ),
    "DevOps & Infrastructure": (
        "Learn the core concepts of {skill} and run the official quick-start locally.",
        "Add {skill} to one of your existing projects (e.g. build, deploy or monitor it).",
    ),
    "Data & Analytics": (
        "Learn {skill} fundamentals with a hands-on beginner course.",
        "Analyse a public dataset with {skill} and publish the notebook or report.",
    ),
    "Machine Learning & AI": (
        "Learn the core ideas behind {skill} and run a beginner tutorial end to end.",
        "Train or apply a small model with {skill} on a public dataset and write up the results.",
    ),
    "Testing & QA": (
        "Learn {skill} basics and write tests for a small existing project.",
        "Add a {skill} test suite to one of your projects and run it in CI.",
    ),
    "Soft Skills": (
        "Pick a concrete example from your own experience that shows {skill}.",
        "Practise telling that example in the STAR format (situation, task, action, result).",
    ),
}
_DEFAULT_TEMPLATE = (
    "Learn the fundamentals of {skill} with an introductory course or the official documentation.",
    "Build a small project that uses {skill} and publish it (for example on GitHub).",
)


def youtube_search_url(skill: str) -> str:
    return "https://www.youtube.com/results?search_query=" + quote_plus(f"{skill} tutorial")


def _gaps(result: dict) -> list[dict]:
    gaps = [
        {
            "skill": m["skill"],
            "category": m["category"],
            "priority": m["priority"],
            "kind": "learn",
            "jd_evidence": m["jd_evidence"][:1],
            "resume_evidence": [],
        }
        for m in result.get("missing", [])
    ]
    gaps += [
        {
            "skill": m["skill"],
            "category": m["category"],
            "priority": m["priority"],
            "kind": "strengthen",
            "jd_evidence": m["jd_evidence"][:1],
            "resume_evidence": m["resume_evidence"][:1],
        }
        for m in result.get("matched", [])
        if m.get("credit", 1.0) < 1.0
    ]
    gaps.sort(key=lambda g: (_PRIORITY_RANK[g["priority"]], g["kind"] != "learn", g["skill"].lower()))
    return gaps[:MAX_ITEMS]


def _template_steps(gap: dict) -> tuple[list[str], str]:
    first, project = _CATEGORY_TEMPLATES.get(gap["category"], _DEFAULT_TEMPLATE)
    skill = gap["skill"]
    steps = [first.format(skill=skill)]
    if gap["kind"] == "strengthen":
        steps.append(
            f"Your resume shows related experience but never names {skill}. "
            f"If you have used it, name it explicitly in that bullet."
        )
    steps.append(f"Add a resume bullet that names {skill}, what you built, and a measurable result.")
    return steps, project.format(skill=skill)


# ---- AI --------------------------------------------------------------------------


class _AIRoadmapItem(BaseModel):
    skill: str = Field(description="Exactly one of the skill names given.")
    steps: list[str] = Field(description="3 to 5 short, concrete study steps, in order.")
    project_idea: str = Field(description="One small portfolio project that proves the skill.")


class AIRoadmap(BaseModel):
    items: list[_AIRoadmapItem]


SYSTEM_PROMPT = """You are a practical career coach writing a study plan.
Rules:
- Only write plans for the skill names given, spelled exactly as given.
- Steps are short, concrete and in order. No links or URLs.
- You may mention the candidate's existing skills ONLY from the list given; never assume others.
- Do not invent facts about the candidate."""


def _prompt(gaps: list[dict], known_skills: list[str]) -> str:
    lines = [
        f"- {g['skill']} ({g['priority']}; {'new skill' if g['kind'] == 'learn' else 'has related experience'})"
        for g in gaps
    ]
    return (
        "Skills to plan for:\n"
        + "\n".join(lines)
        + "\n\nSkills the candidate already has (verified): "
        + (", ".join(known_skills) or "none listed")
    )


def build_roadmap(result: dict, provider: AIProvider | None, fallback_reason: str | None) -> dict:
    gaps = _gaps(result)
    ai_plans: dict[str, dict] = {}
    notices: list[str] = []
    source, model = "fallback", None

    if provider is not None and gaps:
        known = sorted({m["skill"] for m in result.get("matched", []) if m.get("credit", 1.0) == 1.0})
        try:
            raw = provider.generate_json(system=SYSTEM_PROMPT, prompt=_prompt(gaps, known), schema=AIRoadmap)
            wanted = {g["skill"].lower(): g["skill"] for g in gaps}
            for item in raw.get("items", []):
                name = wanted.get((item.get("skill") or "").strip().lower())
                steps = [s.strip() for s in item.get("steps", []) if s and s.strip()][:5]
                if name and steps and name not in ai_plans:
                    ai_plans[name] = {"steps": steps, "project_idea": (item.get("project_idea") or "").strip()}
            source, model = "ai", f"{provider.name}:{provider.model}"
            missing = [g["skill"] for g in gaps if g["skill"] not in ai_plans]
            if missing:
                notices.append(f"AI gave no plan for {', '.join(missing)}; template steps are shown for those.")
        except AIError as exc:
            fallback_reason = "provider_error"
            notices.append(f"AI roadmap failed, so template steps are shown instead. ({exc})")

    items = []
    for gap in gaps:
        plan = ai_plans.get(gap["skill"])
        if plan:
            steps, project, steps_source = plan["steps"], plan["project_idea"] or None, "ai"
        else:
            steps, project = _template_steps(gap)
            steps_source = "template"
        items.append(
            {
                **gap,
                "steps": steps,
                "project_idea": project,
                "steps_source": steps_source,
                "youtube_url": youtube_search_url(gap["skill"]),
            }
        )

    return {
        "source": source,
        "model": model,
        "fallback_reason": None if source == "ai" else fallback_reason,
        "notices": notices,
        "items": items,
    }
