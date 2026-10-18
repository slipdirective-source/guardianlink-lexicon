"""Core records: hash-chained history, authority and governance records."""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field


def hash_obj(obj) -> str:
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


class HistoryLog:
    """Append-only hash-chained log. The sealed history/state commitment."""

    def __init__(self):
        self.entries: list[dict] = []
        self._hashes: set[str] = set()

    def append(self, kind: str, payload: dict) -> dict:
        prev = self.entries[-1]["hash"] if self.entries else "GENESIS"
        entry = {
            "seq": len(self.entries),
            "prev": prev,
            "kind": kind,
            "payload": payload,
        }
        entry["hash"] = hash_obj({k: entry[k] for k in ("seq", "prev", "kind", "payload")})
        self.entries.append(entry)
        self._hashes.add(entry["hash"])
        return entry

    @property
    def head(self) -> str:
        return self.entries[-1]["hash"] if self.entries else "GENESIS"

    @property
    def seq(self) -> int:
        return len(self.entries)

    def contains(self, h: str) -> bool:
        """True iff h is an ancestor of (or equal to) the current head: no rewrite."""
        return h in self._hashes or h == "GENESIS"

    def events_since(self, seq: int) -> list[dict]:
        return [e for e in self.entries if e["seq"] >= seq]


@dataclass(frozen=True)
class AuthorityRecord:
    """Externally sourced legitimate authority. The Lexicon reads it; nothing in the
    Lexicon writes it. Origin: user/institution rail with provenance."""

    record_id: str
    granted_by: str            # authorizing principal
    scope: frozenset           # authorized action classes, e.g. {"SEND_EMAIL"}
    rails: tuple               # rail identifiers constraining the grant
    provenance: tuple          # chain terminating in granted_by
    valid_until: float

    def covers(self, action_class: str) -> bool:
        return action_class in self.scope


@dataclass(frozen=True)
class GovernanceConstraintRecord:
    """Lexicon governance output. May preserve, narrow, condition, suspend, or block
    execution. May never loosen a rail or expand authority (one-way ratchet)."""

    constraint_id: str
    source_rail: str
    canonical_action_id: str
    action_params_hash: str
    history_commitment: str    # sealed history head at evaluation
    history_seq: int
    cumadm_verdict: str        # "Pass" | "Fail"
    safety_state: str          # GREEN/YELLOW/ORANGE/RED/BLACK
    fired_triggers: tuple
    unresolved: tuple          # ((u_class, depends_bool), ...)
    provenance: tuple          # must extend the AuthorityRecord's chain
    recovery_required: str | None
    scope_after: frozenset     # effective scope; must satisfy ⊆ authority.scope
    issued_at: float
    expires_at: float
    supersedes: str | None
    record_hash: str = ""

    def sealed(self) -> "GovernanceConstraintRecord":
        body = {k: v for k, v in self.__dict__.items() if k != "record_hash"}
        h = hash_obj(body)
        return self.__class__(**{**body, "record_hash": h})

    def verify(self) -> bool:
        if not self.record_hash:
            return False
        return self.sealed().record_hash == self.record_hash


@dataclass(frozen=True)
class ConsequenceRecord:
    """Sealed execution record returned to the Lexicon as Yield/evidence."""

    action_id: str
    action_class: str
    yield_payload: dict
    prev_head: str
    new_head: str
    sealed_at: float
