"""Adversarial coupling tests. Every attack must fail closed in the prescribed
direction. History semantics under test: a commitment must remain an ancestor
(no rewrite); benign appends between evaluation and execution do NOT invalidate;
revocation / safety escalation / mismatch DO."""
from dataclasses import replace

from lexicon_governor import (FailClosed, SendEmail, ModifyFile, SpendMoney,
                              GovernanceConstraintRecord)
from lexicon_governor.records import hash_obj
from tests.harness import make_gov, ALLOWLIST, APPROVED_CATS


def _email(gov, auth_id, to="alice@example.com"):
    act = SendEmail(to, "hi", ALLOWLIST)
    rec = gov.evaluate(act, auth_id)
    return act, rec


def test_stale_decision():
    gov, clock, auth_id = make_gov()
    act, rec = _email(gov, auth_id)
    clock.advance(301)  # past the 300s evaluation TTL
    try:
        gov.execute(rec, act, auth_id)
    except FailClosed as e:
        assert e.reason == "GOVERNANCE_EXPIRED", e.reason
        return "adversarial: stale decision fails closed (expired)"
    raise AssertionError("stale decision executed")


def test_action_substitution():
    gov, _, auth_id = make_gov()
    act, rec = _email(gov, auth_id)
    other = SendEmail("bob@example.com", "hi", ALLOWLIST)
    try:
        gov.execute(rec, other, auth_id)
    except FailClosed as e:
        assert e.reason == "ACTION_MISMATCH", e.reason
        return "adversarial: substituted action fails closed (mismatch)"
    raise AssertionError("substituted action executed")


def test_revocation_after_eval():
    gov, _, auth_id = make_gov()
    act, rec = _email(gov, auth_id)
    gov.revoke_authority(auth_id)
    try:
        gov.execute(rec, act, auth_id)
    except FailClosed as e:
        assert e.reason in ("AUTHORITY_REVOKED_AFTER_EVAL", "AUTHORITY_REVOKED"), e.reason
        return "adversarial: post-eval revocation fails closed"
    raise AssertionError("executed on revoked authority")


def test_benign_history_append_ok():
    gov, _, auth_id = make_gov()
    act, rec = _email(gov, auth_id)
    # An unrelated action executes in between: history grows, commitment stays
    # ancestral, nothing invalidating happened -> original may still execute.
    act2 = ModifyFile("/workspace/notes.txt", versioned=True)
    rec2 = gov.evaluate(act2, auth_id)
    gov.execute(rec2, act2, auth_id)
    out = gov.execute(rec, act, auth_id)
    assert out.yield_payload["sent_to"] == "alice@example.com"
    return "adversarial: benign intervening history does not invalidate"


def test_malformed_omitted_u2():
    gov, _, auth_id = make_gov()
    act = SendEmail("alice@example.com", "hi", ALLOWLIST,
                    extra_u=[("U_scale", False)])
    proposed = gov.lexicon.evaluate(act, gov._live_authority(auth_id),
                                    gov.history, gov.rails, gov.clock.now())
    tampered = replace(proposed, unresolved=())  # U omitted
    try:
        gov.admit(tampered, act, auth_id)
    except FailClosed as e:
        assert e.reason == "LEXICON_MISMATCH", e.reason
        return "adversarial: omitted U fails closed (mismatch)"
    raise AssertionError("omitted-U record admitted")


def test_forged_provenance():
    gov, _, auth_id = make_gov()
    act = SendEmail("alice@example.com", "hi", ALLOWLIST)
    proposed = gov.lexicon.evaluate(act, gov._live_authority(auth_id),
                                    gov.history, gov.rails, gov.clock.now())
    tampered = replace(proposed, provenance=("attacker", "lexicon-eval"))
    try:
        gov.admit(tampered, act, auth_id)
    except FailClosed as e:
        assert e.reason in ("PROVENANCE_FORGED", "LEXICON_MISMATCH"), e.reason
        return "adversarial: forged provenance fails closed"
    raise AssertionError("forged provenance admitted")


