# Epoch capability specification

**Status:** SPEC 2026-10-18. No implementation. This document defines
exactly what an epoch capability means so that implementation is a
mechanical translation, not a second design pass.

## 1. Purpose

Per-packet human ceremony at TUN line rate is infeasible. The epoch
capability delegates a bounded operating envelope: "mutations of class
K, under constraints C, for the next epoch." It replaces per-mutation
admission with per-epoch admission + per-mutation predicate checks.

Non-goals: replacing NineGates for high-stakes actions (those keep full
ceremony); durable execution uniqueness (C-3, orthogonal); key custody
(Keystore, separate).

## 2. The predicate requirement (hard)

The epoch capability authorizes a **predicate**, not possession of a key.

- WRONG: `Commit(m) ⇐ Holds(k) ∧ Valid(k)` — the key degenerates into a
  temporary master key.
- RIGHT: `Commit(m) ⇐ Holds(k) ∧ Valid(k) ∧ P_k(m) ∧ WithinBounds(k, usage)`

The commit boundary evaluates `P_k` against the specific mutation `m`
every time. The key alone authorizes nothing. `usage` is the commit
boundary's per-capability counter (rate/volume bounds); it is not
caller-supplied.

## 3. Capability structure

```
EpochCapability {
  id:            String,          // unique; revocation handle
  epoch:         Long,            // monotonic per issuer
  predicate:     Predicate,       // signed; §4
  notBeforeMs:   Long,           // engine clock
  notAfterMs:    Long,           // engine clock; short (§5)
  issuerId:      String,
  issuedAtMs:    Long,
  stateRoot:     String?,         // optional substrate binding (§7)
  maxMutations:  Long?,           // optional; enforced via usage counter
  maxBytes:     Long?,           // optional; enforced via usage counter
  signature:     ByteArray,       // issuer Ed25519 over canonical encoding
}
```

Canonical encoding for signature: `domain("GL-EPOCH-CAP-v1") ||
len(id) || id || epoch_be64 || canonical(predicate) ||
notBefore_be64 || notAfter_be64 || len(issuerId) || issuerId ||
issuedAt_be64 || opt(stateRoot) || opt(maxMutations) || opt(maxBytes)`.
Length-framed throughout; no ambiguity.

## 4. Scope predicate language

A predicate is a conjunction. All fields are signed (part of the
capability); the commit boundary evaluates them against the presented
mutation. The language is deliberately small and decidable:

