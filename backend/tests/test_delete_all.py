"""Delete all my data."""

import pathlib

from sqlalchemy import func, select

from database import Base

SAMPLES = pathlib.Path(__file__).resolve().parents[2] / "samples"


def test_delete_all_removes_everything(make_client):
    resume = (SAMPLES / "sample_resume.txt").read_bytes()
    jd = (SAMPLES / "sample_job_description.txt").read_text(encoding="utf-8")
    with make_client() as client:
        a = client.post("/api/analyses", files={"resume": ("cv.txt", resume)}, data={"jd_text": jd}).json()
        client.post(f"/api/analyses/{a['id']}/roadmap")
        client.post(f"/api/analyses/{a['id']}/interview")
        job = client.post("/api/jobs", data={"jd_text": jd}).json()
        client.post(f"/api/jobs/{job['id']}/candidates", files=[("resumes", ("c.txt", resume))])

        resp = client.post("/api/data/delete-all", json={"confirm": "DELETE"})
        assert resp.status_code == 200
        assert resp.json() == {"analyses_deleted": 2, "jobs_deleted": 1}

        assert client.get("/api/analyses").json() == []
        assert client.get("/api/jobs").json() == []
        with client.app.state.engine.connect() as conn:
            for table in Base.metadata.sorted_tables:
                assert conn.execute(select(func.count()).select_from(table)).scalar() == 0, table.name
        # The app keeps working afterwards.
        again = client.post("/api/analyses", files={"resume": ("cv.txt", resume)}, data={"jd_text": jd})
        assert again.status_code == 201


def test_delete_all_needs_the_confirmation_word(make_client):
    with make_client() as client:
        client.post("/api/analyses", files={"resume": ("cv.txt", b"Python")}, data={"jd_text": "Python"})
        assert client.post("/api/data/delete-all", json={"confirm": "yes"}).status_code == 422
        assert client.post("/api/data/delete-all", json={}).status_code == 422
        assert len(client.get("/api/analyses").json()) == 1
