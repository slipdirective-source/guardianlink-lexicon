# Sole authority path: answering the open questions

**Status:** ADDENDUM 2026-10-18. The capability spec v2.1 stays frozen;
this document records a framing revision and answers the open
questions. Nothing here enlarges the architecture.

## 1. The reframing

"Sole writer" is the wrong ultimate property. It reasons structurally
— which code is permitted to write — and the reflection finding proved
it insufficient: a single writer that anyone can invoke unconstrained
proves very little.

The property actually under test is the **sole authority path**:

*No governed effect commits unless it crosses one irreducible
authorization relation — verified at the commit point, at the commit
instant — regardless of how many physical writers exist.*

Five writers could satisfy it; one writer can violate it. The
reference-monitor formulation is the established term: invoked for
every security-sensitive operation (complete mediation), resistant to
tampering, and constrained enough to analyze. Cornell's version is
the closest: the monitor evaluates a predicate over the requested
operation and current monitor state, and blocks when it isn't
satisfied. That sentence describes `P_k(m) ∧ Valid(C, t_c)` at
`ConciergeInterface.execute()`.

## 2. The diagnostic

Whenever a "new" control requirement appears, ask: is it a genuinely
new invariant, or an existing invariant that stops being enforced at
some lower layer? If the latter, don't enlarge the architecture — move
the enforcement boundary down until it coincides with the lowest
consequential operation.

The three Android findings were three witnesses for one fact:
incomplete mediation. The architecture already said every governed
mutation crosses the authorization relation; Android had
effect-producing primitives below the level where that rule was
enforced. The epoch-capability work is therefore not a new
governance layer. It is the mechanical realization of the existing
property, pushed down to consequence:

- the key → unforgeable representation of the authority,
- the predicate → what the authority means,
- the TTL → when it means it,
- the epoch → how long autonomous execution may proceed,
- the commit-point verifier → complete mediation,
- the durable lineage → whether the structure actually held, checkable
  afterward.

## 3. Answers

### Q1 — TTL values

Proposed defaults (tuning, but anchored, not arbitrary):

- Mutation capability: 5 min. It's single-use; the TTL is only a
  backstop covering clock skew and evaluation time.
- Epoch capability (TUN): 5 min, matching the existing
  `CHALLENGE_TTL_MS`. It bounds revocation latency and the
  stale-state window with the system's existing heartbeat.
- Rail `maxEpochTtlMs`: 1 hour. The issuer cannot mint longer; the
  verifier enforces the rail independently of the issuer's claim.

The number that matters more than the TTL is the renewal path: for
TUN, renewal cannot be a human ceremony every 5 minutes. Renewal
crosses the admission boundary via a **governance rule** the principal
configured (e.g., auto-renew on clean reliability history and no
security-relevant state change) — the standing-delegation pattern
from the prototype. The human sets the policy once; the policy
renews the epoch. This is legitimate delegation, not accumulated
surrender, and the diagnostic confirms it: renewal-as-delegation is
the existing admission invariant extended in time, not a new one.

### Q2 — Capability interface: `ActionEvidence` vs. dispatcher handoff

The capability travels in (or alongside) `ActionEvidence` to
`ConciergeInterface.execute()`, and `execute()` verifies it. The
dispatcher may *attach* it; only the commit boundary *checks* it.
Checking at the dispatcher would repeat the original mistake — the
dispatcher is bypassable, so it cannot be the enforcement point.

Performance: the signature is verified once per epoch and cached by
capability id at the boundary; per-effect checks run against the
cached entry (predicate, bounds, TTL, revocation, state deps). The
cache is invalidated on revocation and expiry. Per-packet cost is a
predicate evaluation and counter decrement — no crypto per packet.

This is the diagnostic applied directly: the check already belongs to
the commit relation; the interface question is just where the
representation rides.

### Q3 — Issuer

The issuer is the existing admission boundary with one new output:
minting a capability. Do not build a second ceremony. Gate 7's
ceremony already decides "this authority is admitted"; the issuer
encodes that decision as a delegated artifact instead of only a
single authorization.

Constraints (already in the spec, restated as the mechanical form):
- The issuer key is held where the agent cannot reach it (Android:
  Keystore, used only by the ceremony component).
- Attestation with nonce gives the verifier freshness: the key is
  hardware-backed *now*, not merely at provisioning.
- The verifier receives the issuer's public key at engine init.
- The agent can request issuance; it cannot perform it
  (constitutional no-self-renewal).

Per H3: the issuer mints the representation; it does not govern. The
commit boundary governs.

### Q4 — Predicate v2

Don't build it. The trigger for revisiting is a scope that v1 cannot
express **and** that represents a genuinely new invariant — run the
diagnostic first. Field-level constraints, if they ever come, are
probably the existing predicate at a finer grain, not a new concept.

### R1 — Anchor-file trust boundary

Tighten the port contract instead of enlarging the design:
`ExternalAnchor` must guarantee append-only, independently
timestamped, externally checkable records. The file anchor is the
dev-grade instantiation; production substitutes a write-once store or
timestamping authority (OpenTimestamps is the staged candidate)
behind the same port. The invariant — tamper-evident durable record —
already exists; this is instantiation strength, and it varies by
deployment without changing the architecture.

### R2 — Conservative recovery's availability cost

Bound it and give the embedder a way to reconcile:

- C-3: a dead actionId costs one new ceremony. Mitigation: a
  recovery-path query, `wasSealed(actionId)`, against the durable
  seal log, so the embedder distinguishes "committed but unacked"
  (reconcile, don't retry) from "never committed" (safe to retry with
  a new actionId).
- H1: underspend bounded by the reservation size `R`.

The cost is priced, bounded, and partially recoverable — not silent,
not unbounded.

### R3 — Embedder serialization

Move the lock inside the commit boundary. `execute()` (or the
capability verifier within it) serializes check-and-act internally;
then no embedder can get it wrong, and the sidecar's `executeLock`
becomes defense-in-depth rather than the enforcement. The diagnostic
again: the atomicity invariant already exists — enforce it where it
can't be bypassed instead of constraining every future embedder by
code review.

## 4. Relation to the frozen spec

v2.1 is unchanged. This addendum interprets it: wherever the spec
says "sole writer," read "sole authority path." The mechanisms —
predicate-not-possession, brutal expiry, no-self-renewal, autonomous
attenuation, state deps, revocation/expiry separation,
class-differentiated replay, atomic usage accounting,
mediation-before-crypto, key-is-not-governor — are the mechanical
form of the one invariant in §1. Implementation remains mechanical;
the remaining work is still concentrated in the answered questions
above, which are now decisions with defaults rather than open design.

## 5. Methodological observation (retained)

When a lower layer violates an established invariant, first move the
enforcement boundary down. Do not automatically create a new
architectural concept.

This is what happened with Android mediation, serialization,
capability issuance, crash recovery, exhaustion accounting, and
renewal. The architecture wasn't missing six ideas. Its existing
ideas hadn't reached consequence yet. The repeated transformation:

*assumption at a higher layer → enforced condition at the lowest
consequential layer.*

Apply it before inventing. If the moved boundary holds, no new
concept was needed. If reality refuses the moved boundary, *that* is
where a genuinely new invariant lives — and the refusal is the
evidence for it.
