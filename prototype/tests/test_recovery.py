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



def test_s3_envelope_expansion():
    gov, _, auth_id = make_gov()
    # Warranted history: 6 similar proposals, all approved by the principal.
    for i in range(6):
        p = gov.propose_rail_change("agent-1", auth_id, "spend-txn",
                                    "max_per_txn", 50.0 + (i + 1) * 5,
                                    f"calibration round {i}")
        gov.approve_rail_changes([p.proposal_id], acting_principal="test-principal")
    # One intervention: the principal rejects an out-of-range proposal.
    p_bad = gov.propose_rail_change("agent-1", auth_id, "spend-txn",
                                    "max_per_txn", 5000.0, "yolo")
    gov.reject_proposal(p_bad.proposal_id, acting_principal="test-principal",
                        reason="exceeds plausible calibration range")
    # The report learns the pattern from history, not from the agent's claims.
    rep = gov.delegation_report()
    r = rep["rails"]["spend-txn"]
    assert (r["applied"], r["rejected"]) == (6, 1), r
    assert r["max_applied_new_value"] == 80.0
    assert r["min_rejected_new_value"] == 5000.0
    assert "spend-txn" in rep["near_routine"]
    # Competence produces the information: the agent grounds its proposal in
    # the report's numbers; the principal disposes.
    rationale = (f"{r['applied']}/{r['applied'] + r['rejected']} applied; "
                 f"max applied {r['max_applied_new_value']}, "
                 f"min rejected {r['min_rejected_new_value']}; "
                 f"bounds set below rejection threshold")
    sdp = gov.propose_standing_delegation(
        "agent-1", auth_id, "spend-txn",
        bounds={"fields": ["max_per_txn"], "max_new_value": 100.0},
        review_ttl=3600.0, rationale=rationale)
    sd = gov.grant_standing_delegation(sdp.proposal_id,
                                       acting_principal="test-principal")
    # In-bounds proposal applies with no per-item ceremony — but the full
    # RegimeDelta record is written and authority terminates in the principal.
    p2 = gov.propose_rail_change("agent-1", auth_id, "spend-txn", "max_per_txn",
                                 90.0, "continued calibration")
    d = gov.apply_within_standing(p2.proposal_id, acting_holder="agent-1")
    assert d.approved_by == "test-principal"
    assert gov.rails["spend-txn"].max_per_txn == 90.0
    assert d.justification == "continued calibration"
    # Out-of-bounds cannot ride the standing delegation.
    p3 = gov.propose_rail_change("agent-1", auth_id, "spend-txn", "max_per_txn",
                                 500.0, "too far")
    try:
        gov.apply_within_standing(p3.proposal_id, acting_holder="agent-1")
        raise AssertionError("out-of-bounds applied")
    except FailClosed as e:
        assert e.reason == "STANDING_BOUNDS_EXCEEDED", e.reason
    # Expiry returns control to the full ceremony.
    gov.clock.advance(3601.0)
    p4 = gov.propose_rail_change("agent-1", auth_id, "spend-txn", "max_per_txn",
                                 95.0, "after expiry")
    try:
        gov.apply_within_standing(p4.proposal_id, acting_holder="agent-1")
        raise AssertionError("expired standing applied")
    except FailClosed as e:
        assert e.reason == "STANDING_EXPIRED", e.reason
    # Revocation likewise: the principal's ordinary path still works.
    gov.revoke_standing_delegation(sd.delegation_id,
                                   acting_principal="test-principal")
    p5 = gov.propose_rail_change("agent-1", auth_id, "spend-txn", "max_per_txn",
                                 95.0, "after revocation")
    try:
        gov.apply_within_standing(p5.proposal_id, acting_holder="agent-1")
        raise AssertionError("revoked standing applied")
    except FailClosed as e:
        assert e.reason == "STANDING_REVOKED", e.reason
    gov.approve_rail_changes([p5.proposal_id], acting_principal="test-principal")
    assert gov.rails["spend-txn"].max_per_txn == 95.0
    return ("recovery S3: envelope expands via learned standing delegation; "
            "bounds, expiry, and revocation return control")


TESTS = [test_s1_recovery_batch_delegation, test_s2_recovery_regime_delta,
         test_s2_recovery_batch_review, test_batch_atomicity_no_double_apply,
         test_s3_envelope_expansion]
