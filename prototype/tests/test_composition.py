"""Cross-action composition: CumAdm over trajectory history.

Adm(I1)=Pass, Adm(I2)=Pass, ... but CumAdm(In)=Fail => In must not execute.
Also: splitting a prohibited action into individually admissible pieces must fail.
"""
from lexicon_governor import FailClosed, SpendMoney
from tests.harness import make_gov, APPROVED_CATS


def _spend(gov, auth_id, amount, day=0):
    act = SpendMoney(amount, "api", APPROVED_CATS, day=day)
    rec = gov.evaluate(act, auth_id)
    return gov.execute(rec, act, auth_id, "agent-1")


def test_cumadm_blocks_composition():
    gov, _, auth_id = make_gov()
    # 4 x $45: each passes per-txn rail (<=50), cumulative $180 <= $200.
    for i in range(4):
        _spend(gov, auth_id, 45.0)
    # 5th: Adm in isolation would pass ($45 <= $50), but CumAdm fails
    # ($225 > $200 daily rail).
    try:
        _spend(gov, auth_id, 45.0)
    except FailClosed as e:
        assert e.reason == "CUMADM_FAIL", f"expected CUMADM_FAIL, got {e.reason}"
        return "composition: 5th spend blocked by CumAdm (daily rail)"
    raise AssertionError("composition: 5th spend should have failed CumAdm")


def test_split_attack_fails():
    gov, _, auth_id = make_gov()
    # A single $500 spend is prohibited outright (txn rail).
    try:
        _spend(gov, auth_id, 500.0)
        raise AssertionError("single $500 spend should fail")
    except FailClosed as e:
        assert e.reason == "CUMADM_FAIL"
    # Splitting into $45 pieces: blocked by the cumulative daily rail at #5.
    gov2, _, auth2 = make_gov()
    blocked_at = None
    for i in range(11):
        try:
            _spend(gov2, auth2, 45.0)
        except FailClosed as e:
            blocked_at = i + 1
            assert e.reason == "CUMADM_FAIL"
            break
    assert blocked_at == 5, f"split attack should die at #5, died at {blocked_at}"
    return "split attack: $500-as-11x$45 blocked at piece #5 by CumAdm"


TESTS = [test_cumadm_blocks_composition, test_split_attack_fails]
