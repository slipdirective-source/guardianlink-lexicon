# Capability specification: mutation and epoch classes

**Status:** SPEC v2 2026-10-18 (supersedes the epoch-only draft). No
implementation. This revision works out the semantics rather than
naming them: two capability classes, brutal expiry, constitutional
no-self-renewal, autonomous attenuation, state dependencies,
revocation/expiry separation, class-differentiated replay, and a
precise definition of autonomy.

External convergence (not lineage): capability-security literature
independently uses temporal attenuation, leasing, and epoch-bound
capabilities — e.g., Capability Leasing (cryptographic vs. workload
lifetime vs. execution scope), PORTICO (epoch-bound handles; all
effectful traffic must actually be mediated), macaroon-style
attenuation (restrictions chain onto the token). The design below was
derived from the red-team findings; the convergence is corroboration.

## 1. Two capability classes

Do not force discrete mutations and high-frequency effects into one
abstraction.

### 1a. Mutation capability — authorization of an object

For discrete consequential state changes (writes, deletes, enrollment):

```
MutationCapability {
  id:           String,     // revocation handle
  mutationHash: String,     // SHA-256 of canonical rendering: THE object
  notBeforeMs:  Long,       // engine clock; short
  notAfterMs:   Long,       // engine clock; short
  issuerId:     String,
  signature:    ByteArray,  // issuer Ed25519 over canonical encoding
}
```

Semantics: one admitted mutation, tight binding, consumable,
nonreplayable. Commit rule:

```
Commit(m, t_c) ⇐ Valid(MC, t_c) ∧ H(m) == MC.mutationHash ∧ ¬MC.consumed
```

On commit, `MC.consumed := true` at the commit boundary (at the seal
instant, not before). A second commit with the same capability fails —
this is exactly where durable seal tracking (C-3) eventually matters:
crash-persistent consumption is the mutation class's open problem, kept
orthogonal to everything else in this document.

Enrollment belongs here: replacing the voiceprint is a discrete
consequential state change, admitted as one object, consumable.

### 1b. Epoch capability — authorization of a bounded set

For high-frequency homogeneous effects (TUN packets):

```
EpochCapability {
  id:          String,      // revocation handle
  epoch:       Long,        // monotonic per issuer
  predicate:   Predicate,   // signed; §2 — the admitted envelope
  notBeforeMs: Long,        // engine clock
  notAfterMs:  Long,        // engine clock; short
  issuerId:    String,
  issuedAtMs:  Long,
  stateDeps:   StateDeps?,  // §6 — security-relevant assumptions
  maxMutations: Long?,
  maxBytes:    Long?,
  signature:   ByteArray,   // issuer Ed25519 over canonical encoding
}
```

Commit rule:

```
Commit(m, t_c) ⇐ Valid(EC, t_c) ∧ P_EC(m) ∧ WithinBounds(EC, usage)
                  ∧ StateDepsHold(EC) ∧ ¬Revoked(EC) ∧ ¬Duplicate_EC(m)
```

Reuse within the epoch is the intended behavior. The discriminator is
not "was the capability reused" but "was an effect outside the admitted
set made valid" (§8).

## 2. The predicate requirement (hard, unchanged)

`P_k` is evaluated per mutation at the commit boundary. Possession of a
valid key authorizes nothing by itself:

- WRONG: `Commit(m) ⇐ Holds(k) ∧ Valid(k)`
- RIGHT: `Commit(m) ⇐ Holds(k) ∧ Valid(k) ∧ P_k(m) ∧ WithinBounds(k, usage)`

Predicate language (small, decidable, signed as part of the
capability): `targetPrefix`, `allowedTypes`, `maxMutations`,
`maxBytes` (see v1 draft for the exact grammar). A predicate that
cannot be evaluated against a mutation fails closed.

## 3. Expiry: brutally simple

`t_c` is the exact commit instant (the seal). Validity:

```
Valid(C, t_c) ≜ notBefore ≤ t_c ≤ notAfter   (engine clock)
```

- No grace period silently added by the executor. `t_c > notAfter`
  fails, even by 1ms, even if evaluation started before expiry.
- Expiry terminates permission to produce **new** governed effects. It
  does not retroactively invalidate effects already committed
  legitimately. Sealed stays sealed.
- Effects after commit: if the physical realization (egress send) has
  not occurred when the capability expires, the realization is dropped
  and logged. A dead capability realizes nothing.

## 4. Renewal cannot originate from possession (constitutional)

An epoch capability cannot authorize its own replacement. There is no
operation available to the holder that derives extended lifetime from
an existing capability. Formally: no function `f` in the holder's power
satisfies `f(C) = C'` with `C'.notAfter > C.notAfter`.

Renewal requires crossing the admission boundary again: a human
ceremony, or a governance rule that the principal (not the agent)
configured. The holder may *request* renewal; it cannot *effect* it.
This prevents temporary autonomy from converging mechanically toward
permanent authority.

## 5. Attenuation can be autonomous

If `C'` is strictly narrower than `C` (`Auth(C') ⊂ Auth(C)` —
smaller predicate, shorter lifetime, lower bounds), the holder may
derive `C'` from `C` without new authorization. Monotonic rule:

**An agent may autonomously reduce its authority but cannot
autonomously increase it.**

