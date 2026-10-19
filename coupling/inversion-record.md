# Inversion Record: GuardianLink Authority Engine

**Date:** 2026-10-18
**Head SHA at inversion:** 83ecc38b101f
**CI status:** CI ✓, APK ✓, CodeQL ✓ (all green on head SHA)

## The Question That Inverted

Before C-1, every question was defensive: "Can this be trusted?"
After C-1, the question became: "Given exactly what we've demonstrated
can be trusted, what structures can we safely construct above it?"

This record documents the demonstrated trust boundary — what survived,
what was attacked, what remains uncertain, and why the remaining
uncertainty does not defeat the operational threshold for Outward-0.

## Properties That Survived Falsification

### 1. Assent Replay Resistance (R-1)
**Property:** An already-sealed (action, evidence) pair cannot authorize
a second mutation.

**Attack:** Re-presented a sealed actionId to the engine admission path.
**Result:** VULNERABLE on unpatched code (demonstrated double mutation).
**Fix:** sealedActionIds in NineGates; halt at Gate 7
(theta_assent: assent already consumed); consume at seal.
**Verification:** Failing test on unpatched main; fix verified on branch;
merged to main (6bf5e3ca). Time-decaying seal keys (Caleb's design):
records evicted exactly when the assent they consumed dies.
**Status:** SURVIVED (post-fix).

### 2. Epoch Mutation Bound Enforcement (C-1)
**Property:** An EpochCapability with maxMutations=N cannot authorize
more than N mutations.

**Attack:** Executed 3 mutations against an epoch with maxMutations=2.
**Result:** FALSIFIED — the commit path never called checkAndRecordEpoch.
**Fix:** MutationCapability.epochId binding verified at mint; commit path
derives epoch from the capability's authenticated binding and charges it.
(Caleb's design decision: derive epoch from authenticated action/evidence,
NOT an optional param on execute(); fail closed if binding absent/invalid.)
**Verification:** Failing test reproduced the violation; fix verified;
merged (a12e98613578).
**Status:** SURVIVED (post-fix).

### 3. Sovereign Issuance Confinement (10-test battery)
**Property:** Only SovereignRoot can issue epochs. No holder, epoch-holder,
attenuated capability, delegated authority, expired permit, or revoked
permit can manufacture issuance authority.

**Attacks:** Caleb's reconstructed 10-test battery:
1. Holder can't issue
2. Epoch holder can't issue
3. Attenuation can't create issuance
4. Delegation can't launder issuance
5. Expiry can't auto-refresh
6. Revocation ≠ reset-and-reissue
7. Concurrent overlapping epochs independently bounded
8. Rotation preserves lineage (new EpochId, same LineageId+RootId)
9. New lineage requires sovereign
10. Fresh sovereign issuance gets fresh local budget (characterization)

**Result:** All 10 held. Merged (8b644dd71a0e).
**Extension (2026-10-18):** MAC-signed permits (HMAC-SHA256) for
cross-process issuance. 6 additional tests: verify, tamper rejection,
wrong-key rejection, valid mint, double-use rejection, forgery rejection.
**Status:** SURVIVED.

### 4. Crash Consistency (Phase 3)
**Property:** Post-recovery state = some atomic prefix of operation history.
Durability of effect never precedes durability of the governance state
that constrains its interpretation. (Caleb's law, verbatim.)

**Mechanism:** WAL + fsync + idempotent replay as the single
linearization point for crash consistency AND cross-process serialization.
Fencing epochs for validate-stall-resume. Recovery semantics written first
as the crash-consistency oracle.

**Attack:** The crash harness caught a real off-by-one before going green
(recovery silently dropped every COMMIT record).
**Verification:** TLA+ bounded model checked (no errors). 165/165 green
at merge (b8c631eb86b3).
**Status:** SURVIVED.

### 5. WAL-Backed Permit Single-Use (2026-10-18)
**Property:** A consumed issuance permit cannot authorize a second epoch,
even across process restart.

**Mechanism:** DurableCapabilityStore.recordPermitConsumption() writes
PERMIT_CONSUMED to WAL with fsync. Recovery replays these records to
repopulate the consumedPermitIds set.

**Note:** The store-level primitive is implemented and tested. The
issuer-level mintEpochWithPermit uses its in-memory consumedPermitIds;
the automatic durable recording via DurableCapabilityStore at the
issuer level was not separately verified as a distinct integration test.
This is a bounded residual, not a known violation.
**Status:** SURVIVED (store-level); issuer↔store wiring is a documented
residual.

### 6. Holder CLI Authority-Surface Confinement (Outward-0)
**Property:** Possession and arbitrary use of the holder CLI grants no
authority beyond authority already embodied in the holder-supplied capability.

**Attacks (O0-1 through O0-16):**
- O0-1..O0-12: Command-surface confinement, dependency confinement,
  input non-amplification, failure atomicity, positive characterization.
  No CLI imports of SovereignRoot or SovereignIssuanceAuthority (verified).
- O0-13: Foreign epoch ID — holder-proposed epochId must not bind
  another holder's live epoch.
- O0-14: Consumed/revoked stay dead across restart.
- O0-15: Concurrent presentation — atomicity via engine synchronized block.
- O0-16: Revocation between parse and commit → rejection at t_c.

**Refinements (Caleb, 2026-10-18):**
- Count durable state, not instrumented calls (sovereign-delta oracle).
- Assert specific engine reason codes, not just rejection.
- O0-5 bearer model: serialized capability is a bearer reference;
  engine resolves against store, ignores predicate/bounds in the copy.
- O0-11 requires module split: check the shipped jar/classpath, not source.
- G4 fixture isolation: CLI must run where the sovereign test fixture
  isn't on the classpath.

**Verification:** PR #11 merged (8b644dd71a0e); PR #12 merged (317194255aa3).
CI green.
**Status:** SURVIVED.

### 7. Commit Serialization (Phase 1) + Capability Commit-Point Check (Phase 2)
**Properties:** Commits are serialized (no interleaving). Capability is
checked ONLY at execute() — the commit point — not before.

**Verification:** Merged (6d47b7c2, 533568165b6c). 7 property tests.
Verification coverage matrix.
**Status:** SURVIVED.

## Attacks Performed (Summary)

| ID | Attack | Outcome |
|---|---|---|
| R-1 | Assent replay (double execution) | FOUND, DEMONSTRATED, FIXED, MERGED |
| C-1 | Epoch bound violation (3 mutations on maxMutations=2) | FALSIFIED, CONFIRMED, FIXED, MERGED |
| C-3 | Crash between seal and anchor | ANALYZED — residual documented (durable seal tracking) |
| C-4 | Epoch overlap / budget laundering | DECIDED — overlap prohibited by default (mintEpoch(allowOverlap=false)) |
| H-1 | 404/409 status-code ordering leak | FIXED (held since Oct 11) |
| S-1 | Action substitution / semantic mismatch | HELD by existing coverage |
| J-1 | Judgment/enforcement divergence | HELD (prototype, 35/35) |
| K-1/K-2 | Stale evaluation / expired authority | HELD |
| K-3 | Clock skew shortening cooling windows | ANALYZED — trust-model boundary |
| W-1 | Alternate write path (sidecar/engine) | HELD by inspection |
| O0-1..O0-16 | Holder CLI authority-surface | ALL HELD |

## Residual Uncertainty (Bounded)

### R-U1: Issuer↔Store Durable Permit Wiring
The WAL-backed permit consumption primitive exists at the store level
and is tested. The automatic invocation of
DurableCapabilityStore.recordPermitConsumption from within
CapabilityIssuer.mintEpochWithPermit was not separately verified as a
distinct integration test. The in-memory consumedPermitIds in the issuer
provides single-use within a process lifetime; cross-restart single-use
depends on the store-level primitive being invoked.

**Why it doesn't defeat the threshold:** The store-level primitive is
implemented, tested, and green. The wiring gap is a missing integration
test, not a known violation. The in-process single-use is verified.
The cross-restart path has the mechanism but not the end-to-end test.

### R-U2: Cross-Instance Replay (Two Engine Instances, Same actionId)
ActionIds are per-instance. Two engine instances sharing no state could
each seal the same actionId. This is by design — actionIds are not
globally unique.

**Why it doesn't defeat the threshold:** The threat model is a single
engine instance (the sidecar deployment). Cross-instance coordination
requires an external anchor, which is explicitly out of scope (documented
in Phase 3: "Store rollback OUT OF SCOPE (needs external monotonic anchor)").

### R-U3: Android Dispatcher Path Unreviewed (W-1 residual)
The "dispatcher is sole writer" claim for the device substrate is
architectural and unverified. The Android VpnService/dispatcher path
has not been reviewed.

**Why it doesn't defeat the threshold:** Outward-0 claims are scoped to
the engine and the holder CLI, not the Android execution layer. The
Android path is a separate trust boundary with its own verification
program (APK builds green; the dispatcher review is future work).

### R-U4: Semantic Exfiltration (C-2) — No Provenance/IFC in Core
The core has no information-flow control. A capability could authorize
bytes that, when executed, exfiltrate data through a side channel.

**Why it doesn't defeat the threshold:** This is a declared semantic
boundary, not a claimed property. The core guarantees authorized bytes
execute, not that they mean the same thing in all contexts (C-3:
state-dependent meaning drift). Provenance/IFC is a Lexicon-layer concern.

### R-U5: Assent Composition (C-5) — Deferred to Principal
How multiple assents compose (ceremony layer) is deferred to the principal.

**Why it doesn't defeat the threshold:** Composition is explicitly out
of scope for the engine. The engine governs single actions; the ceremony
layer governs composition. This is a documented division of labor, not
a gap in a claimed property.

### R-U6: Forward Clock Jumps Shorten Cooling Windows (K-3)
A large forward time jump makes assent appear older, shortening the
effective cooling window.

**Why it doesn't defeat the threshold:** The clock is an engine-owned
trusted component. This is a trust-model boundary, not a bypass.
Mitigated by DurableMonotonicClock's throttled persistence.

## Why the Remaining Uncertainty Does Not Defeat the Operational Threshold

The operational threshold for Outward-0 is: **"Make the existing guarantees
observable without adding authority."**

The user-facing guarantee (brutally small, per Caleb):
- A capability cannot be widened through supported attenuation.
- Authority cannot be reused beyond allowance.
- Revoked authority cannot authorize a later commit.
- A successful commit is attributable to live authority at the commit point.

Every residual above is either:
1. **Out of scope for the claimed property** (R-U2, R-U3, R-U4, R-U5) —
   the claim never included cross-instance coordination, the Android
   dispatcher, information-flow control, or ceremony composition.
2. **A trust-model boundary, not a bypass** (R-U6) — the clock is trusted;
   the residual is environmental, not mechanical.
3. **A missing test, not a known violation** (R-U1) — the mechanism exists
   and is tested at the store level; the integration test is future work.

No known counterexample violates a claimed core invariant. The falsification
battery has been run to green. The evidence of what succeeded and what
failed is preserved in the attack ledger and this record.

Per the release doctrine (Caleb's words): "We tried hard enough to kill
the properties that matter, preserved the evidence of everything that
succeeded and failed, bounded what we still don't know, and the remaining
uncertainty no longer warrants withholding operation."

## What Inversion Means

The question inverts from "Can this be trusted?" to "Given exactly what
we've demonstrated can be trusted, what structures can we safely construct
above it?"

The authority engine is now a **working apparatus with demonstrated
falsification value**. The cognitive surface becomes the first constructive
program built on top of it.

**Development invariant (Caleb):** "Expansion rate ≤ falsification-growth
rate. If that inequality flips, stop adding surface area."

---

**Frozen:** 2026-10-18
**Next:** Surface Experiment 001 (spec frozen separately; not run pre-inversion)
