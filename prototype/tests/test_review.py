"""Third domain for the ceremony-batching principle: retrospective oversight.

S1/S2/S3 batch *prospective authorization*. This batches *retrospective
review* — structurally different, same mechanical test: batching is
legitimate only while accountability remains atomically reconstructible.
The abuse tests matter most: review must not become a backdoor for control
(a flagged item is not a revoked authority), and no item may pass through
a review session without its own disposition.
"""
from lexicon_governor import FailClosed, SendEmail
from tests.harness import make_gov, ALLOWLIST


def _three_executions():
    gov, _, auth_id = make_gov()
    seqs = []
    for to, subject in [("alice@example.com", "hi"),
                          ("bob@example.com", "hi"),
                          ("alice@example.com", "follow-up")]:
        act = SendEmail(to, subject, ALLOWLIST)
        rec = gov.evaluate(act, auth_id)
        gov.execute(rec, act, auth_id, acting_principal="agent-1")
        seq = len(gov.history.entries) - 1
        assert gov.history.entries[seq]["kind"] == "execution"
        seqs.append(seq)
    return gov, auth_id, seqs


def test_review_third_domain():
    gov, auth_id, seqs = _three_executions()
    dispositions = {seqs[0]: "acknowledged", seqs[1]: "flagged",
                    seqs[2]: "acknowledged"}
    sid = gov.submit_review(auth_id, seqs, dispositions,
                            acting_principal="test-principal",
                            note="weekly review")
    assert sid.startswith("rev-")
    # Atomic reconstructibility: from the audit trail alone, recover exactly
    # what was decided about each item.
    sess = gov.history.entries[-1]
    assert sess["kind"] == "review session"
    recovered = {it["seq"]: it["disposition"]
                 for it in sess["payload"]["items"]}
    assert recovered == dispositions
    assert sess["payload"]["reviewed_by"] == "test-principal"
    return "review: one session, per-item dispositions, fully reconstructible"


def test_review_refuses_gaps():
    gov, auth_id, seqs = _three_executions()
    # An item without a disposition cannot pass through silently.
    try:
        gov.submit_review(auth_id, seqs, {seqs[0]: "acknowledged"},
                          acting_principal="test-principal")
        raise AssertionError("gap allowed")
    except FailClosed as e:
        assert e.reason == "REVIEW_DISPOSITION_MISMATCH", e.reason
    # A non-execution entry cannot be smuggled into a review.
    try:
        gov.submit_review(auth_id, [0], {0: "acknowledged"},
                          acting_principal="test-principal")
        raise AssertionError("non-execution reviewed")
    except FailClosed as e:
        assert e.reason == "REVIEW_UNKNOWN_ITEM", e.reason
    # Dispositions are a closed set.
    try:
        gov.submit_review(auth_id, seqs[:1], {seqs[0]: "shrugged"},
                          acting_principal="test-principal")
        raise AssertionError("bad disposition allowed")
    except FailClosed as e:
        assert e.reason == "REVIEW_BAD_DISPOSITION", e.reason
    # Only the granting principal reviews.
    try:
        gov.submit_review(auth_id, seqs[:1], {seqs[0]: "acknowledged"},
                          acting_principal="agent-1")
        raise AssertionError("agent self-reviewed")
    except FailClosed as e:
        assert e.reason == "NOT_GRANTING_PRINCIPAL", e.reason
    return "review: gaps, smuggling, and self-review refused"


def test_review_changes_nothing():
    gov, auth_id, seqs = _three_executions()
    # Escalating an item in review grants the review no power: the authority
    # stays live, the rails stay put, and new actions still execute.
    gov.submit_review(auth_id, [seqs[1]], {seqs[1]: "escalated"},
                      acting_principal="test-principal")
    gov._live_authority(auth_id)
    assert gov.rails["spend-txn"].max_per_txn == 50.0
    act = SendEmail("bob@example.com", "follow-up", ALLOWLIST)
    rec = gov.evaluate(act, auth_id)
    gov.execute(rec, act, auth_id, acting_principal="agent-1")
    return "review: observation only — flagged item revokes nothing"


TESTS = [test_review_third_domain, test_review_refuses_gaps,
         test_review_changes_nothing]
