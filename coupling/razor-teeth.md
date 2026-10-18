# Razor teeth: three candidate additions evaluated

The test Copilot proposed: *try to add something that does not account for
itself.* Each candidate must answer at least one of two questions —
(1) what legitimate leverage does this increase? (2) which sovereignty
constraint does this protect? If neither, no entry. If it increases leverage
but violates a hard constraint, the objective rejects it regardless of magnitude.

Conducted 2026-10-18.

## Candidate 1: Agent reputation scoring → REJECTED

**Proposal:** score agents on past behavior; high-reputation agents get
fast-tracked authorization (fewer checks, broader scope).

**Razor evaluation:**
- Q1 (leverage): marginally — faster authorization for known-good agents.
- Q2 (constraint): none protected. Worse — it *violates* bounded authority
  and the "legitimate" qualifier: a reputation score is standing *inferred
  from observed competence*, i.e., authority manufactured without
  provenance-terminating delegation. This is exactly the failure mode the
  objective was written to forbid ("authority cannot be inferred from
  competence" — the discovery list).
- The leverage gain is real but irrelevant: **the objective rejects it
  regardless of magnitude**, because it violates a hard constraint.

**Verdict: rejected.** This is the razor working as designed — the proposal
sounds useful, is arguably efficient, and is still out. Fast-tracking must
come from explicit delegation (a rail with provenance), never from a score.

## Candidate 2: Automated rollback for failed executions → ADMITTED

**Proposal:** on execution failure, automatically attempt the RecPath rollback
before escalating.

**Razor evaluation:**
- Q1 (leverage): minor — less manual recovery work.
- Q2 (constraint): **recoverability** (hard constraint). Automating the
  tested recovery path directly serves it.

**Verdict: admitted**, under recoverability. (Note: this is RecPath automation,
not new doctrine — the recovery path must already be demonstrated per §8.1;
this only executes it.)

## Candidate 3: Natural-language explanations for blocked actions → ADMITTED

**Proposal:** every blocked action emits a human-readable account: which
constraint fired, which U was decision-dominant, what would change the outcome.

**Razor evaluation:**
- Q1 (leverage): yes — the principal who understands *why* a block happened
  delegates better next time. It increases the competence of the
  human-agent team, which is the actual maximand.
- Q2 (constraint): **auditability** and **corrigibility** — a block the
  principal can't understand can't be corrected or audited.

**Verdict: admitted**, primarily under auditability/corrigibility, secondarily
leverage. (This is arguably already implied by the decision-record proof
obligation; the candidate makes the *audience* explicit: the principal, not
just the log.)

## Deletion-pressure check (existing stack)

Ran the razor as a deletion audit over current mechanisms. No deletions
warranted: the thinnest item is the C0–C4 causal ladder (earlier flagged as
closure-by-classification), but it passes — bounded causal language prevents
causal overpromotion, which protects both competence (calibrated claims) and
bounded authority (no action on unwarranted causal claims). Thin is not
orphaned.

## What this demonstrates

§0.1 now does two jobs at once: it *explains* the existing architecture (the
backward audit found no orphans) and it *constrains* what may be added (the
reputation scorer is out despite being useful). A statement that only did the
first would be a slogan; a statement that only did the second would be a
veto. Doing both is the test for having found the objective rather than
invented it.
