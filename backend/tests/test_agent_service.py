import json
from io import BytesIO

from app import agent_service


def test_sanitize_prompt_masks_common_sensitive_values():
    raw = (
        "分析客户质量，联系人:张三，邮箱 test@example.com，"
        "电话 13812345678，服务器 10.20.30.40，password=SuperSecret123"
    )
    safe = agent_service.sanitize_prompt(raw)
    for secret in ["张三", "test@example.com", "13812345678", "10.20.30.40", "SuperSecret123"]:
        assert secret not in safe
    assert "[邮箱已脱敏]" in safe
    assert "[手机号已脱敏]" in safe
    assert "[IP已脱敏]" in safe
    assert "[凭据已脱敏]" in safe


def test_local_agent_fallback_returns_governance_steps(monkeypatch):
    for key in ["LLM_API_KEY", "LLM_API_BASE_URL", "LLM_MODEL"]:
        monkeypatch.delenv(key, raising=False)
    result = agent_service.run_governance_agent(
        "请帮我设计客户主数据质量规则",
        {"assets": 12, "standards": 8, "quality_rules": 6, "open_issues": 2,
         "unclassified_columns": 9, "sensitive_columns": 4},
    )
    assert result["provider_status"] == "local_fallback"
    assert result["requires_human_approval"] is True
    assert "数据质量" in result["reply"]
    assert "数据资产 12 项" in result["reply"]
    assert "未分级字段 9 个" in result["reply"]
    assert "敏感及高度敏感字段 4 个" in result["reply"]


def test_external_model_receives_only_sanitized_prompt_and_aggregate_context(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-api-key")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://llm.example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_EXTERNAL_ENABLED", "true")
    captured = {}

    class Response(BytesIO):
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            self.close()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return Response(json.dumps({
            "choices": [{"message": {"content": "建议先梳理数据标准。"}}]
        }).encode("utf-8"))

    monkeypatch.setattr(agent_service.urllib.request, "urlopen", fake_urlopen)
    result = agent_service.run_governance_agent(
        "请分析质量问题，联系人:李四，电话 13912345678，token=private-token",
        {"assets": 3, "standards": 4, "quality_rules": 5, "open_issues": 1,
         "unclassified_columns": 6, "sensitive_columns": 2},
        allow_external_model=True,
    )

    serialized = json.dumps(captured["body"], ensure_ascii=False)
    for private_value in ["李四", "13912345678", "private-token", "10.0.0.1"]:
        assert private_value not in serialized
    assert "asset_count" in serialized
    assert "unclassified_column_count" in serialized
    assert "sensitive_column_count" in serialized
    assert "6" in serialized
    assert result["provider_status"] == "connected"
    assert result["sanitized"] is True
    assert result["requires_human_approval"] is True
    assert captured["url"] == "https://llm.example.test/v1/chat/completions"


def test_external_model_requires_explicit_user_consent(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-api-key")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://llm.example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_EXTERNAL_ENABLED", "true")

    def unexpected_call(*_args, **_kwargs):
        raise AssertionError("external model must not be called without user consent")

    monkeypatch.setattr(agent_service.urllib.request, "urlopen", unexpected_call)
    result = agent_service.run_governance_agent("请给出数据标准建议", {"assets": 1})
    assert result["provider_status"] == "consent_required"
    assert result["requires_human_approval"] is True


def test_server_switch_can_block_external_model_even_with_user_consent(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-api-key")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://llm.example.test/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_EXTERNAL_ENABLED", "false")

    def unexpected_call(*_args, **_kwargs):
        raise AssertionError("server policy must block external model calls")

    monkeypatch.setattr(agent_service.urllib.request, "urlopen", unexpected_call)
    result = agent_service.run_governance_agent(
        "请给出数据标准建议", {"assets": 1}, allow_external_model=True
    )
    assert result["provider_status"] == "external_disabled"
