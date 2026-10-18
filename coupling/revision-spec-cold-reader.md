# GuardianLink Trust Core: Revision Specification for Cold Reader Assessment
**Date:** 2026-10-18  
**Status:** Inversion point reached. Core claim fully specified.  
**Purpose:** Enable an independent assessor with no prior context to evaluate what the system guarantees, what it does not, and what remains.

---

## 1. The Question

**What is the smallest mechanically enforceable structure in which authority can be created, bounded, delegated, consumed, revoked, renewed, and composed without accidentally manufacturing more authority?**

This started as: "prove one personal agent couldn't overstep its delegated authority." It generalized to the question above.

---

## 2. What Was Built (Phases 1-3)

### Phase 1: Serialization
**Problem:** Can concurrent operations violate an authorization decision through race conditions?  
**Solution:** `ConciergeInterface.execute()` wraps its entire body in a `ReentrantLock` (`commitLock`). All authorization-to-commit sequences are serialized.  
**Tests:** 4 tests including reflection-based lock-holding proof and 8-thread overlap discriminator.  
**Status:** Merged, CI green.

### Phase 2: Capability Enforcement
**Problem:** Can authority be bypassed at the commit point?  
**Solution:** New `guardianlink.capability` package:
- `MutationCapability`: one admitted mutation, bound to `sha256Hex(evidence.rendering)`, consumable, non-replayable.
- `EpochCapability`: bounded set of mutations (maxMutations, maxBytes), predicate-constrained (targetPrefix, allowedTypes).
- `CapabilityIssuer`: mints capabilities; verifies attenuated children against live parent.
- `checkAndConsumeMutation` / `checkAndRecordEpoch`: atomic check+consume/record, synchronized.
- Commit path: on `GateOutcome.Integrated`, mints MutationCapability; substrate adoption crosses ONLY on `checkAndConsumeMutation` → else `Rejected`.

**Key bug caught:** TOCTOU in commit point — `t_c` read before minting; clock tick between read and mint made fresh capability "not yet valid." Fixed by binding `notBeforeMs` to `t_c`.

**Tests:** 24 falsification tests + 7 property tests (fixed seeds).  
**Status:** Merged, CI green.

### Phase 3: Crash Consistency
**Problem:** Do authorization decisions survive crash, restart, and process boundaries?  
**Solution:** 
- `RecoveryOracle`: reference semantics — post-recovery state must equal some atomic prefix of operation history.
- `DurableCapabilityStore`: WAL (`capability.log`) + fsync + idempotent replay. INTENT → fsync → COMMIT → fsync → in-memory apply. `recover()` replays COMMIT records, drops orphan INTENTs.
- `withStoreLock`: ReentrantLock + `FileChannel.lock()` (OS releases on death).
- Fencing epochs for validate-stall-resume.
- `CrashInjector` with 5 crash points; harness crashes at every point vs. oracle.

**Key bug caught:** `parseOp` off-by-one — recovery silently dropped EVERY COMMIT record. Fixed.

**TLA+:** Bounded model checked exhaustively (126 states, no errors). Unbounded ran 27M+ states, no violation.

**Threat boundary:** Store rollback (snapshot restore) OUT OF SCOPE — needs external monotonic anchor (future ExternalAnchor hook). Counters/epochs monotonic, never wall-clock. Expiry IS wall-clock (fail-closed on forward jump).

**Status:** Merged (b8c631e), CI green.

---

## 3. Composition Attacks (C-1 through C-5)

### C-1: Quantitative Composition — FALSIFIED, FIXED, CLOSED
**Question:** Can individually admissible mutations, each valid under its own capability, compose into a cumulative state violating an aggregate constraint?

**Result:** CONFIRMED. Test minted EpochCapability with maxMutations=2, executed 3 mutations — all 3 committed. Root cause: commit path called ONLY `checkAndConsumeMutation`; `checkAndRecordEpoch` existed but was never called. Wiring gap.

**Fix (merged a12e9861):**
- `MutationCapability` gained `epochId: String?` (authenticated binding).
- `mintMutation(..., epochId)` verifies at mint: epoch exists, is EpochCapability, not revoked, currently valid — else throws → `execute()` returns Rejected (fail closed).
- `ActionEvidence` gained `epochId: String?` (holder proposes; issuer verifies and BINDS).
- Commit path derives epoch from MutationCapability's authenticated binding (never evidence directly), calls `issuer.liveEpoch(boundEpochId)` then `checkAndRecordEpoch`.
- Test now asserts 2 Executed / 1 Rejected.

