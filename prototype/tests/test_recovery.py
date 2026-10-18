"""Leverage recovery: the hard constraint redirects optimization, it doesn't end it.

S1-recovery: batch sub-delegation recovers scaling leverage with zero opacity —
one principal decision mints N individually-visible, individually-revocable records.
S2-recovery: batch RegimeDelta approval recovers rail-update leverage — the agent
proposes with justification, the principal disposes in one action, each change
keeps its own record. The agent can never approve its own proposals.
"""
from lexicon_governor import FailClosed, SendEmail, SpendMoney
from tests.harness import make_gov, ALLOWLIST, APPROVED_CATS


def test_s1_recovery_batch_delegation():
    gov, _, auth_id = make_gov()
    holders = [f"sub-{i:03d}" for i in range(50)]
    subs = gov.delegate_batch(auth_id, holders, scope={"SEND_EMAIL"})
    assert len(subs) == 50
    # Every sub-agent individually visible, chained, and executable...
    for sub in subs:
        assert sub.provenance[0] == "test-principal"
        assert auth_id in sub.provenance
    act = SendEmail("alice@example.com", "hi", ALLOWLIST)
    rec = gov.evaluate(act, subs[7].record_id)
    out = gov.execute(rec, act, subs[7].record_id, acting_principal="sub-007")
    assert out.yield_payload["sent_to"] == "alice@example.com"
    # ...and individually revocable: revoking one leaves the rest working.
    gov.revoke_authority(subs[7].record_id)
    rec2 = gov.evaluate(act, subs[8].record_id)
    gov.execute(rec2, act, subs[8].record_id, acting_principal="sub-008")
    act3 = SendEmail("bob@example.com", "hi", ALLOWLIST)
    try:
        gov.evaluate(act3, subs[7].record_id)
        raise AssertionError("revoked sub-agent evaluated")
    except FailClosed as e:
        assert e.reason == "AUTHORITY_REVOKED", e.reason
    return "recovery S1: 50 sub-agents, one decision, each visible and revocable"


def test_s2_recovery_regime_delta():
    gov, _, auth_id = make_gov()
    # The $60 spend is blocked under the current $50 txn rail.
    act = SpendMoney(60.0, "api", APPROVED_CATS)
    try:
        gov.evaluate(act, auth_id)
        raise AssertionError("should have failed under $50 rail")
    except FailClosed as e:
        assert e.reason == "CUMADM_FAIL", e.reason
    # Agent proposes a rail change with independent justification...
    prop = gov.propose_rail_change("agent-1", auth_id, "spend-txn", "max_per_txn",
                                   75.0, "measured false-positive rate on "
                                   "legitimate infra spend below $75")
    # ...but cannot approve its own proposal.
    try:
        gov.approve_rail_changes([prop.proposal_id], acting_principal="agent-1")
        raise AssertionError("agent approved its own rail change")
    except FailClosed as e:
        assert e.reason == "NOT_GRANTING_PRINCIPAL", e.reason
    # The granting principal disposes in one action; the delta keeps its record.
    deltas = gov.approve_rail_changes([prop.proposal_id],
                                      acting_principal="test-principal")
    assert len(deltas) == 1
    d = deltas[0]
    assert d.justification.startswith("measured false-positive")
    assert d.approved_by == "test-principal"
    assert gov.rails["spend-txn"].max_per_txn == 75.0
    # The previously blocked spend now passes through the full path.
    rec = gov.evaluate(act, auth_id)
    gov.execute(rec, act, auth_id, acting_principal="agent-1")
    return "recovery S2: RegimeDelta applied by principal; agent cannot self-approve"


def test_s2_recovery_batch_review():
    gov, _, auth_id = make_gov()
    p1 = gov.propose_rail_change("agent-1", auth_id, "spend-txn", "max_per_txn",
                                 75.0, "infra spend calibration")
    p2 = gov.propose_rail_change("agent-1", auth_id, "email-volume",
                                 "max_per_day", 10, "batch notification workload")
    # One principal action disposes of both; each keeps its own justification.
    deltas = gov.approve_rail_changes([p1.proposal_id, p2.proposal_id],
                                      acting_principal="test-principal")
    assert len(deltas) == 2
    assert deltas[0].justification != deltas[1].justification
    assert gov.rails["email-volume"].max_per_day == 10
    return "recovery S2: batch review disposes N proposals, one record each"


def test_batch_atomicity_no_double_apply():
    gov, _, auth_id = make_gov()
    p = gov.propose_rail_change("agent-1", auth_id, "spend-txn", "max_per_txn",
                                75.0, "calibration")
    gov.approve_rail_changes([p.proposal_id], acting_principal="test-principal")
    # The same proposal cannot be applied twice: one justification, one change.
    try:
        gov.approve_rail_changes([p.proposal_id], acting_principal="test-principal")
        raise AssertionError("double-apply allowed")
    except FailClosed as e:
        assert e.reason == "UNKNOWN_PROPOSAL", e.reason
    assert gov.rails["spend-txn"].max_per_txn == 75.0
    return "recovery: batch items apply exactly once (atomic accountability)"


TESTS = [test_s1_recovery_batch_delegation, test_s2_recovery_regime_delta,
         test_s2_recovery_batch_review, test_batch_atomicity_no_double_apply]
