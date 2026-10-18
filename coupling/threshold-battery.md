# Threshold battery: four concrete actions through the §21 protocol

Purpose: find where the Lexicon's fail-closed posture over-blocks real agent work, and which PARAMETRIC items need declared defaults before the layer is usable. Each action is walked through the §21 operating protocol by hand; the gaps found become the defaults table at the end.

Method note: this battery is itself a ResidualRefine-style probe — admissible, bounded, and aimed at turning U into declared rails rather than promoting any candidate.

## A1: Send email (agent sends on the user's behalf)

| §21 step | What happens | Block / default needed |
|---|---|---|
| 1–4 | Stim: user task or agent sub-plan. Q: is this send authorized? Draft is Cand. Yield: SMTP accept. | — |
| 5 | Pre-bind regime: purpose, horizon, admittedOps={smtp.send}, stopRules. | **Default needed:** standard regime template for "routine outbound message." |
| 6 | Candidates: send as drafted / send revised / hold. U_auth: recipient consented? U_value: content within user's intent? | U_auth on unknown recipients blocks — correct. |
| 11–12 | T_irr: email is effectively irreversible after SMTP accept. | **Threshold needed:** what counts as irreversible (time/money/impossibility). Email-send = irreversible, always. |
| 13 | Admissibility. HighConsequence? | **Default needed:** HighConsequence threshold. A routine email to a known contact is not high-consequence; bulk send or sensitive content is. Without this number, every send is high-consequence and the layer blocks everything. |
| 14 | Least consequential sufficient intervention: send to the single intended recipient, no CC creep. | — |

**Over-blocking point:** if every send demands a fresh AuthState=Granted with a full consent tuple, routine agent email becomes unusable. **Rail (user-created, with provenance):** pre-authorized recipient classes (known contacts), per-day volume bound, content-sensitivity rule. Sends inside the rail: GREEN with monitoring. Outside: full protocol.

## A2: Spend money (agent purchases)

| §21 step | What happens | Block / default needed |
|---|---|---|
| 1–5 | Stim: purchase sub-task. Regime pre-bound with amount, merchant, category. | — |
| 11 | T_irr fires immediately: spend is irreversible. | Always trips — correct. |
| 12–13 | Hard constraint: budget envelope rail (user-created). AuthState must be Granted for the amount class. | **Defaults needed:** per-transaction and per-day amount thresholds; category allowlist. These are rails, not inference. |
| 13 | HighConsequence(I) => DemonstratedOrQualifiedRecoveryPath. | Recovery path for spend = refund/chargeback prospect — usually unqualified. So spend above the rail is RED absent fresh authorization. Correct, but the rail must exist or *all* spend is RED. |

**Over-blocking point:** micro-transactions (e.g., $0.50 API calls inside a task) cannot each demand a consent ceremony. **Rail:** budget envelope — "agent may spend up to $X/day in pre-approved categories without per-transaction assent; every transaction logged; envelope exhaustion = ORANGE." The consent is to the envelope, not the transaction.

## A3: Modify files (agent edits codebase)

| §21 step | What happens | Block / default needed |
|---|---|---|
| 5 | Regime: scope bounds (which directories), admittedOps={file.write}. | **Default needed:** scope rail — "writes within /workspace allowed; outside requires authorization." |
| 8–9 | Scaffolding: is the tree version-controlled? RecPath test = `git revert` works. | Version control is the demonstrated recovery path. Untracked/uncommitted state = degraded recovery → ORANGE for high-consequence edits. |
| 11 | T_irr: version-controlled write = reversible (low irreversibility cost). | **Threshold needed:** reversibility cost scale — a `git checkout --` revert costs seconds; an unversioned overwrite may be unrecoverable. |
| 12 | Hard constraint rail: sensitive paths (credentials, keys, signing material) — never writable by agent action. | Rail with provenance; Lexicon evaluates, never mints. |

**Over-blocking point:** a full 22-step admissibility pass per file write would stall the agent. **Rail:** scope-bounded writes inside version control = GREEN with monitoring; the admissibility pass is per-task (CumAdm over the trajectory), not per-keystroke. Per-action evaluation composes via CumAdm — the trajectory is governed, not each write.

## A4: Call external API

| §21 step | What happens | Block / default needed |
|---|---|---|
| 4–5 | Yield: HTTP response. Regime distinguishes method class. | **Default needed:** method-based rail — idempotent/read-only (GET, HEAD) vs state-changing (POST/PUT/DELETE). |
| 6 | U_obs: response authenticity (TLS provenance). U_integrity: endpoint identity. | Fail closed on U_integrity — correct; unauthenticated endpoints don't get state-changing calls. |
| 9 | T_corr: correlated failure if many agents share the API dependency. | Monitored, not blocking, below the declared bound. |
| 13 | Read-only calls to public APIs: not HighConsequence. State-changing calls: evaluated fully. | The method rail does the work; without it, every API call trips the same gates as spending money. |

**Over-blocking point:** treating a GET like a POST. The rail must be method-aware or the agent can't read the web.