**Design decision (user):** Derive epoch from authenticated action/evidence, do NOT add optional EpochCapability param to `execute()`. "Authority should come from explicitly conveyed capability-bearing information rather than unrelated ambient context."

### C-4: Cross-Epoch Accumulation — SPECIFIED (Revised)
**Question:** When one valid epoch ends and another begins, does cumulative authority reset, or must prior consumption constrain the new epoch?

**Decision (revised):** maxMutations is an epoch-local bound. A newly issued epoch receives a fresh local budget ONLY because epoch issuance is itself a sovereign-authorized act.

**Required mechanical properties:**
1. **Sovereign-only issuance:** Epoch creation must require fresh authority from the designated sovereign path. Must FAIL: holder-initiated, from EpochCapability, automatic on expiry. (IMPLEMENTATION GAP: `mintEpoch` is currently public; restricting it requires architectural decision on sovereign path representation.)
2. **Concurrent epochs:** Two live epochs must not provide additive budgets over the same scope unless explicitly authorized. IMPLEMENTED: `mintEpoch` refuses overlapping live epochs with identical predicate unless `allowOverlap=true`.
3. **Revoke-and-reissue:** Revocation does not authorize replacement. Reissue must independently traverse sovereign path.
4. **Commit-time charging:** Mutation charged to the authenticated epoch bound AND live at t_c. Verified at t_c; accounting + commit as one atomic operation. (Already satisfied by C-1 fix.)
5. **Characterization test:** Pins "new epoch gets fresh N" as intentional. IMPLEMENTED: 4 tests.

**Named residual:** No persistent cross-epoch enforcement. Requires stable lineage/root identity surviving rotation. The later lineage specification must define: lineage ID format, binding semantics, authorization for replenishment.

**Status:** Specified in `coupling/c4-decision-cross-epoch.md`. Partially implemented (overlap check, characterization tests merged). Sovereign-only issuance remains a documented gap.

### C-2: Semantic Exfiltration — RESIDUAL
`Read(secret)` authorized; `Write("net/out", <bytes>)` authorized; composition is exfiltration neither admitted. Engine has no provenance tracking. Cannot be closed by testing; requires new machinery (IFC). **The core's claim does NOT include exfiltration prevention.**

### C-3: State-Dependent Meaning Drift — SEMANTIC BOUNDARY
Assent binds action bytes; execution happens against current substrate which may have changed. Same bytes, different consequence. **The core guarantees the authorized bytes execute; it does not guarantee they mean the same thing at execution as at assent.**

### C-5: Assent Composition — DEFERRED TO PRINCIPAL
Human assents to A and B separately; agent composes A+B into consequence neither showed. Mitigation is about what the principal was shown (ceremony design), not what the engine computed. **Requires principal design input; cannot be resolved unilaterally.**

---

## 4. The Inversion Point

**Methodology shift:** Up to C-4, every question was defensive (can authority escape? be replayed? break under concurrency? survive crash? compose invalidly?). After C-4, remaining uncertainty is CLASSIFIED rather than reflexively eliminated.

**The question inverts:**
- Before: "Can this be trusted?"
- After: "Given exactly what we've demonstrated can be trusted, what structures can we safely construct above it?"

**Boundary:** Applications (Personal GuardianLink, corporate governance, tiered sovereignty, AI delegation, user-defined tracking) are candidate constructions OVER the core, not capabilities established BY the core.

**The upside-down pyramid:** Built unusually far downward (authority mechanism) before building very far outward (utility). The system is sophisticated along the developed axis and skeletal along deliberately undeveloped axes. "Advanced" and "unfinished" measure different dimensions.

---

## 5. What the Core Guarantees (The Brutally Small Claim)

1. **A capability cannot be widened through the supported attenuation operation.** (`attenuateTo()` returns null on any widening. This is scoped to the modeled capability mechanism; it does not claim that no semantically relevant authority can expand through composition, substrate change, exfiltration, or epoch rotation — see C-2, C-3, C-4.)
2. **Authority cannot be reused beyond its allowance.** (Consumption enforced at commit point; replay refused.)
3. **Revoked authority cannot authorize a later commit.** (Revocation checked at t_c; crash-persistent via WAL.)
4. **A successful commit must be attributable to live authority at the commit point.** (Bound epoch verified live at t_c; capability consumed atomically with commit.)

**What it does NOT guarantee:**
- Cumulative limits across epoch rotation (C-4 residual: needs lineage)
- Exfiltration prevention (C-2 residual: needs provenance/IFC)
- Meaning stability across substrate change (C-3 semantic boundary)
- Composition visibility to principal (C-5 deferred)

