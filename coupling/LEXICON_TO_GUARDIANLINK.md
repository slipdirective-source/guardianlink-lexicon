# Lexicon → GuardianLink: field mapping

Each `LexiconOutput` element (§16) and the GuardianLink component that produces or consumes it. This is the coupling contract: neither layer may silently reinterpret a field.

## decisionRecord → Merkle-anchored audit log

- The engine emits one `decisionRecord` per executed action (§17.1 proof obligation: "every executed action receives a consequence record").
- `decisionId` anchors into the Merkle tree; the tree is the durable anchoring the Lexicon requires "where the deployment provides it."
- `speechAct` typing happens at Gate 7: the engine must know whether it is handling a Q, a Hyp, an Assert, or a Dir before evidence evaluation (§19 invariant 2). A Dir (action request) without a preceding typed chain is rejected.
- `regime` carries the R0 precommitment; `regimeDelta` (in `revision`) is mandatory on any post-result regime change (§4.1). The engine must refuse to overwrite an original result — it appends a RegimeDelta record instead.
- `discrimination` is four-valued. ∅ ("empty" in the schema) is recorded distinctly; the engine routes it to question revision, never to a default-deny/allow shortcut (§19 invariant 21).
- `unresolved` (U-classes) travels with the record; U_auth or U_integrity on a dependent action fails closed at the gate.

## admissibility → Gate 7 evaluation

- `Adm(I|goal,rho,Gamma,Auth,Prov,G_history)` is the gate's evaluation function; `CumAdm` (§16.1) is the canonical cumulative rule — the gate evaluates over trajectory history G_(0:t), scaffolding Sigma_(0:t), and option space Omega_(0:t), not the instantaneous state alone.
- `verdict: Fail` halts execution. No override except an explicit externally authorized override record with responsibility transfer (RED rule, §17.1).
- `HighConsequence(I)` requires `recoveryPath` to be demonstrated or qualified; untested recovery counts as degraded (§8.1).

## safetyState → engine mode

See `safety-state-mapping.md`. The safety state binds the engine's response (§19 invariant 13: safety triggers bind responses — the mapping is not advisory).

## authorizationRequirement → assent + capability tokens

- `authState` maps onto the engine's assent lifecycle. Assent older than the idle-max-age rule (24h age + 24h ledger silence) is treated as expired.
- `consent` tuple dimensions gate which actions assent can license: assent is licensed only for the dimensions and horizon actually established (§11).
- `proxyProvenance` is required wherever the engine acts on non-direct authority; the least-agency-reducing intervention consistent with the authorized duty is preferred.

## recovery → RecPath execution

- The engine's recovery routines must satisfy the RecPath tuple: trigger, authority, resources, dependencies, data, skills, time, test, rollback, reconstruction.
- Recovery that depends solely on the failed component is invalid (§8.1 step 2) — the engine's recovery path must be executable from outside the failed subsystem.

## revision → model update with provenance

- Every model update preserves provenance of the superseded state (§17.1); `revision.supersedes` links the chain.
- Framework-level revisions that change engine behavior arrive as RegimeDeltas with independent justification — the recursion strengthens only if revisions can break the engine, never merely describe it.

## Trust separation (§15)

ProposalAuthority ≠ EvidenceAuthority ≠ AuthorizationAuthority ≠ ExecutionAuthority ≠ AuditAuthority. In the coupled system: the Lexicon layer proposes and types; the engine executes; the audit log attests. Self-reported evidence cannot satisfy a hard gate whose failure benefits the reporter unless separately attested — the engine must not grade its own homework on gates where it is the interested party.

## One-way ratcheting (coupling invariant)

Lexicon outputs — safety states, trigger firings, U-class blocks — can only **tighten** what the PolicyEngine does. They can never loosen a rail, grant authority, or mint a permission. This is the coupling's top invariant: it keeps the governance layer from becoming a back door to authority creep (the capture vector §12 exists to prevent).

**Refinement — the ratchet applies to authority, not to state estimates.** Safety states may relax (RED → YELLOW → GREEN) when reassessment under fresh evidence warrants it; that is estimate updating, not authority granting, and forbidding it would ratchet every escalation into permanence (itself a failure mode). What never flows upward from the Lexicon layer: new permissions, widened scopes, loosened hard constraints, or synthesized consent. This mirrors the engine's evidence-only trust model: the engine never takes a claim of permission at face value — permission must arrive as a rail with provenance.

## Constraint-provenance seam (§10 / §11)

Hard constraints and AuthState transitions must originate from a rail created by the user or a legitimate institution, carrying provenance. The Lexicon may evaluate constraints, escalate non-dominated conflicts to the authorized human/policy process, and enforce — but if a constraint's provenance chain terminates in Lexicon inference rather than an authorizing principal, the constraint is void and the dependent action fails closed. This is where facts stop and authority starts: the normative-smuggling guardrail (§22) made structural.
