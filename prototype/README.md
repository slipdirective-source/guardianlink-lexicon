# prototype: executable coupling contract

`lexicon_governor` is a running implementation of the Lexicon ↔ GuardianLink
interface contract. It demonstrates the governance path, not engine internals:
action *effects* are simulated; the governance machinery is real.

## What it implements

- **Records** (`records.py`): `AuthorityRecord` (externally sourced, provenance
  terminating in the granting principal), `GovernanceConstraintRecord`
  (Lexicon output), `ConsequenceRecord` (sealed execution record returned as
  Yield), and an append-only hash-chained `HistoryLog` (the sealed
  history/state commitment).
- **Separation of powers** (`governor.py`): `LexiconLayer` judges admissibility
  and *proposes*; `Governor` re-derives the evaluation from its own rails and
  history, admits only exact matches, and executes. Neither component can
  independently manufacture execution authority.
- **One-way ratchet**: `scope_after ⊆ scope_before` enforced at admission and
  execution. Lexicon output can only narrow authority, never expand it.
- **Binding**: every record binds the exact canonical action (class + params
  hash) and the history commitment. Records are **single-use**.
- **CumAdm**: rails evaluate over trajectory history + candidate action, not
  the instantaneous state.
- **Decision-dominance (v1.4 T_unk)**: a U blocks iff at least one *admissible*
  resolution of it changes the admissibility outcome. Base evaluation resolves
  each U to its favorable admissible value; counterfactuals do the rest.
- **Fail-closed enumeration**: missing, malformed, expired, superseded,
  consumed, unverifiable, action-mismatched, or history-mismatched governance
  state fails closed. History semantics: a commitment must remain an ancestor
  (no rewrite); benign appends between evaluation and execution do not
  invalidate; revocation / safety escalation / mismatch do.

## Tests

| Suite | What it proves |
|---|---|
| `test_battery.py` | A5a/A5b/A5c regression gates (normative vs Lexicon v1.4) |
| `test_composition.py` | CumAdm blocks individually-admissible compositions; split-attack fails |
| `test_adversarial.py` | 11 adversarial coupling cases, all fail closed in the prescribed direction |
| `test_feedback.py` | Consequences return as Yield/evidence; no auto-promotion; success expands nothing |
| `test_sacrifice.py` | S1a/S1b/S2 executable: opaque inheritance fails, explicit delegation works, self-loosened rails rejected |
| `test_recovery.py` | Leverage recovery: batch sub-delegation, RegimeDelta proposal/batch-approval, S3 learned standing delegation |
| `test_review.py` | Third domain: batched retrospective review, per-item dispositions, review changes nothing |

Run: `python3 run_all.py` → 30 passed, 0 failed (2026-10-18).

## Known prototype limits (not defects in the contract)

- Action effects are simulated; the engine's real gates, biometrics, and
  cryptography are not modeled here.
- `narrow_scope` is currently identity (safety states other than RED/BLACK do
  not narrow scope in this prototype); the ratchet is enforced as ⊆ regardless.
- Single principal, single-threaded, wall-clock TTL of 300s.

## Leverage recovery (S1/S2)

- S1: `delegate_batch` — one principal decision, N individually-visible/revocable records.
- S2: `propose_rail_change` + `approve_rail_changes` — agent proposes with justification, granting principal disposes (batchable); agent self-approval rejected.

## Dogfood log

- 2026-10-18: test pollution caught cross-instance rail contamination — rail instances were shared across Governor instances, so one deployment's RegimeDelta leaked into another's. Fixed: each Governor deep-copies its rails at construction (per-deployment rail ownership, which the ratchet requires).

- 2026-10-18: `test_no_auto_promotion` caught a replay hole — an identical
  repeat action could re-execute on one record within TTL. Classified:
  **interface/coupling defect**. Fixed: records are single-use
  (`GOVERNANCE_CONSUMED`); schema and mapping doc updated to match.
  The battery earned its keep on the first run.
