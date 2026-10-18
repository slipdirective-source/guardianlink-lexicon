"""Bounded action classes + rails.

Rails are user/institution-created with provenance (here: configured by the test
harness acting as the authorizing principal). The Lexicon evaluates them; it
never mints them.
"""
from __future__ import annotations
from .records import hash_obj


class Action:
    action_class: str = "BASE"
    params: dict = {}

    def __init__(self, day: int = 0, extra_u: list | None = None,
                 res_map: dict | None = None):
        self.day = day
        self._extra_u = list(extra_u or [])
        self._res_map = dict(res_map or {})

    def canonical_id(self) -> str:
        return f"{self.action_class}:{hash_obj(self.params)[:12]}"

    def unresolved(self) -> list[tuple[str, bool]]:
        """[(u_class, depends_bool)]. depends is recorded information, not the
        blocking discriminator."""
        return list(self._extra_u)

    def favorable(self, u_class: str) -> dict:
        """Best-case admissible resolution, used for the base evaluation."""
        worlds = self._res_map.get(u_class, [])
        return {k: v for k, v in worlds[0].items() if k != "admissible"} if worlds else {}

    def resolutions(self, u_class: str) -> list[dict]:
        return self._res_map.get(u_class, [{"admissible": True}])

    def perform(self) -> dict:
        return {"ok": True, "action_class": self.action_class, "day": self.day}


class SendEmail(Action):
    action_class = "SEND_EMAIL"

    def __init__(self, recipient: str, subject: str, allowlist: frozenset, **kw):
        super().__init__(**kw)
        self.params = {"recipient": recipient, "subject": subject}
        self._allowlist = allowlist

    def unresolved(self):
        u = list(super().unresolved())
        if self.params["recipient"] not in self._allowlist:
            u.append(("U_auth", True))
        return u

    def perform(self):
        d = super().perform()
        d["sent_to"] = self.params["recipient"]
        return d


class ModifyFile(Action):
    action_class = "MODIFY_FILE"

    def __init__(self, path: str, versioned: bool, scope_prefix="/workspace",
                 blocked=("~/.ssh", ".key", "secrets"), **kw):
        super().__init__(**kw)
        self.params = {"path": path}
        self._versioned = versioned
        self._scope = scope_prefix
        self._blocked = blocked

    def perform(self):
        d = super().perform()
        d["wrote"] = self.params["path"]
        return d


class SpendMoney(Action):
    action_class = "SPEND_MONEY"

    def __init__(self, amount: float, category: str, approved_categories: frozenset, **kw):
        super().__init__(**kw)
        self.params = {"amount": amount, "category": category}
        self._approved = approved_categories

    def unresolved(self):
        u = list(super().unresolved())
        if self.params["category"] not in self._approved:
            u.append(("U_auth", True))
        return u

    def perform(self):
        d = super().perform()
        d["amount"] = self.params["amount"]
        d["category"] = self.params["category"]
        return d


class ExternalApiCall(Action):
    action_class = "EXTERNAL_API_CALL"

    def __init__(self, method: str, host: str, verified_hosts: frozenset, **kw):
        super().__init__(**kw)
        self.params = {"method": method, "host": host}
        self._verified = verified_hosts

    def unresolved(self):
        u = list(super().unresolved())
        if self.params["method"] not in ("GET", "HEAD") \
                and self.params["host"] not in self._verified:
            u.append(("U_integrity", True))
        return u

    def perform(self):
        d = super().perform()
        d["called"] = f"{self.params['method']} {self.params['host']}"
        return d


# ---------------- rails ----------------

class Rail:
    id = "base"

    def check(self, action, authority, history, world):
        """-> (ok: bool, triggers: list, recovery_required: str|None)"""
        return True, [], None


def _executions_today(history, action_class, day):
    return [e for e in history.entries
            if e["kind"] == "execution"
            and e["payload"].get("yield", {}).get("action_class") == action_class
            and e["payload"].get("yield", {}).get("day") == day]


class EmailRecipientRail(Rail):
    id = "email-recipient"

    def check(self, action, authority, history, world):
        if action.action_class != "SEND_EMAIL":
            return True, [], None
        if world and "recipient_authorized" in world:
            ok = bool(world["recipient_authorized"])
        else:
            ok = action.params["recipient"] in action._allowlist
        return ok, [], None


class EmailVolumeRail(Rail):
    id = "email-volume"
    max_per_day = 5  # declared default (user rail)

    def check(self, action, authority, history, world):
        if action.action_class != "SEND_EMAIL":
            return True, [], None
        n = len(_executions_today(history, "SEND_EMAIL", action.day))
        return n < self.max_per_day, [], None


class FileScopeRail(Rail):
    id = "file-scope"

    def check(self, action, authority, history, world):
        if action.action_class != "MODIFY_FILE":
            return True, [], None
        p = action.params["path"]
        if not p.startswith(action._scope) or any(b in p for b in action._blocked):
            return False, [], None
        # Unversioned write: reversible only with effort -> T_irr trigger.
        trig = [] if action._versioned else ["T_irr"]
        return True, trig, None


class SpendTxnRail(Rail):
    id = "spend-txn"
    max_per_txn = 50.0          # declared default (user rail)
    significant = 25.0          # above this, irreversibility is decision-relevant

    def check(self, action, authority, history, world):
        if action.action_class != "SPEND_MONEY":
            return True, [], None
        amt = action.params["amount"]
        if amt > self.max_per_txn:
            return False, ["T_irr"], None
        trig = ["T_irr"] if amt > self.significant else []
        return True, trig, "refund/chargeback (unqualified)" if trig else None


class SpendDailyRail(Rail):
    """The cumulative rail: individually admissible spends can compose into an
    inadmissible trajectory. This is CumAdm made concrete."""
    id = "spend-daily"
    max_per_day = 200.0         # declared default (user rail)

    def check(self, action, authority, history, world):
        if action.action_class != "SPEND_MONEY":
            return True, [], None
        total = sum(e["payload"]["yield"]["amount"]
                    for e in _executions_today(history, "SPEND_MONEY", action.day))
        if total + action.params["amount"] > self.max_per_day:
            return False, ["T_irr"], "refund/chargeback (unqualified)"
        return True, [], None


class SpendCategoryRail(Rail):
    id = "spend-category"

    def check(self, action, authority, history, world):
        if action.action_class != "SPEND_MONEY":
            return True, [], None
        if world and "category_approved" in world:
            ok = bool(world["category_approved"])
        else:
            ok = action.params["category"] in action._approved
        return ok, [], None


class ApiMethodRail(Rail):
    id = "api-method"

    def check(self, action, authority, history, world):
        if action.action_class != "EXTERNAL_API_CALL":
            return True, [], None
        if action.params["method"] in ("GET", "HEAD"):
            return True, [], None  # routine read-only: GREEN path
        if world and "endpoint_verified" in world:
            ok = bool(world["endpoint_verified"])
        else:
            ok = action.params["host"] in action._verified
        return ok, [], None


ALL_RAILS = {
    r.id: r() for r in (EmailRecipientRail, EmailVolumeRail, FileScopeRail,
                        SpendTxnRail, SpendDailyRail, SpendCategoryRail,
                        ApiMethodRail)
}