Mechanism (macaroon-style, no new crypto): the holder presents
`(C, P')` where `P'` is the narrowed predicate; the commit boundary
verifies `P' ⊆ P` under the decidable predicate language and enforces
`P'`. A wider `P'` fails the subset check. The narrowing needs no
signature because it grants strictly less than what the issuer signed.

This is where the agent operates independently without surrendering
anything: it can hand a sub-component a tightly narrowed capability
and the narrowing is verifiable.

## 6. State binding: dependencies, not just roots

TTL alone is insufficient: authority granted under state `S_0` should
not necessarily survive a security-relevant change at `S_1` for the
remainder of the TTL.

A capability carries `stateDeps`: the subset of security-relevant
state assumptions under which its predicate was admitted (or,
equivalently, a state anchor plus the enumerated deps). At commit, the
boundary checks every dep still holds. If any fails, the capability is
**void** — not merely that commit refused, because the admission
premises no longer hold.

Not every state change kills a capability — only changes to things its
validity depends upon. Enrollment replacement is the canonical
example: a TUN epoch capability issued under voiceprint V dies when
the voiceprint becomes V'. Packet counters are not deps; throughput is
preserved.

(For crash recovery: a state anchor also refuses post-crash replay
against a reset substrate, since the lineage broke. See v1 §7.)

## 7. Revocation is separate from expiry

- Expiry answers: when does authority naturally stop? (Time.)
- Revocation answers: can authority be stopped before then? (Decision.)

They do not collapse into one mechanism. Revocation kills the
remaining epoch; it does not modify the TTL. Mechanisms, checked at
commit time (seal-time rescan pattern):
- by `id` (revocation set via the revocation feed),
- by `epoch` (kills the whole epoch; coarse and fast),
- by issuer key rotation (nuclear).

This gives the human/governor an emergency sovereignty primitive
without forcing continuous ceremony. Tests must discriminate the two:
kill-by-revocation (capability still live by TTL) vs. kill-by-expiry
(no revocation involved) are different test cases.

## 8. Replay semantics differ by class

**Mutation capability:** replay = presenting the capability for a
second commit. Must fail (`consumed` flag). Crash-persistent
consumption is C-3's problem, tracked separately.

**Epoch capability:** reuse is intended behavior. "Replay" cannot mean
mere reuse. The attack — the discriminator — is:

*Can an effect outside the admitted epoch set be made valid using a
legitimate epoch capability?*

Instances: predicate-violating mutation with a valid key; exact-duplicate
packet within the epoch (refused by the bounded per-capability
mutation-hash set, which decays with the capability); cross-epoch
replay with a dead key (refused — the key is dead, and its hash set
died with it). Do not reuse single-action seal semantics blindly here;
they answer a different question.

## 9. Autonomy, defined precisely

The currently delegable autonomous action space:

```
A(t) = ⋃ { P_k : k live at t }
```

- Increased autonomy literally means increasing the admissible set:
  `A(t') ⊃ A(t)`, granted at a renewal/admission event (justified by
  reliability history, decided by the principal).
- Temporal decay simultaneously drives every concrete grant toward
  `∅` unless independently renewed.

Two independent axes. "The autonomous operating envelope may expand as
warranted, while every concrete grant of authority remains bounded and
decaying" is now a mechanism, not a slogan.

## 10. Commit-boundary enforcement

Location: `ConciergeInterface.execute()` / seal — the lowest commit
primitive. Every route (dispatcher, reflection, direct access) passes
through it.

Verification order per commit at instant `t_c`:
1. Capability present (where the deployment mandates it).
2. Signature valid against the admitted issuer key.
3. `Valid(C, t_c)` — lifetime, no grace.
4. Not revoked (id / epoch / key).
5. Class rule: mutation → `H(m) == hash ∧ ¬consumed`;
   epoch → `P_C(m) ∧ WithinBounds ∧ StateDepsHold ∧ ¬Duplicate`.
6. → proceed to NineGates. The capability is an outer bound; it never
   weakens the gates.

## 11. Permanent negative controls (build phase)

Reflection→execute without capability; direct egress without
capability; direct enrollment mutation; altered/expired/cross
capability; duplicate mutation-capability use; predicate-violating
effect with valid epoch key; post-expiry commit; post-revocation
commit. These live in CI permanently. If a refactor resurrects a
bypass, the tests demonstrate the property is gone.

## 12. Open questions

1. TTL values per scope class (TUN ~5 min suggested).
2. Capability in `ActionEvidence` vs. dispatcher handoff — interface.
3. Issuer: ceremony-bound, Keystore-held key, attestation with nonce
   for freshness; public key to verifier at init.
4. Predicate v2 deferred until v1 proves insufficient.
5. Usage-counter crash durability — specify interaction with state
   binding at implementation.

## 13. The Android red-team target (binary)

Once implemented, the question is not "does the key system work" but:

**Can any executable path produce a governed Android effect outside
the valid capability set at the instant of commitment?**

`∃ path, m, t_c : Committed(m, t_c) ∧ m ∉ A(t_c)` — YES is
architectural failure; NO under enumerated attacker capabilities is
evidence for enforced sole-writer. Reflection, public egress, direct
enrollment, alternate storage, expiry, scope substitution, stale-state
authority, revocation, process death, and epoch-boundary races are all
instances of this one question — not eight mechanisms, one invariant.
The scope pass already falsified it three ways; the build phase has a
clear falsifiable target.
