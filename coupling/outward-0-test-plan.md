# OUTWARD-0 TEST PLAN: Holder CLI Authority-Surface Falsification

## 1. CLAIM UNDER TEST

Possession and arbitrary use of the holder CLI grants no authority beyond authority already embodied in the holder-supplied capability.

More specifically: No CLI command, argument, environment input, serialized object, filesystem input, configuration value, or reachable holder-facing code path can create, obtain, invoke, reconstruct, or cause exercise of SovereignIssuanceAuthority or any equivalent sovereign issuance operation.

This is an in-process/object-capability claim. It does not claim cryptographic resistance to cross-process permit forgery.

## 2. REQUIRED ARCHITECTURE

Permitted authority direction:
```
SovereignRoot
  v
SovereignIssuanceAuthority
  v
mintEpoch(...)
  v
EpochCapability
  v
================ TRUST BOUNDARY ================
Holder CLI
  v
holder-permitted operations
  v
MutationCapability
```

Forbidden authority direction:
```
Holder CLI --X--> SovereignRoot
Holder CLI --X--> SovereignIssuanceAuthority
Holder CLI --X--> mintEpoch with sovereign authority
Holder CLI --X--> rotate epoch
Holder CLI --X--> create lineage
```

The CLI may consume holder authority. It must never manufacture or escalate authority.

## 3. ACCEPTANCE GATES

**G1. COMMAND-SURFACE CONFINEMENT**
The installed holder executable exposes no sovereign operation. No bootstrap. No mint. No epoch issuance. No rotate. No new-lineage. No sovereign permit generation. No root management. These operations must not merely be hidden or undocumented. They must be absent.

**G2. DEPENDENCY CONFINEMENT**
Holder-facing CLI code has no usable dependency path that gives it sovereign issuance authority. The meaningful property is not merely "there is no mint command" — it is "holder-controlled execution cannot reach sovereign authority."

**G3. INPUT NON-AMPLIFICATION**
All attacker-controlled CLI inputs must be incapable of becoming greater authority than what was supplied. For holder input authority A_in: Authority(output) ⊆ Authority(A_in). CLI parsing, deserialization, configuration, flags, environment variables, and filesystem state must not increase that set.

**G4. FAILURE ATOMICITY**
Rejected escalation attempts produce: no sovereign state transition, no epoch creation, no lineage creation, no capability consumption unrelated to the requested holder operation, no partial privileged effect.

**G5. POSITIVE CHARACTERIZATION**
Normal holder operations must still work. Otherwise tests 1–11 could all pass because the CLI is simply inert.

## 4. FALSIFICATION BATTERY

12 tests. Tests 1–11 are adversarial rejection. Test 12 is characterization.

**O0-1: SOVEREIGN COMMAND ABSENCE**
Enumerate the CLI command surface. Attempt obvious sovereign verbs and aliases: bootstrap, mint, mint-epoch, rotate, new-lineage, issue, root, sovereign.
Expected: Every attempted sovereign operation is rejected as nonexistent.
Falsifies if: Any holder-accessible command reaches sovereign behavior, including undocumented.

**O0-2: CLI HELP/COMPLETION SURFACE LEAKAGE**
Inspect --help, subcommand help, shell completion, generated metadata.
Expected: No sovereign operation appears as invocable CLI surface.
Reason: A command can remain registered even if documentation omits it.

**O0-3: DIRECT SOVEREIGN-AUTHORITY CONSTRUCTION**
Compile adversarial holder-side fixture attempting to instantiate SovereignIssuanceAuthority through every public holder-visible mechanism.
Expected: Construction impossible at type/API boundary.
Falsifies if: Holder code produces valid issuance authority without sovereign SovereignRoot.

