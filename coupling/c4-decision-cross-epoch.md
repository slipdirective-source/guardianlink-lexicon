# C-4 Decision: Cross-Epoch Cumulative Authority (2026-10-18)

## Decision
**EpochCapability limits are epoch-local** unless a separately specified
persistent/lineage constraint says otherwise. Issuance of a new epoch must
not itself be interpreted as renewal or expansion of any authority whose
governing constraint persists across epochs.

NOT adopted: unconditional cross-epoch accumulation in v2.2.
NOT adopted: "epoch renewal inherently resets underlying cumulative authority."

## Criteria
1. **Epoch meaning determines downstream.** If an epoch is a complete new
   authorization decision, resetting can be coherent. If it's technical
   renewal around continuing authority, resetting creates a composition
   channel (unbounded effect via waiting for boundaries).
2. **Don't silently convert specifications.** "No more than N under this
   EpochCapability" (local) vs. "No more than N under this continuing
   delegated authority" (persistent) are materially different. C-1 enforces
   the first; C-4 asks whether the second is intended. Not to be conflated.
3. **No amplification without new sovereign act (strongest).** If two states
   differ only in epoch issuance/rotation, and cumulative authority increases
   without a newly authorized decision justifying it, rotation has become an
   authority-amplification operation. Prohibited by the core principle:
   downstream holders must not manufacture stronger authority than received.
4. **Operations vs. consequences.** Some limits naturally reset with a
   window; others describe cumulative consequences that should not reset on
   credential rollover. A future spec may distinguish these — not smuggled
   into the C-1 fix.
5. **Mechanically identifiable.** The rule must be implementable without
   semantic intuition from the engine.

## Why this narrow rule
C-1 had a crisp object (EpochCapability) and crisp mechanism
(checkAndRecordEpoch); the defect was enforcement not reaching commit.
C-4 requires defining what persists across epoch identities and what
authorizes replenishment — a different state/authority abstraction. Do not
force it into EpochCapability merely because that's the available object.

## Status
- C-1: CLOSED (enforcement wired to commit, merged a12e9861).
- C-4: RECORDED as epoch-local accounting confirmed; cross-epoch persistent
  constraints require an explicit authority-lineage specification before
  mechanical enforcement is claimed.
- The epoch-rollover fresh-budget bypass is classified as a specification
  boundary (known residual), not a demonstrated defect.

## Extension hook
A future `PersistentConstraint` or authority-lineage mechanism may specify
cross-epoch accumulation. Until such a specification exists with its own
authorization semantics, no cross-epoch enforcement is claimed.
