from app.scoring import normalize_unapproved_hosts


def test_only_exact_approved_https_host_passes():
    assert (
        normalize_unapproved_hosts(["https://help.bank.example/path"], {"help.bank.example"}) == []
    )
    for url in (
        "http://help.bank.example",
        "https://help.bank.example.attacker.test",
        "https://attacker.test@help.bank.example",
        "https://help.bank.example.attacker.test",
        "https://help.bank.example:444",
        "https://127.0.0.1",
        "https://help.bаnk.example",  # Cyrillic a: visual lookalike, not approved host
        "javascript://help.bank.example",
        "https://[invalid-host",
    ):
        assert normalize_unapproved_hosts([url], {"help.bank.example"}), url


def test_host_matching_is_not_substring_matching():
    assert normalize_unapproved_hosts(["https://notbank.example"], {"bank.example"}) == [
        "notbank.example"
    ]


def test_only_typed_actions_are_scored_by_campaign():
    # The scorer deliberately receives typed actions, not inert memo quotes.
    assert normalize_unapproved_hosts([], {"help.bank.example"}) == []
