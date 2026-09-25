from pathlib import Path

from tests.helpers import make_docx, make_pdf

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
JD = "Requirements:\n- Python\n- Kubernetes\nNice to have:\n- Terraform"


def post(client, files, data=None):
    return client.post("/api/analyses", files=files, data=data or {})


def test_analyze_pdf_resume_with_pasted_jd(make_client):
    pdf = make_pdf(["Jane Doe", "Python and Docker developer"])
    with make_client() as client:
        resp = post(client, {"resume": ("cv.pdf", pdf, "application/pdf")}, {"jd_text": JD})

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["sources"]["extraction"] == "fallback"
    assert body["sources"]["fallback_reason"] == "no_api_key"
    assert body["sources"]["semantic"] == "disabled"
    assert body["jd_source"] == "paste"
    assert [m["skill"] for m in body["matched"]] == ["Python"]
    assert {m["skill"] for m in body["missing"]} == {"Kubernetes", "Terraform"}
    assert body["score"]["value"] == round(100 * 3 / 7)
    assert "not an official ATS" in body["score"]["label"]


def test_analyze_docx_resume_with_txt_jd_file(make_client):
    docx = make_docx(["Jane Doe"], table=[["Skills", "Python, Kubernetes"]])
    files = {
        "resume": ("cv.docx", docx, "application/octet-stream"),
        "jd_file": ("jd.txt", JD.encode(), "text/plain"),
    }
    with make_client() as client:
        resp = post(client, files)

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["jd_source"] == "upload"
    assert body["jd_filename"] == "jd.txt"
    assert {m["skill"] for m in body["matched"]} == {"Python", "Kubernetes"}


def test_analysis_is_saved_and_can_be_fetched(make_client):
    resume = (SAMPLES / "sample_resume.txt").read_bytes()
    jd = (SAMPLES / "sample_job_description.txt").read_bytes()
    with make_client() as client:
        created = post(client, {"resume": ("r.txt", resume), "jd_file": ("jd.txt", jd)}).json()
        fetched = client.get(f"/api/analyses/{created['id']}")

    assert fetched.status_code == 200
    assert fetched.json() == created


def test_unknown_analysis_is_404(make_client):
    with make_client() as client:
        assert client.get("/api/analyses/999").status_code == 404


def test_jd_must_be_given_exactly_once(make_client):
    resume = {"resume": ("cv.txt", b"Python")}
    with make_client() as client:
        neither = post(client, resume)
        both = post(client, {**resume, "jd_file": ("jd.txt", b"Python")}, {"jd_text": "Python"})
    assert neither.status_code == 422
    assert both.status_code == 422


def test_non_txt_jd_file_is_rejected(make_client):
    files = {"resume": ("cv.txt", b"Python"), "jd_file": ("jd.pdf", make_pdf(["Python"]))}
    with make_client() as client:
        resp = post(client, files)
    assert resp.status_code == 415
    assert ".txt" in resp.json()["detail"]


def test_unsupported_resume_is_rejected_with_message(make_client):
    with make_client() as client:
        resp = post(client, {"resume": ("cv.doc", b"xx")}, {"jd_text": JD})
    assert resp.status_code == 415
    assert ".docx" in resp.json()["detail"]


def test_created_at_is_reported_in_utc(make_client):
    with make_client() as client:
        created = post(client, {"resume": ("cv.txt", b"Python")}, {"jd_text": "Python"}).json()
        fetched = client.get(f"/api/analyses/{created['id']}").json()
    assert created["created_at"].endswith(("Z", "+00:00"))
    assert fetched["created_at"] == created["created_at"]


# ---- Phase 2: AI, fallback and semantic paths through the API -----------------

from ai_provider import AIError  # noqa: E402
from tests.conftest import FakeEmbedder, FakeProvider  # noqa: E402

RESUME_TXT = (SAMPLES / "sample_resume.txt").read_bytes()
JD_TXT = (SAMPLES / "sample_job_description.txt").read_bytes()
SAMPLE_FILES = {"resume": ("r.txt", RESUME_TXT), "jd_file": ("jd.txt", JD_TXT)}


