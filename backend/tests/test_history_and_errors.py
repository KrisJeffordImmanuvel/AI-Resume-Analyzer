from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
FILES = {
    "resume": ("r.txt", (SAMPLES / "sample_resume.txt").read_bytes()),
    "jd_file": ("jd.txt", (SAMPLES / "sample_job_description.txt").read_bytes()),
}


def new_analysis(client) -> int:
    return client.post("/api/analyses", files=FILES).json()["id"]


def test_recent_analyses_newest_first_and_excludes_job_candidates(make_client):
    with make_client() as client:
        first, second = new_analysis(client), new_analysis(client)
        job = client.post("/api/jobs", data={"jd_text": "Need Python"}).json()
        client.post(f"/api/jobs/{job['id']}/candidates", files=[("resumes", ("c.txt", b"Python developer"))])
        listing = client.get("/api/analyses").json()
        limited = client.get("/api/analyses?limit=1").json()
    assert [a["id"] for a in listing] == [second, first]
    assert listing[0] | {"created_at": None} == {
        "id": second, "created_at": None, "resume_filename": "r.txt",
        "jd_title": "Senior Backend Engineer - Example Payments", "score": 69, "extraction": "fallback",
    }
    assert [a["id"] for a in limited] == [second]


def test_delete_removes_the_analysis_and_everything_generated_from_it(make_client):
    with make_client() as client:
        aid = new_analysis(client)
        keep = new_analysis(client)
        client.post(f"/api/analyses/{aid}/roadmap")
        qid = client.post(f"/api/analyses/{aid}/interview").json()["questions"][0]["id"]
        client.post(f"/api/interview/questions/{qid}/answers", json={"answer": "I built it."})
        client.post(f"/api/analyses/{aid}/rewrites", json={"bullet": "- Built dashboards"})
        client.post(f"/api/analyses/{aid}/linkedin", json={"text": "Experience\nEngineer\nAcme\n2020 - 2021"})
        gone = client.delete(f"/api/analyses/{aid}")
        after = [client.get(f"/api/analyses/{aid}").status_code,
                 client.get(f"/api/analyses/{aid}/rewrites").status_code,
                 client.post(f"/api/interview/questions/{qid}/answers", json={"answer": "x"}).status_code]
        again = client.delete(f"/api/analyses/{aid}")
        kept = client.get(f"/api/analyses/{keep}").status_code
        session = client.app.state.session_factory()
        from models import BulletRewrite, ExternalCheck, InterviewAnswer, InterviewQuestion, InterviewSet, Roadmap
        leftovers = sum(session.query(m).count() for m in
                        (Roadmap, InterviewSet, InterviewQuestion, InterviewAnswer, BulletRewrite, ExternalCheck))
        session.close()
    assert gone.status_code == 204
    assert after == [404, 404, 404]
    assert again.status_code == 404
    assert kept == 200
    assert leftovers == 0


def test_deleting_a_job_candidate_analysis_removes_it_from_the_job(make_client):
    with make_client() as client:
        job = client.post("/api/jobs", data={"jd_text": "Need Python"}).json()
        out = client.post(f"/api/jobs/{job['id']}/candidates", files=[("resumes", ("c.txt", b"Python dev"))]).json()
        client.delete(f"/api/analyses/{out['outcomes'][0]['analysis_id']}")
        detail = client.get(f"/api/jobs/{job['id']}").json()
    assert detail["candidates"] == []


def test_unexpected_errors_return_a_plain_json_message(make_client, monkeypatch):
    import routers.analyses as analyses

    def boom(*args, **kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(analyses, "run_analysis", boom)
    with make_client() as client:
        client_no_raise = client.__class__(client.app, raise_server_exceptions=False)
        resp = client_no_raise.post("/api/analyses", files=FILES)
    assert resp.status_code == 500
    assert "Something went wrong" in resp.json()["detail"]
    assert "secret internal detail" not in resp.text
