"""Shared harness: Governor with a test authority covering all four classes."""
from lexicon_governor import (Governor, Clock, ALL_RAILS, AuthorityRecord)


def make_gov():
    clock = Clock()
    gov = Governor(ALL_RAILS, clock)
    auth = AuthorityRecord(
        record_id="auth-test-1",
        granted_by="test-principal",
        holder="agent-1",
        scope=frozenset({"SEND_EMAIL", "MODIFY_FILE", "SPEND_MONEY",
                         "EXTERNAL_API_CALL"}),
        rails=tuple(ALL_RAILS.keys()),
        provenance=("test-principal",),
        valid_until=clock.now() + 86400,
    )
    gov.grant_authority(auth)
    return gov, clock, auth.record_id


ALLOWLIST = frozenset({"alice@example.com", "bob@example.com"})
APPROVED_CATS = frozenset({"api", "infra"})
VERIFIED_HOSTS = frozenset({"api.example.com"})