def test_ai_profile_is_used_and_labelled(make_client):
    provider = FakeProvider({
        "skills": [
            {"name": "CI/CD", "quote": "deployed them to AWS using GitHub Actions"},
            {"name": "Kubernetes", "quote": "Managed Kubernetes clusters"},  # not in resume
        ],
        "experience": [],
        "education": [],
    })
    with make_client(api_key="placeholder", provider=provider) as client:
        body = post(client, SAMPLE_FILES).json()

    assert body["sources"]["extraction"] == "ai"
    assert body["sources"]["model"] == "fake:fake-model"
    assert body["profile"]["discarded"] == 1
    assert any("discarded" in n for n in body["sources"]["notices"])
    cicd = next(m for m in body["matched"] if m["skill"] == "CI/CD")
    assert cicd["match_type"] == "ai_inferred"
    assert cicd["credit"] == 0.5
    assert "Kubernetes" in [m["skill"] for m in body["missing"]]


def test_ai_failure_still_returns_a_labelled_fallback_result(make_client):
    provider = FakeProvider(error=AIError("429 quota exceeded"))
    with make_client(api_key="placeholder", provider=provider) as client:
        resp = post(client, SAMPLE_FILES)

    assert resp.status_code == 201
    sources = resp.json()["sources"]
    assert sources["extraction"] == "fallback"
    assert sources["fallback_reason"] == "provider_error"
    assert any("429 quota exceeded" in n for n in sources["notices"])
    assert len([n for n in sources["notices"] if "AI" in n]) == 1  # one notice, not two


def test_ai_switched_off_is_reported_in_sources_not_as_a_notice(make_client):
    # AI being off is a normal state: the UI shows it calmly from `sources`.
    with make_client(api_key="placeholder", demo_mode="true") as client:
        sources = post(client, SAMPLE_FILES).json()["sources"]
    assert sources["extraction"] == "fallback"
    assert sources["fallback_reason"] == "demo_mode"
    assert sources["notices"] == []


def test_old_ai_off_notice_is_dropped_from_saved_results(make_client):
    from models import Analysis

    with make_client() as client:
        saved = post(client, SAMPLE_FILES).json()
        session = client.app.state.session_factory()
        row = session.get(Analysis, saved["id"])
        result = dict(row.result)
        result["sources"] = {**result["sources"], "notices": [
            "AI extraction is off because no GOOGLE_API_KEY is set. Showing pattern-based results instead.",
            "Something else worth knowing.",
        ]}
        row.result = result
        session.commit()
        session.close()
        notices = client.get(f"/api/analyses/{saved['id']}").json()["sources"]["notices"]
    assert notices == ["Something else worth knowing."]


def test_semantic_match_through_the_api(make_client):
    embedder = FakeEmbedder({"CI/CD": [1, 0], "GitHub Actions": [0.8, 0.6]})
    with make_client(embedder=embedder) as client:
        body = post(client, SAMPLE_FILES).json()

    assert body["sources"]["semantic"] == "enabled"
    cicd = next(m for m in body["matched"] if m["skill"] == "CI/CD")
    assert cicd["match_type"] == "semantic"
    assert cicd["resume_evidence"][0]["similarity"] == 0.8
    assert cicd["resume_evidence"][0]["quote"] in RESUME_TXT.decode()


def test_semantic_model_failure_is_reported_not_fatal(make_client):
    from semantic import EmbedderUnavailable

    embedder = FakeEmbedder(error=EmbedderUnavailable("model download failed"))
    with make_client(embedder=embedder) as client:
        resp = post(client, SAMPLE_FILES)
    assert resp.status_code == 201
    sources = resp.json()["sources"]
    assert sources["semantic"] == "unavailable"
    assert any("model download failed" in n for n in sources["notices"])


def test_phase1_results_saved_earlier_still_load(make_client):
    from models import Analysis

    legacy = {
        "method": "deterministic",
        "score": {"value": 50, "label": "x", "matched_weight": 3, "total_weight": 6,
                  "breakdown": [{"priority": "required", "weight": 3, "matched": 1, "total": 2}]},
        "matched": [{"skill": "Python", "category": "c", "priority": "required", "match_type": "exact",
                     "resume_evidence": [{"quote": "Python", "term": "Python", "term_offset": 0}],
                     "jd_evidence": [{"quote": "Python", "term": "Python", "term_offset": 0}]}],
        "missing": [], "additional": [], "warnings": [],
    }
    with make_client() as client:
        session = client.app.state.session_factory()
        row = Analysis(resume_filename="old.txt", resume_text="Python", jd_source="paste",
                       jd_filename=None, jd_text="Python", score=50, result=legacy)
        session.add(row)
        session.commit()
        resp = client.get(f"/api/analyses/{row.id}")
        session.close()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sources"]["extraction"] == "fallback"
    assert body["matched"][0]["credit"] == 1.0
    assert body["profile"]["skills"] == []
