from pathlib import Path

from tests.conftest import FakeProvider

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
FILES = {
    "resume": ("r.txt", (SAMPLES / "sample_resume.txt").read_bytes()),
    "jd_file": ("jd.txt", (SAMPLES / "sample_job_description.txt").read_bytes()),
}


def new_analysis(client) -> int:
    resp = client.post("/api/analyses", files=FILES)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_roadmap_is_generated_once_then_reused(make_client):
    with make_client() as client:
        aid = new_analysis(client)
        first = client.post(f"/api/analyses/{aid}/roadmap").json()
        again = client.post(f"/api/analyses/{aid}/roadmap").json()
        fresh = client.post(f"/api/analyses/{aid}/roadmap?refresh=true").json()

    assert first["source"] == "fallback"
    assert [i["skill"] for i in first["items"]] == ["CI/CD", "Kubernetes", "Apache Kafka", "RabbitMQ", "Terraform"]
    assert again["created_at"] == first["created_at"]
    assert fresh["created_at"] >= first["created_at"]
    assert all(i["youtube_url"].startswith("https://www.youtube.com/results?search_query=") for i in first["items"])


def test_interview_questions_and_feedback_flow(make_client):
    with make_client() as client:
        aid = new_analysis(client)
        qset = client.post(f"/api/analyses/{aid}/interview").json()
        again = client.post(f"/api/analyses/{aid}/interview").json()
        qid = qset["questions"][0]["id"]
        fb = client.post(f"/api/interview/questions/{qid}/answers", json={"answer": "I built it with Python."})

    assert qset["source"] == "fallback"
    assert again["id"] == qset["id"]
    assert len(qset["questions"]) == 8
    assert fb.status_code == 201
    body = fb.json()
    assert body["question_id"] == qid
    assert body["source"] == "fallback" and body["rating"] is None
    assert body["follow_up_question"]


def test_ai_is_used_for_coaching_when_available(make_client):
    provider = FakeProvider(
        {
            "questions": [
                {
                    "type": "behavioral",
                    "skill": None,
                    "question": "Tell me about a hard deadline you met.",
                    "based_on_quote": None,
                }
            ]
        }
    )
    with make_client(api_key="placeholder", provider=provider) as client:
        aid = new_analysis(client)
        qset = client.post(f"/api/analyses/{aid}/interview").json()
    assert qset["source"] == "ai"
    assert qset["model"] == "fake:fake-model"
    assert [q["question"] for q in qset["questions"]] == ["Tell me about a hard deadline you met."]


def test_answer_validation_and_missing_resources(make_client):
    with make_client() as client:
        aid = new_analysis(client)
        qid = client.post(f"/api/analyses/{aid}/interview").json()["questions"][0]["id"]
        blank = client.post(f"/api/interview/questions/{qid}/answers", json={"answer": "   "})
        too_long = client.post(f"/api/interview/questions/{qid}/answers", json={"answer": "x" * 5001})
        no_question = client.post("/api/interview/questions/9999/answers", json={"answer": "hi"})
        no_analysis_roadmap = client.post("/api/analyses/9999/roadmap")
        no_analysis_interview = client.post("/api/analyses/9999/interview")

    assert blank.status_code == 422
    assert too_long.status_code == 422
    assert no_question.status_code == 404
    assert no_analysis_roadmap.status_code == 404
    assert no_analysis_interview.status_code == 404
