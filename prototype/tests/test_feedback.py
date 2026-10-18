"""Feedback loop: sealed consequences return as Yield/evidence.

Successful execution must NOT automatically establish: correctness of the
Lexicon reasoning, correctness of the governing model, causal explanation,
future admissibility, or expanded authority.
"""
from lexicon_governor import FailClosed, SpendMoney, SendEmail
from tests.harness import make_gov, APPROVED_CATS, ALLOWLIST


def test_consequence_returns_as_yield():
    gov, _, auth_id = make_gov()
    act = SpendMoney(20.0, "api", APPROVED_CATS)
    rec = gov.evaluate(act, auth_id)
    out = gov.execute(rec, act, auth_id, "agent-1")
    # The sealed consequence is chained into history and visible to the next
    # CumAdm evaluation (evidence, not proof).
    assert out.prev_head != out.new_head
    assert gov.history.head == out.new_head
    # A second identical spend sees the first in its cumulative evaluation.
    act2 = SpendMoney(190.0 - 20.0, "api", APPROVED_CATS)
    try:
        gov.evaluate(act2, auth_id)
        raise AssertionError("cumulative evidence ignored")
    except FailClosed as e:
        assert e.reason == "CUMADM_FAIL", e.reason
    return "feedback: consequence returns as evidence for next CumAdm"


def test_no_auto_promotion():
    gov, _, auth_id = make_gov()
    act = SendEmail("alice@example.com", "hi", ALLOWLIST)
    rec = gov.evaluate(act, auth_id)
    gov.execute(rec, act, auth_id, "agent-1")
    # Success does not license the next action: fresh evaluation required.
    # Reusing the old record for a new (identical-params) action fails on
    # supersession/history; a new evaluation is the only path.
    act2 = SendEmail("alice@example.com", "hi", ALLOWLIST)
    try:
        gov.execute(rec, act2, auth_id, "agent-1")
        raise AssertionError("old record reused")
    except FailClosed:
        pass
    rec2 = gov.evaluate(act2, auth_id)  # fresh evaluation: the honest path
    gov.execute(rec2, act2, auth_id, "agent-1")
    return "feedback: no auto-promotion; each execution needs fresh evaluation"


def test_authority_not_expanded_by_success():
    gov, _, auth_id = make_gov()
    before = set(gov._live_authority(auth_id).scope)
    act = SendEmail("alice@example.com", "hi", ALLOWLIST)
    rec = gov.evaluate(act, auth_id)
    gov.execute(rec, act, auth_id, "agent-1")
    after = set(gov._live_authority(auth_id).scope)
    assert before == after, "successful execution must not expand authority"
    assert set(rec.scope_after) <= before, "ratchet: scope_after ⊆ scope_before"
    return "feedback: success expands nothing (ratchet holds)"


TESTS = [test_consequence_returns_as_yield, test_no_auto_promotion,
         test_authority_not_expanded_by_success]
