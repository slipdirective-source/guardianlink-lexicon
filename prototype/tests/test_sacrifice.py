"""Executable sacrifice tests (companion to coupling/sacrifice-test.md).

S1: opaque sub-agent authority inheritance must fail; explicit delegation
     (each sub-agent with its own AuthorityRecord) must work.
S2: the Lexicon/governed layer cannot loosen its own rails — a proposal
     derived under relaxed rails must be rejected at admission.
"""
from lexicon_governor import FailClosed, SendEmail, SpendMoney
from tests.harness import make_gov, ALLOWLIST, APPROVED_CATS


def test_s1a_opaque_inheritance_fails():
    """A sub-agent acting under the parent's record: HOLDER_MISMATCH."""
    gov, _, auth_id = make_gov()
    act = SendEmail("alice@example.com", "hi", ALLOWLIST)
    rec = gov.evaluate(act, auth_id)
    try:
        gov.execute(rec, act, auth_id, acting_principal="sub-agent-1")
    except FailClosed as e:
        assert e.reason == "HOLDER_MISMATCH", e.reason
        return "sacrifice S1a: opaque inheritance fails closed (holder mismatch)"
    raise AssertionError("sub-agent executed on parent's authority")


def test_s1b_explicit_delegation_works():
    """The legitimate form: explicit per-agent delegation with its own record,
    visible provenance, and narrowed-or-equal scope. The overhead is the price."""
    gov, _, auth_id = make_gov()
    sub = gov.delegate(auth_id, "sub-agent-1", scope={"SEND_EMAIL"})
    assert sub.provenance[:1] == ("test-principal,",) or \
        sub.provenance[0] == "test-principal"
    assert auth_id in sub.provenance, "delegation must chain to the parent grant"
    act = SendEmail("alice@example.com", "hi", ALLOWLIST)
    rec = gov.evaluate(act, sub.record_id)
    out = gov.execute(rec, act, sub.record_id, acting_principal="sub-agent-1")
    assert out.yield_payload["sent_to"] == "alice@example.com"
    # ...and the delegation cannot widen scope.
    try:
        gov.delegate(auth_id, "sub-agent-2", scope={"SEND_EMAIL", "NUKES"})
        raise AssertionError("widening delegation allowed")
    except FailClosed as e:
        assert e.reason == "DELEGATION_WIDENING", e.reason
    return "sacrifice S1b: explicit delegation works; widening refused"


def test_s2_rail_self_modification_fails():
    """A Lexicon proposal derived under loosened rails is rejected at
    admission: the governed layer cannot relax its own constraints."""
    gov, _, auth_id = make_gov()
    auth = gov._live_authority(auth_id)
    relaxed = dict(gov.rails)
    tampered = dict(relaxed)
    # Adversary's move: re-derive the proposal under a $5000 txn rail.
    from lexicon_governor.actions import SpendTxnRail
    loose = SpendTxnRail()
    loose.max_per_txn = 5000.0
    tampered["spend-txn"] = loose
    act = SpendMoney(100.0, "api", APPROVED_CATS)
    proposed = gov.lexicon.evaluate(act, auth, gov.history, tampered,
                                    gov.clock.now())
    assert proposed.cumadm_verdict == "Pass"  # passes under the loose rails
    try:
        gov.admit(proposed, act, auth_id)  # Governor re-derives with real rails
        raise AssertionError("loosened-rail proposal admitted")
    except FailClosed as e:
        assert e.reason in ("LEXICON_MISMATCH", "CUMADM_FAIL"), e.reason
        return "sacrifice S2: self-loosened rails rejected at admission"


TESTS = [test_s1a_opaque_inheritance_fails, test_s1b_explicit_delegation_works,
         test_s2_rail_self_modification_fails]
