"""Oversized requests are refused early with a plain message."""

import main


def test_declared_oversized_upload_is_refused(make_client):
    big = b"x" * (main.MAX_REQUEST_BYTES + 1)
    with make_client() as client:
        resp = client.post("/api/analyses", files={"resume": ("cv.txt", big)}, data={"jd_text": "Python"})
    assert resp.status_code == 413
    assert "too large" in resp.json()["detail"]


def test_oversized_upload_without_length_is_refused(make_client):
    chunk = b"x" * (1024 * 1024)

    def stream():  # no Content-Length: the size is only known while reading
        for _ in range(main.MAX_REQUEST_BYTES // len(chunk) + 2):
            yield chunk

    with make_client() as client:
        resp = client.post(
            "/api/analyses", content=stream(), headers={"content-type": "multipart/form-data; boundary=x"}
        )
    assert resp.status_code == 413


def test_normal_requests_are_unaffected(make_client):
    with make_client() as client:
        resp = client.post(
            "/api/analyses", files={"resume": ("cv.txt", b"Python developer")}, data={"jd_text": "Need Python"}
        )
        assert resp.status_code == 201
        assert client.get("/health").status_code == 200


def test_limit_fits_a_full_job_provider_batch():
    from parsing import MAX_UPLOAD_BYTES
    from routers.jobs import MAX_FILES_PER_UPLOAD

    assert main.MAX_REQUEST_BYTES > MAX_FILES_PER_UPLOAD * MAX_UPLOAD_BYTES
