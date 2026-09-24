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
    assert body["method"] == "deterministic"
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
