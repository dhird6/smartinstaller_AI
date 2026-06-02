"""Unit tests for configuration management (MAINT-02)."""

from smartinstall.agent.infrastructure.config_provider import ConfigProvider


def test_load_config(temp_config) -> None:
    provider = ConfigProvider(temp_config)
    config = provider.load()
    assert config.config_version == "1.0"
    assert config.output_root.is_absolute()
