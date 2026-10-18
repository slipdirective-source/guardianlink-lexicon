# Attacking the two residuals: C-3 and crash-around-exhaustion

**Status:** ATTACK ANALYSIS 2026-10-18. No implementation. This document
attacks the two honestly-marked residuals with the actual commit path
as the target. Code references are to Guardianlink main `6bf5e3ca1c9c`.

## 1. The commit path as built

`ConciergeInterface.execute()` (`core/ConciergeInterface.kt:101`):

1. `gates.evaluate(ctx)`:
   - `sealedActionIds[ctx.actionId] = ctx.assentedAtMs`
     (`gates/NineGates.kt:244`) — **in-memory** consumption record.
   - `appendAudit("SEAL ...")` — **in-memory** Merkle log.
   - returns `Integrated(newSubstrate, sealRoot)`.
2. `substrate = outcome.newSubstrate` — **in-memory** field.
3. `anchor.anchor(root, entryIndex, timestampMs)` — **durable**
   (`anchors.log`, append-only file).
4. returns `Executed`.

Two records of "this action executed" exist: the volatile one
(`sealedActionIds`, consulted at Gate 7) and the durable one (anchor
file, never consulted at Gate 7). On crash they diverge, and the
check uses the volatile one. That sentence is the whole attack.

## 2. C-3: crash windows

| Window | Crash point | Durable state | Memory on restart | Retry verdict |
|---|---|---|---|---|
| W1 | before/during `evaluate()` | nothing | clean | Safe: nothing committed; retry is a first execution. |
| W2 | after `evaluate()` returns, before substrate assignment | nothing | clean | Safe: same as W1. |
| W3 | after substrate assignment, before `anchor.anchor()` | nothing | clean | Safe-ish: the first execution never durably happened and the embedder never saw success. Retry is effectively first. (Audit shows nothing; acceptable.) |
| **W4** | **after `anchor.anchor()` returns, before the embedder durably records success** | **anchor file contains the seal** | **wiped: `sealedActionIds` empty, substrate fresh** | **VULNERABLE: retry re-executes. Double external effect; anchor file holds two seals for one assent.** |
| W5 | `anchor.anchor()` throws | nothing new | intact: `sealedActionIds` HAS the actionId | Safe from double-execution: retry hits Gate 7 consumption refusal. (Embedder sees `AnchoringFailed` with a committed in-memory mutation — fail-loud per contract, a separate error-semantics issue, not C-3.) |

### 2.1 The confirmed attack (W4), step by step

Precondition: a **direct embedder** — anything calling
`concierge.execute()` itself and retrying after crash/timeout. (The
Android dispatcher pattern, not the sidecar HTTP API; see §2.2.)

1. Embedder calls `execute(action, evidence)`, actionId `A`.
2. NineGates seals: `sealedActionIds[A] = t`; SEAL in the ledger;
   `Integrated` returned.
3. `substrate = newSubstrate`; `anchor.anchor(...)` fsyncs the seal
   root to `anchors.log`.
4. **Process dies** (kill -9, OOM, battery, panic) before the embedder
   records the `Executed` result.
5. Restart: `sealedActionIds` empty, substrate back to genesis, anchor
   file holding the seal.
6. Embedder, which never saw a result, retries `(action, evidence, A)`.
7. Gate 7 consumption check: `sealedActionIds` has no `A` → passes.
8. All gates pass (assent still live) → seals again, anchors again.
9. Any external effect of the action (packets, writes, calls) happens
   a second time. One assent → two executions.

### 2.2 Why the sidecar HTTP path is not vulnerable — and why that doesn't generalize

The sidecar's `assent()` (`GuardianLinkEngine.kt`) consumes the
**server-owned** actionId namespace: `pending.remove(actionId)` and
`activeCeremony = null` (in `finally`, consumed whether gates pass or
fail). After a crash, `pending` is gone; the old actionId does not
exist; `assent()` returns `UnknownAction`. There is no public API by
which the old `(action, evidence)` can be re-presented.

