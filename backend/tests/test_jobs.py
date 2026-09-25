from pathlib import Path

from comparison import compare, job_skills
from tests.conftest import FakeProvider

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
JD = (SAMPLES / "sample_job_description.txt").read_bytes()
RESUMES = {name: (SAMPLES / name).read_bytes() for name in
           ("sample_resume.txt", "sample_resume_devops.txt", "sample_resume_frontend.txt")}


def create_job(client, **form):
    files = {"jd_file": ("jd.txt", JD, "text/plain")} if "jd_text" not in form else None
    return client.post("/api/jobs", data=form, files=files)


def upload(client, job_id, names):
    files = [("resumes", (n, RESUMES[n] if n in RESUMES else b"", "text/plain")) for n in names]
    return client.post(f"/api/jobs/{job_id}/candidates", files=files)


def test_job_skills_come_from_the_engine_with_priorities():
    skills = job_skills(JD.decode())
    assert [s["priority"] for s in skills] == sorted([s["priority"] for s in skills],
                                                      key=["required", "standard", "preferred"].index)
    names = {s["skill"] for s in skills}
    assert {"Python", "Kubernetes", "Terraform"} <= names


def test_create_job_defaults_title_to_first_line(make_client):
    with make_client() as client:
        job = create_job(client).json()
        titled = create_job(client, title="Backend role", jd_text="Need Python").json()
        listing = client.get("/api/jobs").json()
    assert job["title"] == "Senior Backend Engineer - Example Payments"
    assert job["candidates"] == [] and job["candidate_count"] == 0
    assert titled["title"] == "Backend role"
    assert [j["id"] for j in listing] == [titled["id"], job["id"]]


def test_candidates_are_ranked_and_compared_side_by_side(make_client):
    with make_client() as client:
        job = create_job(client).json()
        resp = upload(client, job["id"], list(RESUMES))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert [o["status"] for o in body["outcomes"]] == ["added", "added", "added"]
    rows = body["job"]["candidates"]
    assert [r["rank"] for r in rows] == [1, 2, 3]
    assert [r["score"] for r in rows] == sorted((r["score"] for r in rows), reverse=True)
    by_file = {r["filename"]: r for r in rows}
    devops = by_file["sample_resume_devops.txt"]
    assert devops["cells"]["Kubernetes"]["status"] == "named"
    assert devops["cells"]["Kubernetes"]["quote"]
    assert by_file["sample_resume.txt"]["cells"]["Kubernetes"] == {"status": "missing", "match_type": None,
                                                                  "quote": None}
    assert set(devops["cells"]) == {s["skill"] for s in body["job"]["skills"]}


def test_provider_results_are_identical_to_job_seeker_results(make_client):
    """Single engine: the same resume + JD gives the same analysis in both modes."""
    with make_client() as client:
        job = create_job(client).json()
        added = upload(client, job["id"], ["sample_resume_devops.txt"]).json()["outcomes"][0]
        via_provider = client.get(f"/api/analyses/{added['analysis_id']}").json()
        via_seeker = client.post("/api/analyses", files={
            "resume": ("sample_resume_devops.txt", RESUMES["sample_resume_devops.txt"]),
            "jd_file": ("jd.txt", JD)}).json()
    for key in ("score", "matched", "missing", "additional", "profile", "sources", "warnings"):
        assert via_provider[key] == via_seeker[key], key


def test_ai_is_used_for_candidates_when_available(make_client):
    provider = FakeProvider({"skills": [{"name": "CI/CD", "quote": "deployed them to AWS using GitHub Actions"}],
                             "experience": [], "education": []})
    with make_client(api_key="placeholder", provider=provider) as client:
        job = create_job(client).json()
        row = upload(client, job["id"], ["sample_resume.txt"]).json()["job"]["candidates"][0]
    assert row["extraction"] == "ai"
    assert row["cells"]["CI/CD"]["status"] == "related"
    assert row["cells"]["CI/CD"]["match_type"] == "ai_inferred"