def test_replayed_record():
    gov, _, auth_id = make_gov()
    act = SendEmail("alice@example.com", "hi", ALLOWLIST)
    rec1 = gov.evaluate(act, auth_id)
    rec2 = gov.evaluate(act, auth_id)  # supersedes rec1
    assert rec1.constraint_id != rec2.constraint_id
    try:
        gov.execute(rec1, act, auth_id)
    except FailClosed as e:
        assert e.reason == "GOVERNANCE_SUPERSEDED", e.reason
        return "adversarial: replayed (superseded) record fails closed"
    raise AssertionError("replayed record executed")


def test_safety_downgrade_rejected():
    gov, _, auth_id = make_gov()
    act = SpendMoney(40.0, "api", APPROVED_CATS)  # >significant -> T_irr -> YELLOW
    proposed = gov.lexicon.evaluate(act, gov._live_authority(auth_id),
                                    gov.history, gov.rails, gov.clock.now())
    assert proposed.safety_state == "YELLOW", proposed.safety_state
    tampered = replace(proposed, safety_state="GREEN")  # downgrade w/o reassessment
    try:
        gov.admit(tampered, act, auth_id)
    except FailClosed as e:
        assert e.reason == "LEXICON_MISMATCH", e.reason
        return "adversarial: safety downgrade without reassessment rejected"
    raise AssertionError("downgraded safety admitted")


def test_rail_loosening_rejected():
    gov, _, auth_id = make_gov()
    act = SendEmail("alice@example.com", "hi", ALLOWLIST)
    rec = gov.evaluate(act, auth_id)
    # Forge a sealed record whose scope exceeds the granted authority.
    forged = GovernanceConstraintRecord(
        **{**rec.__dict__, "constraint_id": "gcr-forged",
           "scope_after": frozenset(set(rec.scope_after) | {"NUKES"})}).sealed()
    gov.issued[forged.constraint_id] = forged
    try:
        gov.execute(forged, act, auth_id)
    except FailClosed as e:
        assert e.reason == "RATCHET_VIOLATION", e.reason
        return "adversarial: rail-loosening output rejected (ratchet)"
    raise AssertionError("loosened rail executed")


def test_execution_without_evaluation():
    gov, _, auth_id = make_gov()
    act = SendEmail("alice@example.com", "hi", ALLOWLIST)
    fake = GovernanceConstraintRecord(
        constraint_id="gcr-fake", source_rail="x",
        canonical_action_id=act.canonical_id(),
        action_params_hash=hash_obj(act.params),
        history_commitment=gov.history.head, history_seq=gov.history.seq,
        cumadm_verdict="Pass", safety_state="GREEN", fired_triggers=(),
        unresolved=(), provenance=("test-principal",), recovery_required=None,
        scope_after=frozenset({"SEND_EMAIL"}),
        issued_at=gov.clock.now(), expires_at=gov.clock.now() + 300,
        supersedes=None).sealed()
    try:
        gov.execute(fake, act, auth_id)
    except FailClosed as e:
        assert e.reason == "GOVERNANCE_UNKNOWN", e.reason
        return "adversarial: execution without evaluation fails closed"
    raise AssertionError("unevaluated action executed")


def test_valid_constraint_missing_authority():
    gov, _, auth_id = make_gov()
    act = SendEmail("alice@example.com", "hi", ALLOWLIST)
    rec = gov.evaluate(act, auth_id)
    del gov.authorities[auth_id]  # authority record gone
    try:
        gov.execute(rec, act, auth_id)
    except FailClosed as e:
        assert e.reason == "NO_AUTHORITY", e.reason
        return "adversarial: missing AuthorityRecord fails closed"
    raise AssertionError("executed without authority")


TESTS = [test_stale_decision, test_action_substitution, test_revocation_after_eval,
         test_benign_history_append_ok, test_malformed_omitted_u2,
         test_forged_provenance, test_replayed_record, test_safety_downgrade_rejected,
         test_rail_loosening_rejected, test_execution_without_evaluation,
         test_valid_constraint_missing_authority]
