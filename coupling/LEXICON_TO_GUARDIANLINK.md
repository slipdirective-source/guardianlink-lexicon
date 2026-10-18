# Lexicon → GuardianLink: field mapping

Each `LexiconOutput` element (§16) and the GuardianLink component that produces or consumes it. This is the coupling contract: neither layer may silently reinterpret a field.

## Dual invariant (layer separation)

**The Lexicon cannot execute. GuardianLink cannot independently manufacture epistemic warrant.** The Lexicon judges consequential admissibility; GuardianLink governs execution. Lexicon output can only narrow existing legitimate authority, never expand it. Every consequential action must (a) remain authorized under an externally sourced AuthorityRecord, (b) pass current cumulative admissibility (CumAdm) against actual trajectory history, (c) pass GuardianLink's own gates independently, and (d) return its sealed consequence record to the Lexicon as Yield — evidence for the next evaluation, never proof the reasoning was correct.

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

## AuthorityRecord vs GovernanceConstraintRecord

Two records, never merged:

- **AuthorityRecord** — externally sourced. Who granted what, under which rail, with provenance terminating in the authorizing principal (user or legitimate institution). Lives in `authorizationRequirement.authorityRecord`. The Lexicon reads it; nothing in the Lexicon writes it.
- **GovernanceConstraintRecord** — what the Lexicon evaluated: constraint id, the source rail it derives from, the Adm/CumAdm evaluation reference. Lives at top level. If a constraint's provenance chain terminates in Lexicon inference rather than an authorizing principal, the constraint is void.

## Action binding (replay protection)

Every LexiconOutput is bound to one exact canonical GuardianLink action (`actionBinding.canonicalActionId`) and one sealed history/state commitment (`actionBinding.historyCommitment`, e.g. the Merkle root at evaluation time). A constraint record presented against a different action, or against evolved history, is action-mismatched / history-mismatched and fails closed. Governance state that is missing, malformed, expired, superseded, consumed, unverifiable, action-mismatched, or history-mismatched fails closed — enumerated in `governanceStateCheck`, no silent pass. Records are single-use: one evaluation authorizes exactly one execution, so an identical repeat action needs a fresh evaluation.

## Depends(Action, U) — necessary information, not the discriminator

`unresolvedDependencies` records the relation as *information*: whether the action materially depends on resolving each U-class. It is **not** the blocking discriminator. The discriminator is counterfactual sensitivity — the (proposed) v1.4 `T_unk` criterion: a U blocks iff at least one *admissible* resolution of it changes the admissibility outcome. A5b is the demonstration of why: dependency alone is too coarse, because a material-but-outcome-invariant U must not block. U_auth on the payment step of a purchase: material, blocks. U_scale on an unrelated background parameter: recorded, does not block. This is the formal counterpart of the battery's "decision-dominant" threshold — the relation decides *whether* a U can block; the threshold decides *when* a material U is dominant. Both are needed; neither alone is sufficient.

## CumAdm as the cumulative rule

CumAdm (§16.1) is the single canonical cumulative-action rule for sequential interventions: individually admissible actions can compose into an inadmissible trajectory, so the gate evaluates over G_(0:t), Sigma_(0:t), Omega_(0:t) — never the instantaneous state alone. (Note: the engine's previously documented residuals do not list a cumulative-reasoning gap; this is adopted as a new hardening requirement on the coupling, not a cited defect.)

### Prior art: path-dependent governance (Kaptein et al., 2026)

Path-dependent admissibility is **not claimed as novel**. Kaptein, Khan & Podstavnychy, *Runtime Governance for AI Agents: Policies on Paths* (arXiv:2603.16586, March 2026), make the execution path the central object of runtime governance and formalize compliance policies as deterministic functions mapping **agent identity, partial path, proposed next action, and organizational state** to a policy violation probability — the same structural idea as CumAdm's evaluation over trajectory history rather than instantaneous state. (Abstract verified via arXiv 2026-10-18; full-text comparison against their AI-Act-inspired example policies is in progress.)

Where this stack differs is what sits **around and under** the path-dependent evaluation:

1. **Typed non-numeric uncertainty instead of violation probabilities.** Their policy function outputs a violation probability, and they list *risk calibration* as an open problem. The Lexicon's P_unknown rule answers it directly: never fabricate a number — where the probability is ungrounded, raise the safety state instead, and type the uncertainty (U-classes) with a resolution path rather than pricing it. A probability threshold smuggles ungrounded precision into the decision; a typed U block keeps the ignorance visible and actionable.
2. **Authority separation.** Proposal, evidence, authorization, execution, and audit are distinct loci with distinct provenance requirements (the dual invariant at the top of this document). Their abstract's framework does not separate these — which is where capture enters: whoever manufactures the warrant also disposes of it.
3. **Provenance-as-warrant.** Nothing in the Lexicon authorizes; authority records are externally sourced and provenance must terminate in the authorizing principal. Path-dependent evaluation without provenance discipline evaluates the path but not the *standing* of the actor walking it.

Novelty claim, stated plainly: **typed non-numeric uncertainty plus authority separation, layered over path-dependent evaluation.** The path-dependence itself is prior art and cited as such.