This safety is a property of the **transport's namespace ownership**,
not of the engine. Any embedder that constructs `ActionEvidence`
directly — the Android dispatcher, a future Rust core, a test harness
— bypasses it. The engine-level invariant ("one assent → one
execution") must not depend on which transport the embedder used.

### 2.3 Why time-decay doesn't close it

The `sealedActionIds` keys decay with the assent (`evictDecayedSeals`):
a stale key is a dead key even if the record is lost. True — but a
crash doesn't wait for decay. W4 replays a **fresh** assent whose
consumption record was lost, inside its validity window (up to
`maxAssentIdleMs`, 24h). Decay bounds the replay window; it does not
close the hole.

### 2.4 Required mechanism (build constraint, not implementation)

A **durable seal log**: before `evaluate()` returns `Integrated`
(i.e., before the seal is visible to any embedder), append
`(actionId, mutationHash, assentedAtMs)` to an append-only file and
fsync. On startup, rebuild the consumption set from the log; Gate 7
checks the rebuilt set.

Ordering (intent before effect, as in the prototype's `crash_audit()`):
1. Durably log seal intent.
2. Commit the mutation.
3. (Durably log completion — optional; see recovery.)

Recovery is conservative: any actionId in the log is refused, whether
or not completion was logged. Crash between intent and commit →
actionId dead forever (availability cost; the embedder starts a new
ceremony with a new actionId). This is fail-closed in the correct
direction: it can deny a legitimate retry, it can never permit a
double execution.

Pruning: entries may be lazily pruned once their assent is dead under
the same `theta_assent_idle` condition (a dead assent can't authorize
anyway, so a crash before pruning only causes a correct refusal).
The anchor file cannot serve this purpose as built: its lines are
`entryIndex|root|timestampMs|prevAnchorHash` — no actionId. Either a
separate `seals.log` or an actionId-bearing anchor line is required.

Seals are low-frequency (human-ceremony pace), so fsync-per-seal is
affordable. The high-frequency path needs a different mechanism (§3).

## 3. Crash around exhaustion (H1)

Target: the future epoch-capability implementation. The naive
implementation separates three steps:

```
check:  if (usage[k.id] >= k.maxMutations) refuse()
commit: commit(m)
record: usage[k.id]++; persist(usage)   // maybe batched
```

### 3.1 Interleavings

- **E1 — crash between commit and record.** Effect committed,
  consumption lost. On recovery the counter undercounts; the
  capability overspends. Signature valid, predicate valid, TTL valid —
  the bound is advisory.
- **E2 — crash between record and commit.** Consumption recorded,
  effect never committed. Underspend: legitimate authority denied.
  Fail-closed (availability cost), not a safety violation.
- **E3 — lazy/batched persist, crash inside the batch window.** Same
  as E1 without needing instruction-level precision: any crash in the
  window loses accounting.

E1 is the attack. Note it needs no malice — ordinary crashes suffice,
which is why it's the honest residual rather than a hypothetical.

### 3.2 In-process TOCTOU

If the commit boundary is multi-threaded, check-then-act on the usage
counter is itself racy: two threads can both pass the check with one
unit remaining. The spend (decrement) and the commit must be under the
same lock — or the boundary must be single-threaded. (The engine's
`evaluate()` is currently called under the sidecar's `executeLock`;
the direct-embedder path must provide equivalent serialization. This
is a build constraint on every embedder, not just the sidecar.)

### 3.3 Epoch-boundary races

- A commit in flight as the epoch expires: validity is checked at the
  commit instant `t_c` (`Valid(C, t_c)`); a live reservation does not
  extend the TTL. `t_c > notAfter` refuses even with budget remaining.
- Crash with an open reservation, recovery in a new epoch: the
  durable usage record is keyed by capability id; it cannot leak into
  the new epoch's accounting. The old capability is dead by TTL; its
  reservations die with it (counted as spent — conservative, §3.4).

### 3.4 Required mechanism: reservations

Durably reserve `R` units **before** spending from the reservation:

```
reserve: durableUsage[k.id] += R; fsync        // before any spend
spend:   in-memory R-- ; commit(m)             // no I/O per commit
```

On crash, unspent `R` is lost but counted as spent (conservative).
Invariant: **`durableUsage >= actualCommits` always.** Overspend is
impossible; underspend is bounded by `R`. `R` tunes I/O cost against
the underspend bound — for TUN line rate, thousands of packets per
fsync.

Per-packet fsync is thereby avoided without weakening H1. The
per-packet dedup set stays in-memory (decays with the capability); a
crash loses it, but post-crash duplicates still consume the
attacker's own reservation — the bound holds even when dedup
doesn't.

## 4. The unified principle

§2.4 and §3.4 are one pattern, not two mechanisms:

**Durable intent precedes effect; recovery assumes the worst.**

- C-3: durable `(actionId → consumed)` before the seal is visible;
  recovery refuses logged actionIds.
- H1: durable `(capabilityId → reserved)` before spending; recovery
  assumes reserved = spent.

In both cases the safe direction of the crash race is chosen
structurally (refuse / count-as-spent), and the availability cost
(denied legitimate retry / bounded underspend) is accepted explicitly.

## 5. What stays unresolved (honest)

1. **Anchor-file trust boundary.** `AppendOnlyFileAnchor` is honest
   about it: durable across restarts, tamper-evident via chaining, but
   not resistant to a host adversary with write access. The durable
   seal log (§2.4) inherits the same boundary. Host-adversary
   resistance needs a write-once store or timestamping authority
   behind the port — specified as a deployment substitution, not
   built.
2. **Conservative recovery's availability cost.** Intent logged but
   commit crashed → the actionId is dead; the principal starts over
   with a new ceremony. For epoch reservations → bounded underspend
   per crash. Both are priced and accepted; neither is silent.
3. **Embedder serialization (§3.2).** Every direct embedder must
   serialize `execute()` equivalently to the sidecar's `executeLock`,
   or the usage check TOCTOUs. This is a constraint on code that
   doesn't exist yet (Android dispatcher, Rust core) — it must be a
   review gate on those builds.

## 6. Build constraints (summary)

1. Durable seal log consulted at Gate 7 (C-3 fix); intent before
   commit; conservative recovery.
2. Reservation-pattern usage accounting (H1 fix); `durableUsage >=
   actualCommits` as the demonstrated invariant.
3. Single-lock (or single-thread) commit boundary per embedder.
4. Mediation before crypto (H2); keys last (H3) — unchanged.
5. Permanent negative controls extended: post-crash replay of a sealed
   actionId → refused; overspend past `maxMutations` across a crash →
   impossible (test kills the process mid-stream).
