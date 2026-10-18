# Objective coverage audit

The nasty test, run backward: every mechanism in the stack must be explainable
in terms of the objective (Lexicon §0.1) — it either increases a maximand
(useful competence, legitimate delegated agency, consequential leverage) or
protects a hard constraint (human sovereignty, revocability, bounded authority,
corrigibility, auditability, recoverability). Anything unaccounted for is
flagged, not grandfathered.

Conducted 2026-10-18. Verdict: **everything accounts for itself.** That is
itself evidence the objective was generating the architecture before it was
stated — the constraint left very little room, and the mechanisms are what fit.

## Maximands

| Mechanism | Serves |
|---|---|
| GuardianLink engine (gates, assent, policy evaluation) | Useful competence: the thing that acts well |
| Lexicon discrimination machinery (four-valued Δ, D_rho, ResidualRefine) | Useful competence: better distinctions = more competent governance |
| Speech-act / epistemic typing (§3) | Useful competence: precise claims, no promotion without warrant |
| AuthorityRecord, assent & capability tokens, AuthState machine, consent tuples | Legitimate delegated agency: the apparatus that *enables* delegation — agency is maximized *through* legitimacy, not around it |
| CumAdm cumulative evaluation | Consequential leverage: agents can safely compose actions, so each action can reach further |
| Routine-regime templates, declared PARAMETRIC defaults | Consequential leverage: safe actions flow without ceremony; friction only where consequence warrants it |
| Threshold battery (A5a/A5b/A5c) | Useful competence: the system knows exactly when to block and when not to |
| Prototype `lexicon_governor` | Useful competence: the contract is executable, not aspirational |

## Hard constraints

| Mechanism | Protects |
|---|---|
| Sov_A self-consistency; authorship non-transferable both ways (§9) | Human sovereignty: authorship cannot be delegated away or disowned |
| Capture detection vector (§12); trust separation (§15) | Human sovereignty: the governor must not capture the principal |
| Dual invariant; one-way ratchet; Lexicon cannot mint authority | Human sovereignty + bounded authority: governance can only narrow, never grant |
| AuthState Revoked; assent idle-max-age; authority revocation; record expiry/supersession | Revocability: every grant has an off-ramp |
| Rails, scope bounds, hard constraints (§10), action+history binding, single-use records | Bounded authority: authority has edges, and the edges are enforced |
| Revision with provenance; RegimeDelta; self-application test (§22); GOVERNANCE.md self-amendment | Corrigibility: the system (and its spec, and its process) can be corrected |
| Merkle-anchored log; decision records; provenance chains; attic/; provenance ledgers | Auditability: every consequential step leaves a checkable trail |
| RecPath; HighConsequence ⇒ demonstrated recovery; safety states with bound responses | Recoverability: failure has a way back, tested before it's needed |
| 99.99% principle (incompleteness as engine) | Corrigibility: a system that believed itself complete would stop correcting — and a complete model of the principal could substitute for them. The principle keeps the revision paths open by doctrine |
| T_unk decision-dominance (v1.4) | Bounded authority + useful competence: blocks exactly where uncertainty is decision-relevant — neither over-blocking (which destroys leverage) nor under-blocking (which surrenders control) |
| Objective razor (this document's parent rule) | Human sovereignty: the stack cannot accumulate machinery that serves neither leverage nor constraint — anti-bloat as a sovereignty protection |

## Notes

- The 99.99% principle is the most doctrine-flavored entry; its protection claim (corrigibility) is real but indirect. Flagged for honesty, not challenged: without it, "operational closure" drifts toward completeness claims, which would license unrevisable authority.
- No mechanism was found that serves neither term. The audit will be re-run whenever a mechanism is added; the razor gates proposals going forward.