**O0-4: ROOT ACQUISITION FROM HOLDER CAPABILITIES**
Begin with valid EpochCapability and MutationCapability. Attempt to obtain SovereignRoot or SovereignIssuanceAuthority through public methods, fields, conversions, cloning, callbacks, factories.
Expected: No escalation path exists.
(This re-tests Phase-2/C-4 boundary from outward-facing side.)

**O0-5: SERIALIZED CAPABILITY ESCALATION**
Supply CLI input: (1) valid holder capability, (2) modified, (3) additional sovereign-looking fields, (4) substituted rootId, (5) substituted lineageId, (6) authority-shaped serialized material.
Expected: Deserialization cannot promote representation into authority.
Invariant: Authority derives from possession of the live capability, not representation of its fields.

**O0-6: ARGUMENT-INJECTION ESCALATION**
Treat every CLI argument as adversarial. Attempt injection through flags, positionals, repeated/unknown/conflicting options.
Expected: Arguments select among holder-permitted operations only. No combination changes the authority class.

**O0-7: ENVIRONMENT/CONFIGURATION ESCALATION**
Attempt to influence privileged behavior through env vars, config files, working directory, default paths.
Expected: Configuration can configure holder operations but cannot select sovereign authority.
Falsifies if: Attacker-controlled config makes CLI load/construct/exercise root authority.

**O0-8: FILESYSTEM SUBSTITUTION**
Give CLI attacker-controlled files at every holder-readable input boundary, including files masquerading as root state, issuance authority, epoch state, lineage state.
Expected: Reading privileged-looking bytes does not confer privileged authority.

**O0-9: HOLDER OPERATION CONFUSED-DEPUTY TEST**
Use legitimate holder command but craft inputs so execution would require sovereign operation.
Expected: Operation fails closed. CLI cannot become confused deputy exercising unavailable authority.

**O0-10: EPOCH EXHAUSTION/INVALIDITY ESCALATION**
Supply capabilities that are exhausted, expired, revoked, consumed, wrong prefix/type, or otherwise incapable.
Expected: CLI rejects. Must not repair by issuing or rotating an epoch. (Automatic recovery would recreate the C-4 reset vector at application layer.)

**O0-11: DIRECT PRIVILEGED-SYMBOL REACHABILITY**
Build adversarial fixture against exact dependency/API surface shipped with holder CLI. Attempt direct access to sovereign issuance chain bypassing CLI dispatch.
Expected: Holder-facing dependencies expose no usable path to sovereign issuance.
Reason: O0-1 through O0-10 could pass while the executable still ships a library allowing privileged import.

## 5. CHARACTERIZATION TEST

**O0-12: VALID HOLDER OPERATION SUCCEEDS**
Provision honestly issued holder capability through sovereign test fixture. Invoke real holder CLI using only that holder authority. Assert:
1. CLI accepts the capability.
2. Authorized holder operation succeeds.
3. Resulting mutation is exactly the authorized mutation.
4. Target/type/usage/time/revocation constraints remain enforced.
5. No sovereign authority created or consumed.
6. No new epoch minted.
7. No new lineage created.

This proves Outward-0 is an authority-preserving outward interface, not merely a locked executable.

## 6. SOVEREIGN-EFFECT ORACLE (Durable State)

Count durable state, not instrumented calls. A bypass path that never increments a counter passes a counter check.

For each hostile invocation:
1. Snapshot the durable store (WAL contents + derived in-memory state) before.
2. Invoke the hostile CLI operation.
3. Snapshot after.
4. Require the diff to be empty, or limited to exactly the records the legitimate holder operation would write.

This covers G4's "no unrelated consumption": if a hostile invocation consumes a capability it shouldn't, or writes a WAL record it shouldn't, the diff catches it even if no counter was incremented.

Rationale: Counters are instrumentation; the WAL is the ground truth. A bypass that avoids the instrumented code path is still visible in durable state.

## 7. COMMIT-POINT REQUIREMENT

Carry Phase-2 commit-point discipline forward. For every holder operation, define t_c. The assertion is not "capability was valid when CLI parsed it" but "capability authorized the exact mutation at the point the mutation became committed."

