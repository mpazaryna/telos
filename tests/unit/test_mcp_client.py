"""Unit tests for telos.mcp_client."""

from pathlib import Path

from telos.mcp_client import _interpolate_env, load_mcp_config


class TestLoadMcpConfig:
    """Tests for load_mcp_config."""

    def test_loads_valid_config(self, tmp_path):
        config = tmp_path / "mcp.json"
        config.write_text(
            '{"mcpServers": {"clickup": {"type": "sse", "url": "https://mcp.clickup.com/sse"}}}'
        )
        result = load_mcp_config(config)
        assert "mcpServers" in result
        assert "clickup" in result["mcpServers"]
        assert result["mcpServers"]["clickup"]["url"] == "https://mcp.clickup.com/sse"

    def test_loads_config_with_headers(self, tmp_path):
        config = tmp_path / "mcp.json"
        config.write_text(
            '{"mcpServers": {"svc": {"type": "sse", "url": "https://example.com/sse", '
            '"headers": {"Authorization": "Bearer ${TOKEN}"}}}}'
        )
        result = load_mcp_config(config)
        headers = result["mcpServers"]["svc"]["headers"]
        assert headers["Authorization"] == "Bearer ${TOKEN}"

    def test_empty_servers(self, tmp_path):
        config = tmp_path / "mcp.json"
        config.write_text('{"mcpServers": {}}')
        result = load_mcp_config(config)
        assert result["mcpServers"] == {}


class TestInterpolateEnv:
    """Tests for _interpolate_env."""

    def test_replaces_env_var(self):
        result = _interpolate_env("Bearer ${TOKEN}", {"TOKEN": "abc123"})
        assert result == "Bearer abc123"

    def test_replaces_multiple_vars(self):
        result = _interpolate_env(
            "${USER}:${PASS}", {"USER": "admin", "PASS": "secret"}
        )
        assert result == "admin:secret"

    def test_missing_var_replaced_with_empty(self):
        result = _interpolate_env("Bearer ${MISSING}", {})
        assert result == "Bearer "

    def test_no_vars_unchanged(self):
        result = _interpolate_env("plain text", {})
        assert result == "plain text"

    def test_var_at_start(self):
        result = _interpolate_env("${KEY}", {"KEY": "value"})
        assert result == "value"
