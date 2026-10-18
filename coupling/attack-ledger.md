# Attack ledger

**Binary question under test:** can hostile execution alter governed state
without satisfying independently re-derived admission?

Each row is one attempted invariant violation. Columns are fixed; a row is
not "a test passed" but security evidence. Test volume ≠ security evidence.

| ID | Attempted invariant violation | Attacker capability assumed | Exact boundary attacked | Observed outcome | Expected safe state | Mutation status | Recovery status | Audit evidence | Residual weakness |
|---|---|---|---|---|---|---|---|---|---|
| R-1 | Exact replay: re-present an already-sealed (action, evidence) pair to execute a second mutation on one assent | Compromised agent or intercepted valid ceremony; can resubmit bytes | Engine admission (NineGates.evaluate / ConciergeInterface.execute) | **VULNERABLE (demonstrated):** second execution integrated and anchored on current main (failing test `exactReplayOfSealedActionMustHalt`, PR #2). Fix on branch: sealed-actionId set, halt at Gate 7 (`theta_assent: assent already consumed`) | Second presentation halted; exactly one seal per assent | Double mutation + double anchor on unpatched code | No recovery path pre-fix; post-fix the replay halts fail-closed, no recovery needed | Pre-fix: two SEAL lines for one assent (visible, not prevented). Post-fix: HALT gate=7 line | Fix is engine behavior change — **held for owner merge decision** (PR #2). Cross-instance replay (two engine instances, same actionId) still possible by design — actionIds are per-instance. |
| C-1 | Crash between mutation and seal: kill the process after perform, before the history append | Crash timing control (not code execution) | Prototype execute(): perform/seal window | **HELD:** orphaned `execution started` intent surfaced by `crash_audit()`; no silent mutation-without-seal. Consumption-first gives at-most-once across the window | Orphan visible; blind retry is operator error, not governor decision | Mutation may have happened exactly once; seal did not | Orphan requires substrate investigation before any retry | `execution started` with no matching `execution`/`execution aborted` | True at-most-once needs substrate cooperation (prepare/commit); the governor makes the ambiguity visible rather than resolving it. Prototype-only; engine Merkle-log crash window not yet attacked. |
| C-2 | Handled failure during perform: exception after partial mutation | Faulty/malicious action implementation | Prototype execute() exception path | **HELD:** `execution aborted` recorded; mutation exactly once; spent record refuses reuse (`GOVERNANCE_CONSUMED`) | Abort in audit trail; no silent second attempt | Single mutation | No recovery needed; fresh authorization requires fresh ceremony | `execution aborted` entry bound to constraint id | None at prototype level. |
| K-1 | Stale evaluation: execute after EVAL_TTL expiry | Clock control (advance) | Prototype governance-record freshness | **HELD:** `GOVERNANCE_EXPIRED` | Refuse | None | Re-evaluation required | Halt entry | Clock itself is trusted in the prototype (engine owns it in production). |
| W-1 | Alternate write path: mutate governed state without invoking the governor | Network attacker (HTTP) / in-process caller | Sidecar HTTP surface; engine substrate ownership | **HELD (by inspection):** sidecar exposes 4 routes; only the assent route reaches `concierge.execute`; `/v1/substrate` is GET-only; the executed action is the server-stored `pending` entry, never caller bytes at assent time; no-submit → `NoActiveCeremony`. In-process: `SubstrateState` is an immutable data class; `ConciergeInterface.substrate` is private and only assigned from `Integrated` outcomes | Single mutation path: submit → challenge → assent → execute | None via the examined surfaces | N/A (no bypass found) | Code structure (routes, pending map, private substrate) | **Residual:** Android VpnService/dispatcher path not yet reviewed — the "dispatcher is sole writer" claim for the device substrate is architectural and unverified. In-process reflection attacks are out of scope (process compromise = ambient authority, documented). |
| K-2 | Expired authority: evaluate under a lapsed AuthorityRecord | Clock control (advance past valid_until) | Prototype `_live_authority` | **HELD:** `AUTHORITY_EXPIRED` | Refuse | None | Re-grant required | Halt entry | Same trusted-clock caveat. Engine DurableMonotonicClock adversarial tests exist (rollback, corrupt state file) — not yet extended to hostile values. |

## Priority queue (ordered per 2026-10-18 program)

1. **Alternate write-path attacks** — mutation without invoking the governor. IN PROGRESS. Any success makes gate tests secondary.
2. **Action substitution / semantic mismatch** — partially covered (tampered rendering halts at Gate 7; hostile-alphabet injectivity fuzz). Open: ambiguous canonicalization concealing aggregate effect.
3. **Replay / duplication** — R-1 demonstrated + fix on branch. Remaining: challenge replay (voice — known residual), crash-recovery record replay.
4. **Revocation races** — covered at prototype (post-eval re-scan) and engine (`sealTimeRescanCatchesLateValidRevocation`, revocation matrix). Open: revocation *during* mutation window.
5. **Crash-window exploration** — C-1/C-2 at prototype. Open: engine Merkle-log crash window; anchor-failure window (partially covered: throwing anchor propagates, transition applied + sealed locally).
6. **Clock attacks** — K-1/K-2 at prototype; engine hostile-clock tests exist. Open: cooling-window disagreements under clock skew.
7. **Judgment/enforcement divergence** — corrupt the judgment output; verify enforcement re-derives. Prototype: exact-match admission tested (11 adversarial). Engine: the re-derivation boundary is the coupling layer's job — needs a hostile-Lexicon test.
8. **Cross-action composition** — prototype composition battery (cumulative rail, split-attack). Engine-level: not governed (by design — Lexicon layer's job). The trajectory-vs-transition gap is now a documented division of labor, not an open hole.

## Notes

- The ledger records *attempts*, including failed attacks (a failed attack is evidence the boundary held at that attacker capability).
- "Observed outcome" of HELD vs VULNERABLE is the security verdict; test counts are not.
- Engine behavior changes from red-team findings are held for the owner's explicit merge decision (precedent: 404/409 sidecar fix).
