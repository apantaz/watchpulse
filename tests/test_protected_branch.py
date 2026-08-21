from watchpulse.dev.protected_branch import branch_name, main


def test_branch_name_normalizes_full_ref() -> None:
    assert branch_name("refs/heads/master") == "master"


def test_protected_branch_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("PRE_COMMIT_REMOTE_BRANCH", "refs/heads/main")

    assert main() == 1


def test_feature_branch_is_allowed(monkeypatch) -> None:
    monkeypatch.setenv("PRE_COMMIT_REMOTE_BRANCH", "refs/heads/feat/dbt")

    assert main() == 0
