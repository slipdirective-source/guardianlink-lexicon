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

## 6. SOVEREIGN-EFFECT INSTRUMENTATION

For adversarial tests, instrument: bootstrapCount, issuanceAuthorityCreated, mintEpochCount, epochRotationCount, newLineageCount.

After legitimate setup, establish baseline. Every hostile CLI invocation must satisfy: **Delta sovereignOperations = 0**.

Stronger than exit codes: a CLI returning "permission denied" is insufficient if privileged side effects occurred before rejection.

## 7. COMMIT-POINT REQUIREMENT

Carry Phase-2 commit-point discipline forward. For every holder operation, define t_c. The assertion is not "capability was valid when CLI parsed it" but "capability authorized the exact mutation at the point the mutation became committed."

The CLI must not introduce: validate → delay/transform/dispatch → commit, where validity can change between validation and commitment. Prefer delegating the authoritative decision to the engine.

## 8. EXPLICIT NON-CLAIMS

Passing Outward-0 does not establish: hostile-process isolation, OS-user isolation, secret extraction resistance, memory inspection resistance, MAC/signature authenticity, malicious executable replacement, supply-chain integrity, remote protocol security.

Outward-0 establishes: **The legitimate holder-facing program surface does not amplify object-capability authority.**

## 9. EXIT CRITERION

OUTWARD-0 PASS iff:
- All adversarial tests reject.
- AND Delta sovereign issuance effects = 0 for every rejected case.
- AND Characterization test succeeds.
- AND Holder-facing production dependencies contain no holder-reachable SovereignRoot → SovereignIssuanceAuthority path.

Outward-0 is not testing whether sovereign functionality is difficult to discover. It is testing whether sovereign functionality is **unreachable** from the holder's authority domain.
