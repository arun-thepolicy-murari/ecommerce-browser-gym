from agents.openai_agent import _chat_request


def test_openrouter_hy3_uses_supported_token_parameter(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    for model in ("tencent/hy3", "tencent/hy3:free"):
        request = _chat_request(model, [{"role": "user", "content": "x"}])
        assert request["max_tokens"] == 2048
        assert "max_completion_tokens" not in request
        assert request["extra_body"] == {
            "provider": {"require_parameters": True},
        }


def test_regular_openai_model_keeps_existing_parameter(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    request = _chat_request("gpt-5.4", [{"role": "user", "content": "x"}])
    assert request["max_completion_tokens"] == 2048
    assert "max_tokens" not in request
    assert "extra_body" not in request
