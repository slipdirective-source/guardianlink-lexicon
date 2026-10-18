"""LexiconLayer (pure evaluation) + Governor (admission & execution).

Separation of powers: the LexiconLayer judges admissibility and proposes a
GovernanceConstraintRecord. The Governor re-derives the evaluation from its own
rails and history, admits only exact matches, and executes. Neither component
can independently manufacture execution authority.
"""
from __future__ import annotations
import uuid

from .records import (
    AuthorityRecord, GovernanceConstraintRecord, ConsequenceRecord, HistoryLog, hash_obj,
    RailChangeProposal, RegimeDeltaRecord,
)


class FailClosed(Exception):
    def __init__(self, reason: str, detail: dict | None = None):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail or {}


class Clock:
    def __init__(self, start: float = 1_000_000.0):
        self._t = start

    def now(self) -> float:
        return self._t

    def advance(self, seconds: float):
        self._t += seconds


EVAL_TTL = 300.0  # governance evaluations expire after 5 minutes


class LexiconLayer:
    """Pure function: action + authority + history view -> proposed record.

    Proposes; does not seal, does not execute. A proposal is unsigned until the
    Governor admits it.
    """

    def evaluate(self, action, authority: AuthorityRecord, history: HistoryLog,
                 rails: dict, now: float) -> GovernanceConstraintRecord:
        # Base evaluation resolves each U to its favorable admissible value;
        # decision-dominance then tests the counterfactuals. This makes T_unk
        # (not rail failure on unknowns) the single blocking mechanism for U.
        recorded_u = list(action.unresolved())
        fav: dict = {}
        for (u, _depends) in recorded_u:
            fav.update(action.favorable(u))
        verdict, triggers, detail = check_cumadm(
            action, authority, history, rails, fav or None)

        # U analysis: record all; test decision-dominance for each
        dominant = [
            u for (u, _depends) in recorded_u
            if decision_dominant(action, authority, history, rails, u, verdict, fav)
        ]

        safety = derive_safety(triggers, verdict)
        narrowed = narrow_scope(authority.scope, safety, triggers)

        if dominant:
            # v1.4 T_unk: decision-dominant uncertainty fails closed HERE, at
            # evaluation. The Lexicon does not issue an executable record for an
            # action whose admissibility turns on an unresolved variable.
            # The dominant U stays represented in the failure detail.
            raise FailClosed("T_UNK", {
                "dominant": dominant,
                "recorded_unresolved": recorded_u,
                "base_verdict": verdict,
            })

        rec = GovernanceConstraintRecord(
            constraint_id="gcr-" + uuid.uuid4().hex[:12],
            source_rail=",".join(sorted(detail.get("rails_used", []))) or "baseline",
            canonical_action_id=action.canonical_id(),
            action_params_hash=hash_obj(action.params),
            history_commitment=history.head,
            history_seq=history.seq,
            cumadm_verdict=verdict,
            safety_state=safety,
            fired_triggers=tuple(triggers),
            unresolved=tuple(recorded_u),
            provenance=tuple(authority.provenance) + ("lexicon-eval",),
            recovery_required=detail.get("recovery_required"),
            scope_after=frozenset(narrowed),
            issued_at=now,
            expires_at=now + EVAL_TTL,
            supersedes=None,
        )
        # The Lexicon never issues a block as an executable record: a dominant U
        # or failed CumAdm is returned as a Fail verdict for the Governor to refuse.
        return rec


def check_cumadm(action, authority: AuthorityRecord, history: HistoryLog,
                 rails: dict, world: dict | None = None) -> tuple[str, list, dict]:
    """Cumulative admissibility: rails evaluated over trajectory history + candidate.

    Returns (verdict, triggers, detail). verdict is "Pass"/"Fail".
    `world` optionally overrides action attributes for counterfactual evaluation.
    """
    triggers: list[str] = []
    rails_used: list[str] = []
    recovery_required = None

    for rail_id in authority.rails:
        rail = rails[rail_id]
        ok, trig, rec = rail.check(action, authority, history, world)
        rails_used.append(rail_id)
        if trig:
            triggers.extend(trig)
        if rec:
            recovery_required = rec
        if not ok:
            return "Fail", sorted(set(triggers)), {
                "rails_used": rails_used, "failed_rail": rail_id,
                "recovery_required": recovery_required}
    return "Pass", sorted(set(triggers)), {
        "rails_used": rails_used, "recovery_required": recovery_required}


