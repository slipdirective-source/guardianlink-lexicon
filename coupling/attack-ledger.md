# Attack ledger

**Binary question under test:** can hostile execution alter governed state
without satisfying independently re-derived admission?

Each row is one attempted invariant violation. Columns are fixed; a row is
not "a test passed" but security evidence. Test volume ≠ security evidence.

| ID | Attempted invariant violation | Attacker capability assumed | Exact boundary attacked | Observed outcome | Expected safe state | Mutation status | Recovery status | Audit evidence | Residual weakness |
|---|---|---|---|---|---|---|---|---|---|
| R-1 | Exact replay: re-present an already-sealed (action, evidence) pair to execute a second mutation on one assent | Compromised agent or intercepted valid ceremony; can resubmit bytes | Engine admission (NineGates.evaluate / ConciergeInterface.execute) | **VULNERABLE (demonstrated), FIX VERIFIED:** second execution integrated and anchored on unpatched main (failing test `exactReplayOfSealedActionMustHalt`, PR #2). Fix on branch `redteam/assent-replay`: sealed-actionId set in NineGates, halt at Gate 7 (`theta_assent: assent already consumed`), consume at seal — **CI green** (`:test` + `:guardianlink-sidecar:test`, incl. the new replay test, the updated composition test, and a corrected stale sidecar test asserting 409-while-busy) | Second presentation halted; exactly one seal per assent | Double mutation + double anchor on unpatched code | No recovery path pre-fix; post-fix the replay halts fail-closed, no recovery needed | Pre-fix: two SEAL lines for one assent (visible, not prevented). Post-fix: HALT gate=7 line | Fix **merged to main** 2026-10-18 (merge commit 6bf5e3ca) per owner authorization, with time-decaying seal keys (records evicted exactly when the assent they consumed dies) and the 404/409 sidecar fix (unknown-action check before busy check, held since Oct 11). Branch CI was green on `:test` + `:guardianlink-sidecar:test`. Cross-instance replay (two engine instances, same actionId) still possible by design — actionIds are per-instance. |
| C-1 | Crash between mutation and seal: kill the process after perform, before the history append | Crash timing control (not code execution) | Prototype execute(): perform/seal window | **HELD:** orphaned `execution started` intent surfaced by `crash_audit()`; no silent mutation-without-seal. Consumption-first gives at-most-once across the window | Orphan visible; blind retry is operator error, not governor decision | Mutation may have happened exactly once; seal did not | Orphan requires substrate investigation before any retry | `execution started` with no matching `execution`/`execution aborted` | True at-most-once needs substrate cooperation (prepare/commit); the governor makes the ambiguity visible rather than resolving it. Prototype-only; engine Merkle-log crash window not yet attacked. |
| C-2 | Handled failure during perform: exception after partial mutation | Faulty/malicious action implementation | Prototype execute() exception path | **HELD:** `execution aborted` recorded; mutation exactly once; spent record refuses reuse (`GOVERNANCE_CONSUMED`) | Abort in audit trail; no silent second attempt | Single mutation | No recovery needed; fresh authorization requires fresh ceremony | `execution aborted` entry bound to constraint id | None at prototype level. |
| K-1 | Stale evaluation: execute after EVAL_TTL expiry | Clock control (advance) | Prototype governance-record freshness | **HELD:** `GOVERNANCE_EXPIRED` | Refuse | None | Re-evaluation required | Halt entry | Clock itself is trusted in the prototype (engine owns it in production). |
| W-1 | Alternate write path: mutate governed state without invoking the governor | Network attacker (HTTP) / in-process caller | Sidecar HTTP surface; engine substrate ownership | **HELD (by inspection):** sidecar exposes 4 routes; only the assent route reaches `concierge.execute`; `/v1/substrate` is GET-only; the executed action is the server-stored `pending` entry, never caller bytes at assent time; no-submit → `NoActiveCeremony`. In-process: `SubstrateState` is an immutable data class; `ConciergeInterface.substrate` is private and only assigned from `Integrated` outcomes | Single mutation path: submit → challenge → assent → execute | None via the examined surfaces | N/A (no bypass found) | Code structure (routes, pending map, private substrate) | **Residual:** Android VpnService/dispatcher path not yet reviewed — the "dispatcher is sole writer" claim for the device substrate is architectural and unverified. In-process reflection attacks are out of scope (process compromise = ambient authority, documented). |
| K-2 | Expired authority: evaluate under a lapsed AuthorityRecord | Clock control (advance past valid_until) | Prototype `_live_authority` | **HELD:** `AUTHORITY_EXPIRED` | Refuse | None | Re-grant required | Halt entry | Same trusted-clock caveat. Engine DurableMonotonicClock adversarial tests exist (rollback, corrupt state file) — not yet extended to hostile values. |

| C-3 | Crash between seal and anchor / crash durability of seal tracking (engine) | Crash timing control + retry | Durability boundary: in-memory ledger/substrate/sealedActionIds vs durable anchor | **ANALYZED — residual documented:** MerkleAuditLog is in-memory; the anchor file is the durable record. Crash after seal but before anchor: mutation and seal are lost with the process (fail-safe — no phantom mutation, but the assented action vanishes without a record; recovery is a fresh ceremony). Crash after anchor commit but before response: the anchor holds the seal, but `sealedActionIds` is in-memory and dies with the process — a direct engine embedder retrying the same actionId on a fresh instance re-executes (double seal, detectable in the anchor log, not prevented). Via the sidecar this path is closed: the pending map is also in-memory, so any retry requires a new submit (new actionId) and a fresh assent ceremony | None (seal-before-anchor crash) / double seal + double anchor on direct-engine retry after anchor commit | Fresh ceremony (sidecar) | Anchor log shows the true durable history; in-memory ledger is explicitly non-durable | **Durable seal tracking** (persist consumed actionIds alongside the anchor) would close the direct-embedder retry window. Shipped deployment (sidecar) is safe via fresh-ceremony requirement. |
| S-1 | Action substitution / semantic mismatch at the engine boundary | Caller-controlled bytes at submit, challenge, or assent | Rendering binding (Gate 7), evidence construction | **HELD by existing coverage:** render injectivity + hostile-alphabet fuzz (NineGatesAdversarialTest); Gate 7 halts on any rendering mismatch (`tamperedRenderingAlwaysHaltsAtGate7`, 40-case fuzz); sidecar builds evidence server-side from the stored action — caller bytes at assent time are never used (`pending.remove`, not request parsing) | None | N/A | Halt lines at Gate 7 | Concealed aggregate effect (an accurately-rendered action whose *consequences* exceed what the rendering conveys) is a semantic gap, not a canonicalization gap — not mechanically testable; owned by the Lexicon layer's consequence evaluation. |
| J-1 | Judgment/enforcement divergence: corrupt the judgment output, verify enforcement re-derives | Compromised or fabricated judgment layer output | Prototype Governor admission boundary | **HELD (prototype, 35/35):** 11 adversarial tests — stale decisions, substituted actions, omitted U, forged provenance, replayed records, safety downgrades, rail loosenings, execution without evaluation, valid-constraint-missing-authority all fail closed; the Governor admits only exact re-derivation matches. Engine N/A: the Kotlin gates have no separate judgment layer (they ARE the enforcement); the judgment/enforcement split lives at the coupling layer | None | N/A | Governor halt entries | None at prototype level. |

| K-3 | Clock skew shortens cooling windows (engine) | Control of time source (NTP jump, VM suspend/resume) | Engine-owned MonotonicClock vs cooling-window enforcement (Gate 7, theta_cool) | **ANALYZED — residual documented:** cooling boundaries exactly tested (`coolingWindowBoundaries`); hostile-clock tests cover crash-safety (`hostileClockNeverCrashes`) and durability (`durableClockNeverRollsBackAcrossRestart`, corrupt state file). A large FORWARD jump makes assent appear older, shortening the effective cooling window. Inherent to the trust model — the clock is an engine-owned trusted component (a request cannot substitute it) — mitigated by DurableMonotonicClock's throttled persistence. No testable in-process attack remains; the residual is environmental | None in-process | N/A | Halt/integrate lines at Gate 7 | Forward time jumps shorten cooling windows; accepted as a trust-model boundary, not a bypass. |

## Priority queue (ordered per 2026-10-18 program)

1. **Alternate write-path attacks** — W-1 HELD (see ledger). Residual: Android dispatcher path unreviewed.
2. **Action substitution / semantic mismatch** — S-1 HELD (see ledger). Residual: concealed-aggregate-effect is a semantic gap owned by the Lexicon layer.
3. **Replay / duplication** — R-1 demonstrated, fix verified on branch, merge held. Remaining: voice challenge replay (known residual), crash-recovery replay → C-3 residual (durable seal tracking).
4. **Revocation races** — covered at prototype (post-eval re-scan) and engine (`sealTimeRescanCatchesLateValidRevocation`, revocation matrix). In-process commit point is the seal: synchronous gate8→rescan→seal admits no interleaving; revocation after seal correctly applies forward. No testable in-process race remains.
5. **Crash-window exploration** — C-1/C-2 (prototype) HELD; C-3 (engine) analyzed, residual documented (durable seal tracking).
6. **Clock attacks** — K-1/K-2 (prototype) HELD; engine hostile-clock + durable-clock tests exist (rollback, corrupt state, throttle). K-3 analyzed: forward jumps shorten cooling windows; trust-model boundary.
7. **Judgment/enforcement divergence** — J-1 HELD (see ledger).
8. **Cross-action composition** — prototype composition battery (cumulative rail, split-attack) HELD. Engine-level: not governed by design (Lexicon layer's job). Documented division of labor.

| H-1 | 404/409 status-code ordering (sidecar) | HTTP prober | Challenge endpoint error precedence | **FIXED (was held since Oct 11):** `issueChallenge()` checked ceremony-busyness before action existence, returning 409 for nonexistent actionIds during a live ceremony (leaking ceremony liveness to probes). Unknown-action check now comes first: 404 regardless of ceremony state. Original test expectation restored | None | N/A | Status codes | None. Note: an interim test-only patch (expecting 409) was written without the Oct 11 context and reverted — the code was wrong, not the test. |

## Architectural principle (sharpened 2026-10-18, via Copilot/NIST SP 800-57-1r5)

**The sole writer is not a permanent privileged component. It is a
temporarily instantiated, scope-bound capability whose authority decays
unless independently renewed.**

Consequences enforced by this program:
- Capability lifetime is a first-class property (NIST SP 800-57 Part 1
  Rev. 5: keys have authorized usage periods). Every concrete
  cryptographic capability is short-lived.
- Autonomy may ratchet upward while authority continuously decays: a
  larger envelope at the next authorization event can be justified by
  reliability history, but possession of an old authorization never
  bootstraps itself into more authority.
- The inversion that matters: time decay must never make an existing key
  more powerful merely because time passed. Scope increases solely
  through renewed authorization.
- Self-renewal is prohibited: the agent cannot renew or escalate its own
  authority merely by holding K_n. Renewal is an independent
  authorization event by the principal.
- Blast radius: stealing a capability yields whatever bounded authority
  remains in its scope and lifetime — never indefinite writer status.

Status: R-1's seal keys implement the decay half (keys die with the
assent that created them). The epoch-capability form (K_{S,C,t}:
"mutations in scope S for the next epoch, subject to C") exists at the
prototype's standing-delegation layer, not yet at the engine.

## Notes

- The ledger records *attempts*, including failed attacks (a failed attack is evidence the boundary held at that attacker capability).
- "Observed outcome" of HELD vs VULNERABLE is the security verdict; test counts are not.
- Engine behavior changes from red-team findings are held for the owner's explicit merge decision (precedent: 404/409 sidecar fix).
