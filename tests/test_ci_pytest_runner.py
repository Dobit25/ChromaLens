from scripts.run_ci_pytest import github_command_escape


def test_github_command_escape_preserves_failure_text_as_one_annotation() -> None:
    assert github_command_escape("first%\r\nsecond") == "first%25%0D%0Asecond"