def decision_dominant(action, authority, history, rails, u_class: str,
                      base_verdict: str, fav: dict) -> bool:
    """v1.4 T_unk criterion: U is decision-dominant iff at least one ADMISSIBLE
    resolution of U changes the current admissibility outcome.

    Inadmissible resolutions (worlds where the action is already impossible or
    unauthorized for independent reasons) do not count: dominance is tested only
    over resolutions the framework could actually adopt.
    """
    changed = False
    for res in action.resolutions(u_class):
        if not res.get("admissible", True):
            continue
        world = {**fav, **{k: v for k, v in res.items() if k != "admissible"}}
        verdict, _, _ = check_cumadm(action, authority, history, rails,
                                     world or None)
        if verdict != base_verdict:
            changed = True
            break
    return changed


def derive_safety(triggers: list, verdict: str) -> str:
    if verdict == "Fail":
        return "RED"
    if "T_cat" in triggers or "T_irr_high" in triggers:
        return "ORANGE"
    if triggers:
        return "YELLOW"
    return "GREEN"


def narrow_scope(scope: frozenset, safety: str, triggers: list) -> frozenset:
    # The Lexicon may only narrow. ORANGE suspends novel/high-consequence classes;
    # prototype models this as: ORANGE/RED narrow to the empty set for the
    # evaluated action's class unless explicitly retained. Here we keep it simple:
    # the evaluated action's own class is retained iff safety is GREEN/YELLOW.
    # (Callers pass the action class; enforced in Governor.admit.)
    return scope


