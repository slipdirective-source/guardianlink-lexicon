# Android capability boundary — scoping (not implementation)

**Status:** SCOPED 2026-10-18. No keys implemented. This document locates
the lowest mutation primitives, answers the first red-team question, and
defines where a capability verifier must live for the invariant to hold.

## Target invariant

No governed mutation can commit unless the exact mutation is accompanied
by a currently valid capability derived from independently admitted
authority.

Formally: `Commit(m)` requires `C` where `C` binds `H(m)` (the exact
mutation), is live (`now ∈ [notBefore, notAfter]` on the engine clock),
is scoped (`scope(C)` covers `target(m)`), and is issued by admitted
authority (`verifySig(C, K_issuer)`). Validity is conjunctive; any
conjunct failing refuses the commit.

The inversion holds: time never grants power. Expiry kills capabilities;
broader scope comes only through renewed issuance.

## Lowest mutation primitives (Android)

| # | Primitive | What mutates | Current guard |
|---|-----------|--------------|---------------|
| P1 | `ConciergeInterface.substrate` (private var) | Governed logical state | Assigned only from `Integrated` outcomes in `execute()` |
| P2 | `EgressPlane.send(packet)` | Physical network effect | Called only on `Executed` — by convention |
| P3 | `TemplateStore.save(template)` | Enrolled voiceprint (security parameter) | Via `GuardianApp.setEnrolledTemplate()` — public |
| P4 | Anchor/clock files in app sandbox | Durability | Ambient authority (documented residual, out of scope) |

## All routes to the primitives

**To P1 (governed substrate):**
- R1: `ActionDispatcher.submit()` → `concierge.execute()` — intended sole-writer path.
- R2: `ActionDispatcher.submitTunPacket()` → `submit()` — intended.
- R3: Reflection on `ActionDispatcher`'s private `concierge` field → `concierge.execute()` directly. **Bypasses any dispatcher-level check.**
- R4: Concierge reference leak — currently contained (local to `initEngine()`), but one refactor away from exposure.

**To P2 (egress):**
- R5: `GuardianVpnService.packetLoop()` → `app.egress.send()` on `Executed` — intended.
- R6: **Direct `app.egress.send()`** — `egress` is a public `lateinit var` on `GuardianApp`. Any in-app code calls it. **Bypasses all governance.**

**To P3 (voice template):**
- R7: `VoiceEnrollmentActivity` → `setEnrolledTemplate()` — intended ceremony.
- R8: **Direct `app.setEnrolledTemplate(forged)`** — public method. **Bypasses governance for a security parameter.**

## First red-team question: YES

Can code inside the application reach the underlying state mutation while
completely bypassing the capability verifier? **Yes** — if the verifier
lives only in `ActionDispatcher.submit()`, routes R3, R6, and R8 bypass
it entirely. That is the real Android sole-writer defect: "sole writer"
is currently a convention (one class), not an enforced property.

**Consequence for placement:** the capability verifier must live at the
lowest commit primitive, not at the dispatcher:
- **P1:** verify inside `ConciergeInterface.execute()` (or NineGates at
  seal) — then R1–R4 all pass through it; reflection cannot bypass
  because the check is at the commit point.
- **P2:** gate `EgressPlane.send()` on the capability (or bind egress to
  the `Executed` receipt, which carries the capability reference).
  Additionally, `egress` must not be publicly settable/callable.
- **P3:** enrollment must be a governed action (through the dispatcher
  with a capability), not a public setter.

Only when every route is conditional on verification does the key have
somewhere meaningful to stand.

## Trust boundary (Keystore)

Android Keystore — hardware-backed via KeyMint where the device provides
it — is the candidate boundary for the capability **issuer keys**.
Hardware attestation can establish key properties (TEE/StrongBox
backing); attestation nonces give freshness against replay.

Explicitly NOT claimed: Keystore does not prove sole-writership. It
protects and access-controls the keys; the governed state sink still has
to enforce that a valid capability is mandatory. Key custody and
commit-point enforcement are separate properties, tested separately.

## Orthogonality

- **C-3 (durable execution uniqueness)** stays orthogonal. The capability
  answers "is this mutation authorized right now"; durability answers
  "did this authorization already commit across a crash." A future
  failure must discriminate between them.
- **Voice liveness, revocation, clock** unchanged.

## Not yet built (requires approval)

- Capability types, issuer, verifier — no keys implemented.
- Commit-point enforcement in `ConciergeInterface.execute()`.
- Egress gating and template-enrollment governance.
- The attack battery: altered mutation, expired/replayed/A→B
  capabilities, stale-after-context-change, process death/restart,
  cross-device copy, lower-layer direct invocation, compromised
  dispatcher input.

## Open design questions for the build phase

1. Should the capability ride inside `ActionEvidence` (engine-visible)
   or stay at the dispatcher layer with the check at the commit point?
2. Epoch capabilities (K_{S,C,t}) vs per-mutation capabilities for the
   packet path — per-packet ceremony is infeasible at line rate; the
   TUN path needs an epoch capability with tight scope ("net/*") and
   short TTL. This is where "autonomy ratchets up while authority
   decays" becomes concrete.
3. Issuer placement: ceremony-bound issuer in the Android app, key in
   Keystore; public key to the verifier at engine init.
