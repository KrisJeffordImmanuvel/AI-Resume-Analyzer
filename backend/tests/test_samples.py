"""The "Try with sample data" documents."""

from routers import samples


def test_samples_are_served(make_client):
    with make_client() as client:
        body = client.get("/api/samples").json()
    assert body["resume"]["filename"] == "sample_resume.txt"
    assert body["job_description"]["filename"] == "sample_job_description.txt"
    assert body["resume"]["text"].strip()
    assert body["job_description"]["text"].strip()


def test_sample_analysis_gives_the_documented_score(make_client):
    # The README promises 69/100 without AI for the sample pair.
    with make_client() as client:
        body = client.get("/api/samples").json()
        resp = client.post(
            "/api/analyses",
            files={"resume": (body["resume"]["filename"], body["resume"]["text"].encode(), "text/plain")},
            data={"jd_text": body["job_description"]["text"]},
        )
    assert resp.status_code == 201, resp.text
    assert resp.json()["score"]["value"] == 69


def test_missing_samples_give_a_clear_404(make_client, tmp_path, monkeypatch):
    monkeypatch.setattr(samples, "SAMPLES_DIR", tmp_path / "nowhere")
    with make_client() as client:
        resp = client.get("/api/samples")
    assert resp.status_code == 404
    assert "sample files are missing" in resp.json()["detail"]
