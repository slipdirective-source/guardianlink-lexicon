"""Adversarial: crash-consistency and clock attacks.

The crash tests target the most dangerous window in execute(): between the
mutation (perform) and the seal (history append). The honest result the
architecture must produce there is not at-most-once — which is unachievable
without substrate cooperation — but *visible* at-most-once-attempt: an
orphaned intent the audit surfaces, so no one blind-retries into a double
mutation.

The clock tests target time as an attack surface: stale evaluations and
expired authorities must fail closed when the clock moves past them.
"""
from lexicon_governor import FailClosed, SendEmail
from tests.harness import make_gov, ALLOWLIST


def test_crash_orphan_is_visible_not_silent():
    # A TRUE crash: intent recorded, substrate mutated, process dies before
    # the seal — and before even the abort handler runs. This is the state a
    # real crash leaves behind (constructed directly; an exception is a
    # handled failure, not a crash).
    gov, _, auth_id = make_gov()
    act = SendEmail("alice@example.com", "hi", ALLOWLIST)
    rec = gov.evaluate(act, auth_id)
    gov.consumed.add(rec.constraint_id)
    gov.history.append("execution started",
                       {"action": rec.canonical_action_id,
                        "constraint": rec.constraint_id})
    # substrate mutates here; process dies; no abort entry, no seal.
    orphans = gov.crash_audit()
    assert len(orphans) == 1
    assert orphans[0]["payload"]["constraint"] == rec.constraint_id
    kinds = [e["kind"] for e in gov.history.entries]
    assert "execution" not in kinds
    return "crash: orphaned intent visible; blind retry would be operator error"


def test_aborted_execution_recorded_not_orphaned():
    # The HANDLED failure: perform() raises, the abort is recorded, the
    # mutation happened exactly once, and the spent record cannot be reused.
    gov, _, auth_id = make_gov()
    mutations = []
    act = SendEmail("alice@example.com", "hi", ALLOWLIST)

    def evil_perform():
        mutations.append(1)
        raise RuntimeError("failure during perform")

    act.perform = evil_perform
    rec = gov.evaluate(act, auth_id)
    try:
        gov.execute(rec, act, auth_id, acting_principal="agent-1")
        raise AssertionError("failure did not propagate")
    except RuntimeError:
        pass
    assert len(mutations) == 1
    kinds = [e["kind"] for e in gov.history.entries]
    assert "execution aborted" in kinds
    assert "execution" not in kinds
    # A recorded abort is not an orphan — the failure is in the audit trail.
    assert gov.crash_audit() == []
    # The spent record cannot be reused for a silent second attempt.
    try:
        gov.execute(rec, act, auth_id, acting_principal="agent-1")
        raise AssertionError("spent record reused")
    except FailClosed as e:
        assert e.reason == "GOVERNANCE_CONSUMED", e.reason
    return "abort: recorded, single mutation, spent record dead"


def test_crash_audit_clean_on_happy_path():
    gov, _, auth_id = make_gov()
    for to in ["alice@example.com", "bob@example.com"]:
        act = SendEmail(to, "hi", ALLOWLIST)
        rec = gov.evaluate(act, auth_id)
        gov.execute(rec, act, auth_id, acting_principal="agent-1")
    assert gov.crash_audit() == []
    return "crash: no orphans on the clean path"


def test_clock_stale_evaluation_refused():
    gov, clock, auth_id = make_gov()
    act = SendEmail("alice@example.com", "hi", ALLOWLIST)
    rec = gov.evaluate(act, auth_id)
    clock.advance(301.0)  # past EVAL_TTL=300
    try:
        gov.execute(rec, act, auth_id, acting_principal="agent-1")
        raise AssertionError("stale evaluation executed")
    except FailClosed as e:
        assert e.reason == "GOVERNANCE_EXPIRED", e.reason
    return "clock: evaluation past TTL refused"


def test_clock_expired_authority_refused():
    gov, clock, auth_id = make_gov()
    clock.advance(86401.0)  # past valid_until
    act = SendEmail("alice@example.com", "hi", ALLOWLIST)
    try:
        gov.evaluate(act, auth_id)
        raise AssertionError("expired authority evaluated")
    except FailClosed as e:
        assert e.reason == "AUTHORITY_EXPIRED", e.reason
    return "clock: expired authority refused"


TESTS = [test_crash_orphan_is_visible_not_silent,
         test_aborted_execution_recorded_not_orphaned,
         test_crash_audit_clean_on_happy_path,
         test_clock_stale_evaluation_refused,
         test_clock_expired_authority_refused]
