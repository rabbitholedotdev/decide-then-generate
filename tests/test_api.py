from __future__ import annotations


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["prompt_version"].startswith("sha256:")
    assert body["catalog_size"] == 10
    assert body["retriever"] == "fixtures"
    assert body["decider"] == "mock"


def test_catalog_and_schema(client):
    cat = client.get("/v1/catalog").json()
    assert len(cat["items"]) == 10
    schema = client.get("/v1/schema").json()
    assert len(schema["decision_fields"]) >= 15
    assert "speech_act" in schema["decision_fields"]
    assert "handoff" in schema["speech_acts"]


def test_chat_session_and_no_early_offer(client):
    first = client.post("/v1/chat", json={"message": "oi"}).json()
    assert first["speech_act"] in {"greet", "ask_need"}
    assert first["should_offer"] is False
    sid = first["session_id"]
    second = client.post("/v1/chat", json={"message": "quero um cha", "session_id": sid}).json()
    assert second["session_id"] == sid
    assert second["should_offer"] is False
    assert second["prompt_version"] == first["prompt_version"]
    third = client.post(
        "/v1/chat", json={"message": "para presente", "session_id": sid}
    ).json()
    fourth = client.post(
        "/v1/chat", json={"message": "ela gosta de verde", "session_id": sid}
    ).json()
    assert third["should_offer"] is False
    assert fourth["should_offer"] is False
    fifth = client.post(
        "/v1/chat",
        json={"message": "e iniciante e pode ate 90", "session_id": sid},
    ).json()
    assert fifth["should_offer"] is True
    assert fifth["speech_act"] == "offer"
    assert fifth["guard"]["passed"] is True


def test_chat_handoff(client):
    res = client.post(
        "/v1/chat", json={"message": "vou processar voces no procon com advogado"}
    ).json()
    assert res["should_handoff"] is True
    assert res["speech_act"] == "handoff"
    assert res["should_offer"] is False


def test_index_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Orvalho Atelier" in res.content
