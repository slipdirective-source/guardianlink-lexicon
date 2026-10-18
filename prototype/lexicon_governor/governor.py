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
    StandingDelegationProposal, StandingDelegation,
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
        import copy as _copy
        # Each governor owns its rails: a RegimeDelta applies to this
        # deployment's rails only. Sharing mutable rail instances across
        # governors would let one deployment's rail changes leak into
        # another's — a cross-instance contamination the ratchet forbids.
        self.rails = _copy.deepcopy(rails)
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
        self.standing_proposals: dict[str, StandingDelegationProposal] = {}
        self.standing: dict[str, StandingDelegation] = {}
        self.revoked_standing: set[str] = set()

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
                             "field": field, "new_value": new_value,
                             "justification": justification})
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
            applied.append(self._apply_rail_change(prop, acting_principal))
        return applied

    def _apply_rail_change(self, prop: RailChangeProposal, approved_by: str,
                           via_standing: str | None = None) -> RegimeDeltaRecord:
        import uuid as _uuid
        rail = self.rails[prop.rail_id]
        setattr(rail, prop.field, prop.new_value)
        delta = RegimeDeltaRecord(
            delta_id="rd-" + _uuid.uuid4().hex[:12],
            proposal_id=prop.proposal_id, rail_id=prop.rail_id,
            field=prop.field, old_value=prop.old_value,
            new_value=prop.new_value, justification=prop.justification,
            approved_by=approved_by, approved_at=self.clock.now())
        self.rail_versions.append(delta)
        payload = {"delta_id": delta.delta_id, "rail": prop.rail_id,
                   "field": prop.field,
                   "old": prop.old_value, "new": prop.new_value,
                   "justification": prop.justification,
                   "approved_by": approved_by}
        if via_standing:
            payload["via_standing"] = via_standing
        self.history.append("regime delta applied", payload)
        del self.proposals[prop.proposal_id]
        return delta

    # ---- S3: learned delegation (autonomy as emergent operating envelope) ----
    def reject_proposal(self, proposal_id: str, acting_principal: str,
                        reason: str):
        """The principal explicitly rejects a proposal. Rejections are
        intervention data: the delegation report learns from them."""
        prop = self.proposals.get(proposal_id)
        if prop is None:
            raise FailClosed("UNKNOWN_PROPOSAL", {"proposal_id": proposal_id})
        auth = self._live_authority(prop.authority_id)
        if acting_principal != auth.granted_by:
            raise FailClosed("NOT_GRANTING_PRINCIPAL", {"acting": acting_principal})
        self.history.append("rail change rejected",
                            {"proposal_id": proposal_id, "rail": prop.rail_id,
                             "field": prop.field, "new_value": prop.new_value,
                             "reason": reason, "rejected_by": acting_principal})
        del self.proposals[proposal_id]

    def delegation_report(self) -> dict:
        """What the principal routinely authorizes, where they intervene, and
        which rails are candidates for ceremony compression. Built from the
        audit history — the warranted record, not the agent's impression."""
        rails: dict[str, dict] = {}
        def row(rail_id: str) -> dict:
            return rails.setdefault(rail_id, {"proposed": 0, "applied": 0,
                                              "rejected": 0,
                                              "max_applied_new_value": None,
                                              "min_rejected_new_value": None})
        for e in self.history.entries:
            k, p = e["kind"], e["payload"]
            if k == "rail change proposed":
                row(p["rail"])["proposed"] += 1
            elif k == "regime delta applied":
                r = row(p["rail"]); r["applied"] += 1
                nv = p.get("new")
                if isinstance(nv, (int, float)) and (
                        r["max_applied_new_value"] is None
                        or nv > r["max_applied_new_value"]):
                    r["max_applied_new_value"] = nv
            elif k == "rail change rejected":
                r = row(p["rail"]); r["rejected"] += 1
                nv = p.get("new_value")
                if isinstance(nv, (int, float)) and (
                        r["min_rejected_new_value"] is None
                        or nv < r["min_rejected_new_value"]):
                    r["min_rejected_new_value"] = nv
        routine = [rid for rid, r in rails.items()
                   if r["applied"] >= 5 and r["rejected"] == 0]
        near_routine = [rid for rid, r in rails.items()
                        if r["applied"] >= 5 and r["rejected"] > 0
                        and r["applied"] / max(1, r["applied"] + r["rejected"]) >= 0.8]
        return {"rails": rails, "routine_candidates": routine,
                "near_routine": near_routine}

    def propose_standing_delegation(self, proposer_holder: str,
                                    authority_id: str, rail_id: str,
                                    bounds: dict, review_ttl: float,
                                    rationale: str
                                    ) -> StandingDelegationProposal:
        """The agent proposes a standing delegation grounded in the delegation
        report. Competence produces the information; the principal disposes."""
        import uuid as _uuid
        auth = self._live_authority(authority_id)
        if proposer_holder != auth.holder:
            raise FailClosed("HOLDER_MISMATCH", {})
        if rail_id not in self.rails:
            raise FailClosed("UNKNOWN_RAIL", {"rail_id": rail_id})
        prop = StandingDelegationProposal(
            proposal_id="sdp-" + _uuid.uuid4().hex[:12],
            proposer=proposer_holder, authority_id=authority_id,
            delegation_class="rail-change", rail_id=rail_id, bounds=bounds,
            review_ttl=review_ttl, rationale=rationale,
            proposed_at=self.clock.now())
        self.standing_proposals[prop.proposal_id] = prop
        self.history.append("standing delegation proposed",
                            {"proposal_id": prop.proposal_id, "rail": rail_id,
                             "bounds": bounds, "rationale": rationale})
        return prop

    def grant_standing_delegation(self, proposal_id: str,
                                  acting_principal: str) -> StandingDelegation:
        """The principal grants the standing delegation: bounded, expiring,
        revocable. The envelope expands; self-granted authority does not."""
        import uuid as _uuid
        prop = self.standing_proposals.get(proposal_id)
        if prop is None:
            raise FailClosed("UNKNOWN_PROPOSAL", {"proposal_id": proposal_id})
        auth = self._live_authority(prop.authority_id)
        if acting_principal != auth.granted_by:
            raise FailClosed("NOT_GRANTING_PRINCIPAL", {"acting": acting_principal})
        sd = StandingDelegation(
            delegation_id="sd-" + _uuid.uuid4().hex[:12],
            proposal_id=proposal_id, granted_by=acting_principal,
            holder=prop.proposer, delegation_class=prop.delegation_class,
            rail_id=prop.rail_id, bounds=prop.bounds,
            granted_at=self.clock.now(),
            review_by=self.clock.now() + prop.review_ttl)
        self.standing[sd.delegation_id] = sd
        self.history.append("standing delegation granted",
                            {"delegation_id": sd.delegation_id,
                             "rail": prop.rail_id, "bounds": prop.bounds,
                             "granted_by": acting_principal,
                             "review_by": sd.review_by})
        del self.standing_proposals[proposal_id]
        return sd

    def revoke_standing_delegation(self, delegation_id: str,
                                   acting_principal: str):
        sd = self.standing.get(delegation_id)
        if sd is None:
            raise FailClosed("UNKNOWN_STANDING", {"delegation_id": delegation_id})
        if acting_principal != sd.granted_by:
            raise FailClosed("NOT_GRANTING_PRINCIPAL", {"acting": acting_principal})
        self.revoked_standing.add(delegation_id)
        self.history.append("standing delegation revoked",
                            {"delegation_id": delegation_id,
                             "revoked_by": acting_principal})

    def submit_review(self, authority_id: str, execution_seqs: list[int],
                      dispositions: dict[int, str], acting_principal: str,
                      note: str = "") -> str:
        """Third domain for the ceremony-batching principle: retrospective
        oversight. S1/S2/S3 batch *prospective authorization*; this batches
        *retrospective review* — structurally different, same test.

        One session covers N executed actions; each item gets its own
        disposition (acknowledged / flagged / escalated), individually
        recorded. Dispositions are observation only: they grant, revoke, and
        change nothing. A flagged item is not a revoked authority and not a
        reassessed trigger — review cannot substitute for control actions."""
        import uuid as _uuid
        auth = self._live_authority(authority_id)
        if acting_principal != auth.granted_by:
            raise FailClosed("NOT_GRANTING_PRINCIPAL", {"acting": acting_principal})
        valid = {"acknowledged", "flagged", "escalated"}
        items = {}
        for seq in execution_seqs:
            e = self.history.entries[seq] if 0 <= seq < len(self.history.entries) else None
            if e is None or e["kind"] != "execution":
                raise FailClosed("REVIEW_UNKNOWN_ITEM",
                                 {"seq": seq,
                                  "kind": e["kind"] if e else "absent"})
            items[seq] = e["payload"]
        if set(dispositions.keys()) != set(execution_seqs):
            raise FailClosed("REVIEW_DISPOSITION_MISMATCH",
                             {"items": sorted(execution_seqs),
                              "disposed": sorted(dispositions.keys())})
        for seq, d in dispositions.items():
            if d not in valid:
                raise FailClosed("REVIEW_BAD_DISPOSITION",
                                 {"seq": seq, "disposition": d})
        session_id = "rev-" + _uuid.uuid4().hex[:12]
        self.history.append("review session",
                            {"session_id": session_id,
                             "reviewed_by": acting_principal,
                             "items": [{"seq": seq,
                                        "action": items[seq].get("action"),
                                        "disposition": dispositions[seq]}
                                       for seq in execution_seqs],
                             "note": note})
        return session_id

    def apply_within_standing(self, rail_proposal_id: str,
                              acting_holder: str) -> RegimeDeltaRecord:
        """Apply a rail proposal under a live standing delegation: no per-item
        principal ceremony, but the full RegimeDelta record is still written and
        authority still terminates in the granting principal."""
        prop = self.proposals.get(rail_proposal_id)
        if prop is None:
            raise FailClosed("UNKNOWN_PROPOSAL", {"proposal_id": rail_proposal_id})
        auth = self._live_authority(prop.authority_id)
        if acting_holder != auth.holder:
            raise FailClosed("HOLDER_MISMATCH", {})
        covering = [sd for sd in self.standing.values()
                    if sd.holder == acting_holder
                    and sd.delegation_class == "rail-change"
                    and sd.rail_id == prop.rail_id]
        if not covering:
            raise FailClosed("NO_COVERING_STANDING", {})
        live = [sd for sd in covering
                if sd.delegation_id not in self.revoked_standing
                and self.clock.now() <= sd.review_by]
        if not live:
            sd0 = covering[0]
            if sd0.delegation_id in self.revoked_standing:
                raise FailClosed("STANDING_REVOKED", {})
            raise FailClosed("STANDING_EXPIRED", {})

        def in_bounds(sd: StandingDelegation) -> bool:
            b = sd.bounds
            if prop.field not in b.get("fields", []):
                return False
            mx = b.get("max_new_value")
            if (mx is not None and isinstance(prop.new_value, (int, float))
                    and prop.new_value > mx):
                return False
            return True

        sd = next((s for s in live if in_bounds(s)), None)
        if sd is None:
            raise FailClosed("STANDING_BOUNDS_EXCEEDED", {})
        return self._apply_rail_change(prop, approved_by=sd.granted_by,
                                       via_standing=sd.delegation_id)

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
    def crash_audit(self) -> list[dict]:
        """Return orphaned execution intents: 'execution started' entries with
        no matching 'execution' or 'execution aborted' for the same
        constraint. A crash between mutation and seal produces exactly this
        shape — the mutation may have happened, the seal did not. Orphans
        require investigation, never blind retry (retry would risk a second
        mutation; the record is already consumed, so the governor refuses)."""
        started = {}
        closed = set()
        for e in self.history.entries:
            k, p = e["kind"], e["payload"]
            if k == "execution started":
                started[p["constraint"]] = e
            elif k in ("execution", "execution aborted"):
                closed.add(p["constraint"])
        return [started[c] for c in started if c not in closed]

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

        # Perform (simulated) and seal the consequence — crash-consistent.
        # Consumption first: a crash anywhere below still refuses re-execution
        # (at-most-once). The intent entry goes down BEFORE the mutation so a
        # crash between perform and seal leaves an orphaned intent that
        # crash_audit() surfaces, instead of a silent mutation with no record.
        self.consumed.add(record.constraint_id)
        prev_head = self.history.head
        self.history.append("execution started",
                            {"action": record.canonical_action_id,
                             "constraint": record.constraint_id})
        try:
            yield_payload = action.perform()
        except Exception:
            self.history.append("execution aborted",
                                {"action": record.canonical_action_id,
                                 "constraint": record.constraint_id})
            raise
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
