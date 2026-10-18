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
| 2 | T_unk "decision-dominant" | Any U blocks everything. | U is decision-dominant when it blocks the top-ranked admissible option AND the cost of delay exceeds the declared delay bound. Otherwise: log U, proceed on the best warranted option. |
| 3 | T_irr irreversibility scale | Binary reversible/irreversible over-blocks. | Costed scale: seconds-to-revert (trivial) → money (bounded) → impossible (infinite). Threshold per domain. |
| 4 | Routine-regime templates | Full protocol per action. | Pre-bound R0 templates per action class (email/file/api/spend) with stopRules; per-trajectory CumAdm instead of per-action ceremony. |
| 5 | Auth scope duration | Every action needs fresh assent. | Assent horizon rail (cf. the engine's 24h idle-max-age rule); envelope consent (budget, recipient classes, scope bounds) as rails with provenance. |
| 6 | Sensitive-path / allowlist rails | Agent can't distinguish. | User/institution-created lists with provenance; Lexicon evaluates, never mints. |

## The bypass sensor

A governance layer that blocks everything gets bypassed — and bypass is itself a signal. **Bypass rate is a threshold-calibration sensor:** if agents or users routinely route around the governor, the thresholds are miscalibrated, and the recursion should tighten the *thresholds*, not punish the users. Persistent bypass trips T_capture-style review: the governance layer is losing its check function. This closes the loop the battery opens — the framework audits its own usability, by design.