def test_bad_files_and_duplicates_do_not_stop_the_batch(make_client):
    with make_client() as client:
        job = create_job(client).json()
        upload(client, job["id"], ["sample_resume.txt"])
        files = [("resumes", ("sample_resume.txt", RESUMES["sample_resume.txt"])),
                 ("resumes", ("old.doc", b"x")),
                 ("resumes", ("empty.txt", b"")),
                 ("resumes", ("sample_resume_frontend.txt", RESUMES["sample_resume_frontend.txt"]))]
        body = client.post(f"/api/jobs/{job['id']}/candidates", files=files).json()
    assert [o["status"] for o in body["outcomes"]] == ["duplicate", "error", "error", "added"]
    assert ".docx" in body["outcomes"][1]["message"]
    assert body["job"]["candidate_count"] == 2


def test_remove_candidate_keeps_the_analysis(make_client):
    with make_client() as client:
        job = create_job(client).json()
        aid = upload(client, job["id"], ["sample_resume.txt"]).json()["outcomes"][0]["analysis_id"]
        gone = client.delete(f"/api/jobs/{job['id']}/candidates/{aid}")
        again = client.delete(f"/api/jobs/{job['id']}/candidates/{aid}")
        detail = client.get(f"/api/jobs/{job['id']}").json()
        analysis = client.get(f"/api/analyses/{aid}")
    assert gone.status_code == 204 and again.status_code == 404
    assert detail["candidates"] == []
    assert analysis.status_code == 200


def test_limits_and_validation(make_client):
    with make_client() as client:
        job = create_job(client).json()
        too_many = client.post(f"/api/jobs/{job['id']}/candidates",
                               files=[("resumes", (f"r{i}.txt", b"Python")) for i in range(11)])
        no_jd = client.post("/api/jobs", data={"title": "x"})
        bad_jd = client.post("/api/jobs", files={"jd_file": ("jd.pdf", b"%PDF")})
        missing = [client.get("/api/jobs/999").status_code,
                   client.post("/api/jobs/999/candidates", files=[("resumes", ("r.txt", b"Python"))]).status_code]
    assert too_many.status_code == 422
    assert no_jd.status_code == 422 and bad_jd.status_code == 415
    assert missing == [404, 404]


def test_compare_handles_no_candidates_and_legacy_results():
    out = compare("Requirements:\n- Python", [])
    assert out["candidates"] == [] and [s["skill"] for s in out["skills"]] == ["Python"]


def test_delete_job_removes_it_and_its_candidates_permanently(make_client):
    from models import Analysis, InterviewSet, JobCandidate

    with make_client() as client:
        job = create_job(client).json()
        other = create_job(client, title="Other role", jd_text="Need Python").json()
        added = upload(client, job["id"], ["sample_resume.txt", "sample_resume_devops.txt"]).json()
        ids = [o["analysis_id"] for o in added["outcomes"]]
        kept = upload(client, other["id"], ["sample_resume.txt"]).json()["outcomes"][0]["analysis_id"]
        client.post(f"/api/analyses/{ids[0]}/interview")  # something generated from a candidate
        seeker = client.post("/api/analyses", files={"resume": ("cv.txt", b"Python")}, data={"jd_text": "Python"}).json()

        assert client.delete(f"/api/jobs/{job['id']}").status_code == 204

        assert client.get(f"/api/jobs/{job['id']}").status_code == 404
        assert [j["id"] for j in client.get("/api/jobs").json()] == [other["id"]]
        for aid in ids:
            assert client.get(f"/api/analyses/{aid}").status_code == 404
        # Deleted candidates do not reappear in Job Seeker's list; other data is untouched.
        assert [a["id"] for a in client.get("/api/analyses").json()] == [seeker["id"]]
        assert client.get(f"/api/jobs/{other['id']}").json()["candidate_count"] == 1
        assert client.get(f"/api/analyses/{kept}").status_code == 200
        session = client.app.state.session_factory()
        assert session.query(InterviewSet).filter(InterviewSet.analysis_id.in_(ids)).count() == 0
        assert session.query(JobCandidate).filter(JobCandidate.job_id == job["id"]).count() == 0
        assert session.query(Analysis).count() == 2
        session.close()


def test_delete_unknown_job_is_404(make_client):
    with make_client() as client:
        assert client.delete("/api/jobs/999").status_code == 404