The CLI must not introduce: validate → delay/transform/dispatch → commit, where validity can change between validation and commitment. Prefer delegating the authoritative decision to the engine.

## 8. EXPLICIT NON-CLAIMS

Passing Outward-0 does not establish: hostile-process isolation, OS-user isolation, secret extraction resistance, memory inspection resistance, MAC/signature authenticity, malicious executable replacement, supply-chain integrity, remote protocol security.

Outward-0 establishes: **The legitimate holder-facing program surface does not amplify object-capability authority.**

## 9. EXIT CRITERION

OUTWARD-0 PASS iff:
- All adversarial tests reject **with the expected engine reason code** (not just any rejection).
- AND Durable state diff is empty (or limited to legitimate records) for every rejected case.
- AND Characterization test succeeds.
- AND Holder-facing production dependencies contain no holder-reachable SovereignRoot → SovereignIssuanceAuthority path.

**Reason code requirement:** "All adversarial tests reject" passes vacuously if every test dies in the parser. Each test must assert the specific reason code from the engine (e.g., `revoked`, `expired`, `predicate_mismatch`, `bound_exceeded`). Pair each hostile case with a one-element-different control that succeeds, so the rejection is attributable to the hostile element.

Outward-0 is not testing whether sovereign functionality is difficult to discover. It is testing whether sovereign functionality is **unreachable** from the holder's authority domain.

---

## 10. REFINEMENTS (2026-10-18)

### O0-5 Stated Model: Bearer Reference
In a CLI, possession is representation. A serialized capability is effectively a bearer reference. The engine must resolve it against the store and **ignore any predicate or bound carried in the serialized copy**.

Test procedure: Tamper one field at a time in the serialized capability:
- Widen targetPrefix
- Raise maxMutations
- Move notBeforeMs earlier
- Substitute a different lineageId

Assert zero effect for each tamper. The engine's stored copy is authoritative; the presented copy is a lookup key, not a credential.

### O0-13: FOREIGN EPOCH ID (New Test)
Evidence carries a holder-proposed epochId. Attack: put another holder's live epoch in the store, have the CLI name it in evidence.

If the issuer binds the named epoch without checking that the caller was actually handed that epoch, epoch IDs become an escalation path. The binding must verify not just "this epoch exists and is live" but "this caller is authorized to use this epoch."

This is the confused-deputy case O0-9 gestures at, made concrete.

### O0-11 Requires Module Split
O0-11 (privileged-symbol reachability) cannot pass by source inspection alone. The test must check the **shipped artifact** (jar/classpath), asserting sovereign classes are absent.

If CapabilityIssuer and the sovereign path still share a module, this test cannot pass until the C-4.1 module split lands. Record as blocked on module split, not as passing.

### Missing Tests from Original Spec

**O0-14: KILL-AND-RESTART**
Kill the process after consuming or revoking a capability. Restart. Assert the capability stays dead (consumed stays consumed, revoked stays revoked). This tests the Phase-3 durability guarantee from the holder's perspective.

**O0-15: CONCURRENT CLI PROCESSES**
Two concurrent CLI processes present the same single-use capability. Exactly one must succeed; the other must be rejected with `already_consumed`. This tests the atomic check-and-consume under real concurrency.

**O0-16: PARSE-TO-COMMIT DELAY HOOK**
Insert a delay hook between CLI parsing and engine commit. In that window, revoke or consume the capability via a separate path. Assert the commit is rejected. This tests the t_c claim directly: validity must hold at commit time, not just parse time.

### G4 Fixture Isolation
The "no sovereign state transition" check must also cover the sovereign test fixture used for setup. Verify the fixture cannot be invoked by the CLI process at all — for example, by running the CLI in an environment where the fixture class is not on the classpath. If the test harness and the CLI share a process, the fixture is reachable; the test must account for this.