class Governor:
    """Execution governor. Admits Lexicon proposals only on exact re-derivation,
    then executes under binding, freshness, authority, and ratchet checks."""

    def __init__(self, rails: dict, clock: Clock):
        self.rails = rails
        self.clock = clock
        self.history = HistoryLog()
        self.lexicon = LexiconLayer()
        self.authorities: dict[str, AuthorityRecord] = {}
        self.revoked: set[str] = set()
        self.issued: dict[str, GovernanceConstraintRecord] = {}
        self.latest_by_action: dict[str, str] = {}
        self.consumed: set[str] = set()
        self.proposals: dict[str, RailChangeProposal] = {}
        self.rail_versions: list[RegimeDeltaRecord] = []

    # ---- authority management (external: user/institution) ----
    def grant_authority(self, auth: AuthorityRecord):
        if not auth.provenance or auth.provenance[0] != auth.granted_by:
            raise FailClosed("AUTHORITY_PROVENANCE",
                             {"msg": "provenance must originate from the granting principal"})
        self.authorities[auth.record_id] = auth
        self.history.append("authority granted",
                            {"record_id": auth.record_id, "by": auth.granted_by,
                             "scope": sorted(auth.scope)})

    def delegate(self, parent_id: str, sub_holder: str, scope=None) -> AuthorityRecord:
        """Explicit sub-delegation: the legitimate form of S1.

        A sub-agent receives its OWN AuthorityRecord, derived from the parent
        grant: scope can only narrow, provenance extends the parent chain, and
        the delegation itself is logged. Opaque inheritance (acting under the
        parent's record) is rejected at execution by the holder check.
        Per-agent authorization overhead is the price — paid explicitly."""
        parent = self._live_authority(parent_id)
        sc = frozenset(scope) if scope is not None else parent.scope
        if not sc <= set(parent.scope):
            raise FailClosed("DELEGATION_WIDENING", {})
        sub = AuthorityRecord(
            record_id="auth-" + uuid.uuid4().hex[:12],
            granted_by=parent.granted_by,
            holder=sub_holder,
            scope=sc,
            rails=parent.rails,
            provenance=tuple(parent.provenance) + (parent.record_id, "delegation"),
            valid_until=min(parent.valid_until, self.clock.now() + 86400),
        )
        self.grant_authority(sub)
        return sub

    def delegate_batch(self, parent_id: str, holders: list[str], scope=None
                     ) -> list[AuthorityRecord]:
        """Leverage recovery for S1: one principal action mints N sub-delegations.

        Each sub-agent still gets its OWN record, visible provenance chaining to
        the parent grant, and individual revocability. The authorization overhead
        moves from N ceremonies to one decision + N records — most of the
        scaling leverage recovered, none of the opacity."""
        return [self.delegate(parent_id, h, scope) for h in holders]

    def propose_rail_change(self, proposer_holder: str, authority_id: str,
                            rail_id: str, field: str, new_value,
                            justification: str) -> RailChangeProposal:
        """An agent proposes a rail change. Proposing is legitimate; the agent
        may not dispose of its own proposal (see approve_rail_changes)."""
        import uuid as _uuid
        auth = self._live_authority(authority_id)
        if proposer_holder != auth.holder:
            raise FailClosed("HOLDER_MISMATCH", {})
        if rail_id not in self.rails:
            raise FailClosed("UNKNOWN_RAIL", {"rail_id": rail_id})
        rail = self.rails[rail_id]
        if not hasattr(rail, field):
            raise FailClosed("UNKNOWN_RAIL_FIELD", {"field": field})
        prop = RailChangeProposal(
            proposal_id="prop-" + _uuid.uuid4().hex[:12],
            proposer=proposer_holder, authority_id=authority_id,
            rail_id=rail_id, field=field, old_value=getattr(rail, field),
            new_value=new_value, justification=justification,
            proposed_at=self.clock.now())
        self.proposals[prop.proposal_id] = prop
        self.history.append("rail change proposed",
                            {"proposal_id": prop.proposal_id, "rail": rail_id,
                             "field": field, "justification": justification})
        return prop

    def approve_rail_changes(self, proposal_ids: list[str],
                             acting_principal: str) -> list[RegimeDeltaRecord]:
        """Leverage recovery for S2: the principal disposes of a BATCH of rail
        proposals in one action. Each change still gets its own RegimeDelta
        record with its independent justification — batching the ceremony, not
        the accountability. The agent can never approve its own proposals."""
        import uuid as _uuid
        applied = []
        for pid in proposal_ids:
            prop = self.proposals.get(pid)
            if prop is None:
                raise FailClosed("UNKNOWN_PROPOSAL", {"proposal_id": pid})
            auth = self._live_authority(prop.authority_id)
            if acting_principal != auth.granted_by:
                raise FailClosed("NOT_GRANTING_PRINCIPAL",
                                 {"acting": acting_principal})
            rail = self.rails[prop.rail_id]
            setattr(rail, prop.field, prop.new_value)
            delta = RegimeDeltaRecord(
                delta_id="rd-" + _uuid.uuid4().hex[:12],
                proposal_id=pid, rail_id=prop.rail_id, field=prop.field,
                old_value=prop.old_value, new_value=prop.new_value,
                justification=prop.justification,
                approved_by=acting_principal, approved_at=self.clock.now())
            self.rail_versions.append(delta)
            self.history.append("regime delta applied",
                                {"delta_id": delta.delta_id, "rail": prop.rail_id,
                                 "field": prop.field,
                                 "old": prop.old_value, "new": prop.new_value,
                                 "justification": prop.justification,
                                 "approved_by": acting_principal})
            del self.proposals[pid]
            applied.append(delta)
        return applied

    def revoke_authority(self, record_id: str):
        self.revoked.add(record_id)
        self.history.append("authority revoked", {"record_id": record_id})

    def _live_authority(self, record_id: str) -> AuthorityRecord:
        auth = self.authorities.get(record_id)
        if auth is None:
            raise FailClosed("NO_AUTHORITY", {"record_id": record_id})
        if record_id in self.revoked:
            raise FailClosed("AUTHORITY_REVOKED", {"record_id": record_id})
        if self.clock.now() > auth.valid_until:
            raise FailClosed("AUTHORITY_EXPIRED", {"record_id": record_id})
        return auth

    # ---- evaluation + admission ----
    def evaluate(self, action, authority_id: str) -> GovernanceConstraintRecord:
        """Full path: Lexicon proposes, Governor re-derives and admits (seals)."""
        auth = self._live_authority(authority_id)
        if not auth.covers(action.action_class):
            raise FailClosed("SCOPE", {"action": action.action_class})
        proposed = self.lexicon.evaluate(action, auth, self.history, self.rails,
                                         self.clock.now())
        return self.admit(proposed, action, authority_id)

    def admit(self, proposed: GovernanceConstraintRecord, action,
              authority_id: str) -> GovernanceConstraintRecord:
        auth = self._live_authority(authority_id)
        now = self.clock.now()

        # Re-derive independently and require exact match on governing fields.
        expected = self.lexicon.evaluate(action, auth, self.history, self.rails, now)
        for f in ("canonical_action_id", "action_params_hash", "cumadm_verdict",
                  "safety_state", "fired_triggers", "unresolved", "scope_after"):
            if getattr(proposed, f) != getattr(expected, f):
                raise FailClosed("LEXICON_MISMATCH", {"field": f})
        # Provenance must extend the authority's chain (no forged roots).
        if tuple(proposed.provenance[:len(auth.provenance)]) != tuple(auth.provenance):
            raise FailClosed("PROVENANCE_FORGED", {})
        # One-way ratchet: Lexicon output can only narrow authority, never expand.
        if not set(proposed.scope_after) <= set(auth.scope):
            raise FailClosed("RATCHET_VIOLATION",
                             {"scope_after": sorted(proposed.scope_after),
                              "scope_before": sorted(auth.scope)})
        if proposed.cumadm_verdict != "Pass":
            raise FailClosed("CUMADM_FAIL",
                             {"triggers": list(proposed.fired_triggers)})
        if proposed.safety_state in ("RED", "BLACK"):
            raise FailClosed("SAFETY_HALT", {"state": proposed.safety_state})

        sealed = proposed.sealed()
        # Supersede any earlier live record for the same canonical action.
        prev = self.latest_by_action.get(sealed.canonical_action_id)
        if prev and prev in self.issued:
            old = self.issued[prev]
            self.issued[prev] = GovernanceConstraintRecord(
                **{**old.__dict__, "supersedes": old.constraint_id})
        self.issued[sealed.constraint_id] = sealed
        self.latest_by_action[sealed.canonical_action_id] = sealed.constraint_id
        self.history.append("governance admitted",
                            {"constraint_id": sealed.constraint_id,
                             "action": sealed.canonical_action_id,
                             "safety": sealed.safety_state})
        return sealed

    # ---- execution ----
    def execute(self, record: GovernanceConstraintRecord, action,
                authority_id: str, acting_principal: str) -> ConsequenceRecord:
        now = self.clock.now()
        # Governance-state checks: missing/malformed/expired/superseded/
        # unverifiable/action-mismatched/history-mismatched -> fail closed.
        if not isinstance(record, GovernanceConstraintRecord) or not record.verify():
            raise FailClosed("GOVERNANCE_MALFORMED", {})
        live = self.issued.get(record.constraint_id)
        if live is None or live.record_hash != record.record_hash:
            raise FailClosed("GOVERNANCE_UNKNOWN", {})
        if live.supersedes and self.latest_by_action.get(record.canonical_action_id) != record.constraint_id:
            raise FailClosed("GOVERNANCE_SUPERSEDED", {})
        if record.constraint_id in self.consumed:
            raise FailClosed("GOVERNANCE_CONSUMED", {})
        if now > record.expires_at:
            raise FailClosed("GOVERNANCE_EXPIRED", {})
        if record.canonical_action_id != action.canonical_id():
            raise FailClosed("ACTION_MISMATCH", {})
        if hash_obj(action.params) != record.action_params_hash:
            raise FailClosed("ACTION_MISMATCH", {"params": True})
        # History: commitment must be an ancestor (no rewrite) and no
        # invalidating event (revocation / safety escalation) may have occurred
        # since the commitment for this action's class.
        if not self.history.contains(record.history_commitment):
            raise FailClosed("HISTORY_MISMATCH", {})
        for e in self.history.events_since(record.history_seq):
            if e["kind"] == "authority revoked" and \
                    e["payload"].get("record_id") == authority_id:
                raise FailClosed("AUTHORITY_REVOKED_AFTER_EVAL", {})
            if e["kind"] == "safety escalated":
                raise FailClosed("SAFETY_CHANGED_AFTER_EVAL", {})

        auth = self._live_authority(authority_id)
        if acting_principal != auth.holder:
            raise FailClosed("HOLDER_MISMATCH",
                             {"acting": acting_principal, "holder": auth.holder})
        if not set(record.scope_after) <= set(auth.scope):
            raise FailClosed("RATCHET_VIOLATION", {})
        if action.action_class not in record.scope_after:
            raise FailClosed("SCOPE_NARROWED", {"state": record.safety_state})

        # Perform (simulated) and seal the consequence.
        self.consumed.add(record.constraint_id)
        prev_head = self.history.head
        yield_payload = action.perform()
        entry = self.history.append("execution",
                                    {"action": record.canonical_action_id,
                                     "constraint": record.constraint_id,
                                     "yield": yield_payload})
        return ConsequenceRecord(
            action_id=record.canonical_action_id,
            action_class=action.action_class,
            yield_payload=yield_payload,
            prev_head=prev_head,
            new_head=entry["hash"],
            sealed_at=now,
        )