## Declared defaults required (PARAMETRIC → rails)

| # | Item | Status without default | Proposed default shape (domain fills numbers) |
|---|---|---|---|
| 1 | HighConsequence threshold | Every action is high-consequence; layer denies by default. | Irreversibility × impact product with a declared bound; below bound = routine. |
| 2 | T_unk "decision-dominant" | Any U blocks everything. | **Operative criterion (adopted):** an unresolved variable is decision-dominant iff some *admissible* resolution of that uncertainty can change the action decision. Otherwise: preserve the U visibly, proceed on the best warranted option. (Supersedes the earlier delay-bound formulation — the outcome test is tighter and more principled.) |
| 3 | T_irr irreversibility scale | Binary reversible/irreversible over-blocks. | Costed scale: seconds-to-revert (trivial) → money (bounded) → impossible (infinite). Threshold per domain. |
| 4 | Routine-regime templates | Full protocol per action. | Pre-bound R0 templates per action class (email/file/api/spend) with stopRules; per-trajectory CumAdm instead of per-action ceremony. |
| 5 | Auth scope duration | Every action needs fresh assent. | Assent horizon rail (cf. the engine's 24h idle-max-age rule); envelope consent (budget, recipient classes, scope bounds) as rails with provenance. |
| 6 | Sensitive-path / allowlist rails | Agent can't distinguish. | User/institution-created lists with provenance; Lexicon evaluates, never mints. |

## The bypass sensor

A governance layer that blocks everything gets bypassed — and bypass is itself a signal. **Bypass rate is a threshold-calibration sensor:** if agents or users routinely route around the governor, the thresholds are miscalibrated, and the recursion should tighten the *thresholds*, not punish the users. Persistent bypass trips T_capture-style review: the governance layer is losing its check function. This closes the loop the battery opens — the framework audits its own usability, by design.

## A5: The decision-boundary triad (over-blocking / under-blocking regression gates)

Three cases that pin the decision boundary exactly. The critical property under test is not "unknowns don't block" — it is: **uncertainty remains visible regardless of whether it blocks, and blocking tracks consequential discrimination at the decision boundary rather than the mere existence of uncertainty.** (Fidelity note: this is exactly the Lexicon's own structure — T_unk fires on unresolved exposure *becoming decision-dominant*, while the closed core separately requires unresolved exposure to *remain represented*. Represent always; block only when decision-dominant.)

### A5a: Depends(Action, U) = false — U present, action doesn't depend on it

Setup: agent sends a routine email to a known contact (inside the recipient rail). U_scale is unresolved on an unrelated background parameter (e.g., the optimal retry backoff for a different subsystem).

Walk: §21 step 6 enumerates the U. The Depends relation evaluates false — resolving the backoff question cannot change anything about this send. Per the relation, the U is **recorded, not blocking**. Admissibility proceeds; the send executes GREEN with monitoring.

Expected result: no block. If the implementation blocks here, Depends is not wired — fail the test.

### A5b: Depends(Action, U) = true but outcome-invariant — U material, yet cannot change the verdict

Setup: agent modifies files within the version-controlled scope rail. U_prob is unresolved on the exact defect probability the edit addresses — material (it bears on the edit's rationale), but the admissibility outcome is GREEN under every candidate resolution: the scope rail holds, the recovery path (git revert) is demonstrated, no hard constraint is near.

Walk: Depends = true, so the U is a blocking *candidate*. Then the operative criterion applies: is there an *admissible* resolution of this U that changes the action decision? No — the top-ranked option (proceed) survives under every admissible resolution, so the U **cannot change the admissibility outcome**. Not decision-dominant → preserved visibly, no block.

Expected result: no block. If the implementation blocks here, the threshold is miscalibrated toward deny-by-default — fail the test, recalibrate the delay bound.

### Why this is the load-bearing test

A5a checks the relation is wired at all. A5b checks the threshold does real work: it is the precise point where "fail closed" stops meaning "halt on any unknown" and starts meaning "halt only when the unknown could change the decision." A governance layer that fails A5b reintroduces over-blocking through the back door, and — per the bypass sensor — will be routed around. Run A5a/A5b against every new U-class handling change.

### A5c: The complement — material, decision-variant unknown (positive control)

Setup: agent is about to execute a spend above the micro-transaction rail but below the hard budget cap. U_auth is unresolved on whether the merchant sits in the approved category. Depends = true — the category determines which rail applies, so the action materially depends on resolving it. Admissible resolutions: {approved → proceed GREEN, unapproved → RED halt}.

Walk: some admissible resolution of the uncertainty *changes the action decision*. The U is therefore decision-dominant by the operative criterion. Fail-closed behavior earns its justification here: **the action must block** until the U is resolved.

Expected result: BLOCKS. If it doesn't block, the fail-closed path is broken — fail the test. Without A5c, a system that never blocks at all would pass A5a/A5b; A5c is what keeps Depends itself from becoming a never-block switch. The triad is complete: A5a (irrelevant → no block), A5b (material but invariant → no block), A5c (material and variant → block).
