# C-4 Decision: Cross-Epoch Cumulative Authority (Revised 2026-10-18)

## Decision
**maxMutations is an epoch-local bound.** A newly issued epoch receives a
fresh local budget ONLY because epoch issuance is itself a sovereign-
authorized act. Epoch issuance must not be reachable from an ordinary
holder, an EpochCapability, automatic expiry handling, or any other path
lacking fresh sovereign authorization.

Without that issuance invariant, epoch-local reset is an amplification
channel and Criterion 3 fails.

## Required mechanical properties

### 1. Sovereign-only issuance
Creating an epoch must require fresh authority from the designated
sovereign issuance path.

These paths must FAIL:
- Holder-initiated epoch creation
- Epoch creation from an EpochCapability (holders cannot mint)
- Automatic reissue on expiry

This path may SUCCEED:
- Sovereign-authorized issuance path only

The new budget is therefore newly authorized authority, not authority
manufactured by rotation.

### 2. Concurrent epochs
C-4 must explicitly define whether overlapping live epochs may govern the
same authority scope.

Rule: Two live epochs must not independently provide additive budgets over
the same sovereign, lineage, target scope, and mutation class unless that
overlap was explicitly authorized as additive.

Otherwise, concurrent epochs are a composition channel distinct from
sequential reset.

Note: The core currently lacks the stable lineage identity needed to
recognize that two epochs descend from the same continuing authority.
Therefore, until lineage exists, the narrow mechanically enforceable rule
is:
- Prohibit overlapping epochs for the same exact scope (if determinable), OR
- Explicitly record overlapping epochs as an unresolved amplification residual.

They cannot remain semantically accidental.

### 3. Revoke-and-reissue
Revocation must not itself authorize replacement. Reissuing an epoch
(even with identical scope and bounds) is valid ONLY if the issuance
independently traverses the sovereign-authorized issuance path.

Revocation plus automatic reissue would be a reset primitive. Reissuing
identical scope and bounds is still a new grant and must require the same
authority as any other epoch issuance.

### 4. Commit-time charging
A mutation is charged to the authenticated epoch bound to the
action/evidence AND live at the single commit instant t_c.

At t_c, the engine must verify:
- The bound epoch ID resolves to a live EpochCapability
- The epoch is unrevoked, unexpired, and its epoch number not revoked
- The effect is within the epoch's predicate

Then the accounting update and mutation commit must occur as one
crash-consistent serialized operation (already guaranteed by the
commit lock + durable store from Phase 3).

The epoch is not selected by submission time, validation-start time, or
completion time. This prevents a mutation from straddling a boundary and
opportunistically landing in either budget.

### 5. Characterization test
A test must establish reset as intentional current behavior: a new epoch
receives a fresh local budget. This proves the exact contract:
maxMutations constrains an epoch, not a continuing authority lineage.

If a future lineage mechanism changes this behavior, the test must be
deliberately replaced rather than changing silently.

## Named residual
GuardianLink does not currently enforce persistent cumulative constraints
across epoch rotation. Such enforcement requires a stable lineage/root
identity that survives expiry, revocation, replacement, and concurrent
epoch issuance. Without that identity, the engine has no mechanically
reliable key against which to maintain a persistent counter.

The later lineage specification must define at least:
- Lineage ID format and generation (stable across rotation)
- Binding semantics (how a mutation's lineage is established)
- Authorization for replenishment (what justifies a new budget against
  an existing lineage)

## Classification
- C-1: The epoch-local bound reaches the commit point. (CLOSED)
- C-4 current rule: A fresh sovereignly authorized epoch receives a fresh
  local budget.
- C-4 issuance invariant: Rotation cannot create authority without a fresh
  sovereign act.
- Concurrent epochs: Must be prohibited, explicitly additive, or retained as
  a named residual. Cannot remain semantically accidental.
- Revocation: Does not authorize reissuance or refresh.
- Commit attribution: Charge the bound epoch live at t_c.
- Lineage residual: Persistent cross-epoch limits require a stable root
  identity and a later specification.

## Status
- C-1: CLOSED (merged a12e9861).
- C-4: SPECIFIED (this document). Implementation gaps noted below.
- C-2/C-3/C-5: Classified (see c2-c3-c5-classification.md).

## Implementation gaps (as of 2026-10-18)
1. **Sovereign-only issuance not mechanically enforced.** `mintEpoch` is
   public on CapabilityIssuer. The spec requires it be reachable only from
   the sovereign path. Gap: no mechanical gate.
2. **Concurrent epoch overlap not prohibited.** No check prevents two live
   epochs with identical predicates. Gap: needs overlap detection at mint.
3. **Characterization test not yet written.** The reset behavior is specified
   but not pinned by a test.
