from ccpragents.infrastructure.settings import SettingsService


def test_get_github_settings_includes_advanced_keys():
    settings = SettingsService()
    github_settings = settings.get_github_settings()

    assert github_settings["retry_on_404"] is False
    assert github_settings["retry_on_403"] is True
    assert github_settings["retry_on_500"] is True
    assert github_settings["circuit_breaker_enabled"] is True
    assert github_settings["diff_max_workers"] == 4
    assert isinstance(github_settings["ignore_patterns"], tuple)
    assert isinstance(github_settings["valid_extensions"], tuple)
