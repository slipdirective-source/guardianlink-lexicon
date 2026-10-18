"""A5a / A5b / A5c regression gates (normative against Lexicon v1.4)."""
from lexicon_governor import (FailClosed, SendEmail, ModifyFile)
from tests.harness import make_gov, ALLOWLIST


def test_a5a_irrelevant_u():
    """U exists, action does not depend on it -> preserve U, do not block."""
    gov, _, auth_id = make_gov()
    act = SendEmail("alice@example.com", "hello", ALLOWLIST,
                    extra_u=[("U_scale", False)])
    rec = gov.evaluate(act, auth_id)
    assert ("U_scale", False) in rec.unresolved, "U must remain represented"
    out = gov.execute(rec, act, auth_id, "agent-1")
    assert out.yield_payload["sent_to"] == "alice@example.com"
    return "A5a: irrelevant U preserved, no block"


def test_a5b_material_but_invariant():
    """U material, but no admissible resolution changes the outcome ->
    preserve U, do not block because of U."""
    gov, _, auth_id = make_gov()
    act = ModifyFile("/workspace/src/main.py", versioned=True,
                     extra_u=[("U_prob", True)],
                     res_map={"U_prob": [{"p": "high", "admissible": True},
                                        {"p": "low", "admissible": True}]})
    rec = gov.evaluate(act, auth_id)
    assert ("U_prob", True) in rec.unresolved, "U must remain represented"
    out = gov.execute(rec, act, auth_id, "agent-1")
    assert out.yield_payload["wrote"] == "/workspace/src/main.py"
    return "A5b: material-but-invariant U preserved, no block"


def test_a5c_decision_dominant_blocks():
    """Some admissible resolution changes the outcome -> T_unk fires,
    dependent execution fails closed."""
    gov, _, auth_id = make_gov()
    act = SendEmail("mallory@evil.example", "hello", ALLOWLIST,
                    res_map={"U_auth": [
                        {"recipient_authorized": True, "admissible": True},
                        {"recipient_authorized": False, "admissible": True}]})
    try:
        gov.evaluate(act, auth_id)
    except FailClosed as e:
        assert e.reason == "T_UNK", f"expected T_UNK, got {e.reason}"
        assert "U_auth" in e.detail.get("dominant", []), \
            "dominant U must be named in the failure"
        return "A5c: decision-dominant U fails closed (T_UNK)"
    raise AssertionError("A5c: expected FailClosed(T_UNK), evaluation passed")


TESTS = [test_a5a_irrelevant_u, test_a5b_material_but_invariant,
         test_a5c_decision_dominant_blocks]