---

## 6. Outward-0: Next Milestone (Defined, Not Started)

**Goal:** Make the existing guarantees observable without adding authority.

**Constraints:**
1. Every mutation requires a capability.
2. No privileged bypass for testing or administration.
3. Every rejection reports the mechanically relevant reason (expired, revoked, consumed, wrong prefix, disallowed type, exhausted usage, state-invalidated, etc.).
4. Successful mutation returns identifiers sufficient for the client and test harness to correlate the capability, authorization decision, and committed mutation within the demonstrated execution record. This is not provenance (C-2 remains open) and not a durable-audit guarantee.
5. Restart is part of the demo (consumed/revoked stays dead).
6. Outward build gets its own falsification tests.

**Success:** An independent caller can try to break the authorization boundary and watch the system refuse correctly, including across restart.

**Development invariant:** Expansion rate ≤ falsification-growth rate. If the inequality flips, stop adding surface area.

**Boundary:** Do not advertise cumulative sovereignty limits, provenance/IFC, or semantic stability. Expose what the system actually guarantees.

---


---

## 7a. Critical Corrections to Cold-Reader Assessment

The assessment is directionally correct but thinner than it reads in several places. These corrections are adopted.

### "Unforgeable" requires a stated threat model
On the JVM, `internal` is public in bytecode and reflection can construct anything (the test suite itself uses reflection). A sovereign authority object is only unforgeable against non-reflective callers in the same process.

The mechanical version: a **permit** the issuer verifies via MAC or signature, with the signing key held outside the holder's reach. The permit ID is recorded in the WAL so single-use survives restart. The guarantee then holds across the process boundary, not just the module boundary.

Threat model: the holder is an arbitrary in-process caller who may use reflection. The sovereign key is not in the holder's address space (or is hardware-bound). The permit is unforgeable iff the MAC/signature verifies and the key is not compromised.

### Rotate vs. new lineage is enforced by permit contents, not API shape
Both operations require sovereign authority, so API separation alone does not distinguish them. The permit must carry either an explicit `lineageId` (rotate: issue replacement under existing lineage) or an explicit `NEW` marker (create: establish genuinely separate constraint history), verified at mint time.

`LineageId` allocation must be durable and unique. If "new lineage" can reuse an ID, it becomes a history-reset path.

### Sovereign commands in the holder CLI are a privileged path
If `issue-epoch` lives in the same client binary as `execute`, "no secondary mutation path" is false by construction. The holder client (attenuate, execute, inspect) and the sovereign tool (issue, revoke, rotate) must be separate binaries; the holder client never links against the sovereign tool.

### Reason codes are a deliberate disclosure oracle
Precise denials (revoked vs. expired vs. wrong prefix) tell a holder what exists and what state it is in. This is acceptable for Outward-0 as a **deliberate disclosure** for demonstration purposes. The codes must come from the engine's authorization decision, not recomputed in the client (which would be a second judgment path).

### Sequencing: issuance before Outward-0
The assessment says "begin Outward-0 now," but the sovereign issuance fix is a precondition for the "no bypass" constraint. Correct order:
1. Split API + permit-based issuance (with the 10 falsification tests)
2. Lineage IDs (SovereignRootId, LineageId, EpochId) as distinct types
3. Then Outward-0 CLI (holder client only)

### Lineage IDs are future counter keys, not enforcement claims
The three identity types exist to provide a mechanically reliable key against which a future persistent counter can be maintained. They do not constitute cumulative enforcement. This must be explicit so nobody reads the IDs as a closed C-4.

### Still open (not covered by assessment)
- **Backward-clock hole:** Persist a time high-water mark; evaluate expiry against `max(now, hwm)`. Currently, a backward clock jump could revive an expired capability.
- **Lock layer:** Which lock does `execute()` hold during the full authorize-to-commit sequence? (Phase 1 added `commitLock`, but the interaction with the durable store lock needs explicit documentation.)
- **TLA+ coverage:** What exactly does the bounded model cover? The spec should state the modeled operations and the properties checked, so the "27M+ states, no violation" claim is interpretable.

---


---

## 7a-ii. Identity Separation and Sovereign Issuance Boundary (Specified 2026-10-18)

### Identity types
Three distinct identity types, each with a different role:

- **SovereignRootId**: Identifies the sovereign authority source. Stable across all epochs and lineages issued under it. The root is the authority source; issued capabilities are bounded products of it. The root itself is NOT a consumable permit.