- `targetPrefix: String` — `target(m)` must start with this prefix.
  (`target` = recordId for Read/Write/Delete; the flattened step
  targets for Sequence; both branches' targets for Guarded.)
- `allowedTypes: Set{Read, Write, Delete}` — mutation type must be a
  member. (Sequence/Guarded are decomposed; their steps must each
  satisfy the predicate.)
- `maxMutations: Long?` — at most this many commits under this
  capability (usage counter at the commit boundary).
- `maxBytes: Long?` — at most this many payload bytes under this
  capability (usage counter).

No field constraints in v1 (deferred; the predicate language versions
with the domain tag). A predicate that cannot be evaluated against a
mutation fails closed.

Example (TUN): `{targetPrefix: "net/", allowedTypes: {Write},
maxMutations: 60000, maxBytes: 96_000_000}` — roughly line-rate for a
5-minute epoch, then it dies.

## 5. Lifetime

Short. The TTL is a deployment parameter per scope class; the TUN epoch
suggested default is 5 minutes (matching the existing challenge TTL
horizon). `notAfterMs - notBeforeMs` is bounded by a rail
(`maxEpochTtlMs`); the issuer cannot mint longer-lived capabilities than
the rail allows, and the commit boundary enforces the rail independently
of the issuer's claim.

Renewal is a new issuance event. The agent may request renewal; it
cannot grant it. Holding `K_n` confers zero authority toward `K_{n+1}`
— the issuer key is never available to the writer, and there is no
"renew" operation that takes the old capability as input. Renewal
policy (e.g., auto-renew on clean reliability history) is governance,
not cryptography.

## 6. Revocation semantics

- By `id`: the commit boundary holds a revocation set (populated via
  the revocation feed). Checked at commit time, like the seal-time
  rescan — a revocation that lands mid-evaluation still kills the
  commit.
- By `epoch`: revoking an epoch number kills every capability from that
  epoch (coarse, fast).
- By issuer key rotation: kills everything from the old key (nuclear).
- Short TTLs bound worst-case revocation latency: the maximum window
  of a compromised-but-unrevoked capability is `notAfterMs - now`.

## 7. State binding

`stateRoot` (optional): the Merkle root of the governed substrate at
issuance. If present, the commit boundary requires the current
substrate's lineage to include the bound root — i.e., the substrate has
not been reset or rolled back since issuance.

This closes a concrete hole: after a process crash, the in-memory
substrate is gone; a replayed epoch capability against the fresh
substrate is refused when state-bound, because the lineage was broken.
(For the TUN path, where packets are stateless, state binding is
optional; for stateful scopes it is recommended.)

## 8. Replay semantics

Within a live epoch, the same `(mutation, capability)` presented twice:

- The predicate passes both times (it authorizes a class). Uniqueness
  is a separate concern from authorization.
- The commit boundary maintains a per-capability mutation-hash set
  (SHA-256 of canonical rendering), bounded by `maxMutations`, decaying
  with the capability. An exact duplicate within the epoch is refused
  as `DUPLICATE`, not re-committed.
- Rationale for the TUN path: exact-duplicate packets are retransmit
  noise; dropping them at the governed boundary is safe (the network
  stack above handles reliability). The bound keeps memory proportional
  to the epoch, not to history.

Cross-epoch replay is impossible: the capability is dead, and the hash
set died with it.

## 9. Expiry semantics

- Validity is checked at **commit time** (seal), not at presentation.
  If `notAfterMs` passes mid-evaluation, the commit fails closed.
  (Same pattern as the revocation rescan.)
- Already-sealed mutations stay sealed. Expiry does not uncommit.
- Effects after commit: if the physical effect (egress send) has not
  yet realized when the capability expires, the effect is dropped and
  logged. The capability authorizes the mutation *and* its realization;
  a dead capability realizes nothing. (Fail-closed direction: drop, not
  send.)

## 10. Commit-boundary enforcement

Location: `ConciergeInterface.execute()` (or NineGates at seal) — the
lowest commit primitive identified in the scoping doc. Every route to
mutation (dispatcher, reflection, direct concierge access) passes
through it.

Verification order (fail fast, fail closed):
1. Capability present (if the deployment mandates capabilities).
2. Signature valid against the admitted issuer key.
3. `notBeforeMs <= now <= notAfterMs` (engine clock).
4. Not revoked (by id, epoch, or key).
5. `P_k(m)` holds (predicate evaluation per mutation).
6. Usage bounds (`maxMutations`, `maxBytes`) not exceeded.
7. State binding holds (if bound).
8. Not a duplicate within the epoch.
9. → proceed to NineGates evaluation (the capability does not replace
   the gates; it gates *access to* the gates for the delegated class).

A capability never weakens NineGates. It is an additional outer bound,
not an inner bypass.

## 11. Permanent negative controls (build phase requirement)

These bypasses become permanent CI controls; they must fail forever:
- Reflection → `concierge.execute()` without capability → refused.
- Direct `egress.send()` without capability → refused (or unreachable).
- Direct `setEnrolledTemplate()` outside governance → refused.
- Valid capability + altered mutation → refused (predicate mismatch).
- Expired capability → refused.
- Cross-capability use (A's capability for B's mutation) → refused.

If a future refactor resurrects any bypass, CI demonstrates that the
sole-writer property has disappeared. The tests are not deleted when
the bypasses are fixed; they are the property.

## 12. Open questions (build phase)

1. Exact TTL per scope class (TUN suggested 5 min; settings longer?).
2. `ActionEvidence` carries the capability (engine-visible) vs.
   dispatcher-layer handoff with commit-point check — interface shape.
3. Issuer implementation: ceremony-bound, Keystore-held key, public key
   to the verifier at engine init. Attestation freshness via nonce.
4. Predicate language v2 (field constraints?) — only if v1 proves
   insufficient; do not pre-build.
5. Usage-counter durability across crash: currently in-memory (dies
   with the epoch's process). Acceptable because the capability's
   state binding (§7) refuses post-crash reuse against fresh state —
   but specify the interaction explicitly in implementation.