- **LineageId**: Identifies a continuing constraint history. Stable across epoch rotation within the same lineage. Exists to provide a mechanically reliable key against which a future persistent counter can be maintained. Does NOT currently enforce cumulative constraints — that remains explicitly residual.

- **EpochId**: Identifies a single epoch (one issuance, one local budget). Unique per mint. The unit to which `maxMutations` applies.

### Operations
- **Rotate Epoch**: Issue a replacement epoch under the SAME lineage. The permit carries an explicit `lineageId`. The new epoch receives a fresh local budget because the issuance was sovereign-authorized, not because the old epoch's consumption was forgotten.

- **New Lineage**: Establish a genuinely separate constraint history. The permit carries an explicit `NEW` marker (not a lineageId). This is a distinct sovereign operation, not a rotation synonym. A caller cannot erase cumulative history by labeling replacement as new lineage creation.

`LineageId` allocation must be durable and unique. If "new lineage" can reuse an ID, it becomes a history-reset path.

### Sovereign issuance boundary
The sovereign issuance authority is structurally separate from mutation authority:

1. **SovereignIssuanceAuthority** is a distinct type. It cannot be constructed through the public capability API.

2. It cannot be derived from, attenuated from, or delegated via a `MutationCapability` or `EpochCapability`. Holder-held authority cannot become issuance authority.

3. `mintEpoch` requires possession of a live `SovereignIssuanceAuthority` object. Not a boolean flag, not a role string, not a caller identity check.

4. Expiry, revocation, exhaustion, or destruction of an epoch never invokes issuance. There is no automatic renewal path.

5. Reissue (even with identical scope and bounds) uses the same sovereign path as first issue. Revocation does not authorize replacement.

6. `allowOverlap=true` requires sovereign authorization. It cannot be proposed by holder-controlled evidence alone (holder cannot set it via epochId, lineageId, or other holder-supplied data).

7. **Threat model for "unforgeable":** On the JVM, `internal` visibility is public in bytecode and reflection can construct anything. The mechanical guarantee is a **permit** verified by MAC or signature, with the signing key held outside the holder's address space. The permit ID is recorded in the WAL so single-use survives restart. The guarantee holds across the process boundary, not just the module boundary.

8. The sovereign root is the persistent authority source. Individual issuances may use consumable permits (one permit per mint, recorded in WAL), but the root itself is not consumed.

### Why this matters for C-4
C-4 does not require cumulative cross-epoch enforcement yet. It requires making epoch creation itself **structurally incapable of becoming the mechanism that defeats epoch-local enforcement**.

The clean boundary: fresh sovereign issuance may intentionally receive a fresh local budget; capability holders cannot cause that reset themselves.

If epoch creation were reachable through holder-controlled authority, automatic renewal, or anything derived from a consumable capability, then `maxMutations` could be effectively refreshed by rotating epochs. That would be an authority-reset path, not merely an implementation detail.

---

## 7b. Open Items for Assessor

1. **Sovereign-only issuance (C-4.1):** How should the sovereign issuance path be mechanically distinguished from general issuer access? Current `mintEpoch` is public. Options: split API, sealed authorization token, module boundary. Needs architectural decision.

2. **Lineage identity:** What should the stable root identity look like? Must survive expiry, revocation, replacement, and concurrent issuance. This is the prerequisite for any future persistent cross-epoch constraints.

3. **Outward-0 design:** What is the thinnest client that makes denials observable without becoming a second authority path?

4. **Release assessment:** Given the classified residuals (C-2, C-3, C-4 lineage, C-5), does the remaining uncertainty warrant withholding operation, or is bounded operation with continuous red-teaming the correct mode?

---

## 8. Key Files

**Engine (Guardianlink repo, main):**
- `src/main/kotlin/guardianlink/capability/Capabilities.kt` — capability types, issuer, enforcement
- `src/main/kotlin/guardianlink/durability/` — WAL, recovery oracle, crash harness
- `src/main/kotlin/guardianlink/core/ConciergeInterface.kt` — execute() with commit lock + capability check

**Spec (guardianlink-lexicon repo, main):**
- `coupling/c4-decision-cross-epoch.md` — revised C-4 decision
- `coupling/c2-c3-c5-classification.md` — residual classification
- `coupling/composition-attacks.md` — original C-1..C-5 scope
- `coupling/attack-ledger.md` — full attack history
- `coupling/phase3-threat-boundary.md` — durability threat model

**Tests:**
- `CapabilityFalsificationTest.kt` — 24+4 falsification tests (incl. C-4 characterization)
- `CapabilityPropertyTest.kt` — 7 property tests
- `CrashHarnessTest.kt` — crash consistency vs. oracle
