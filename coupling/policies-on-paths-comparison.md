# Policies on Paths vs the Lexicon: the comparison case

**Source (verified):** Kaptein, Khan & Podstavnychy, *Runtime Governance for AI Agents:
Policies on Paths*, arXiv:2603.16586v1, 17 Mar 2026. Full text read 2026-10-18
(via arXiv HTML rendering). What follows paraphrases; no extended quotation.

**Their framework, in brief.** Each policy j is a deterministic function
π_j(A, P_i, s*, Σ) → [0,1]: agent identity (with registered metadata and a hash
of the agent definition), partial execution path, proposed next action (type +
input; output unknown because it is intended, not yet executed), and shared
governance state — mapping to a *violation probability*. Step score
v_i = 1 − ∏(1 − π_j); fleet objective: maximize expected utility subject to
expected violations ≤ risk budget B. Decision function δ maps v_i to
Pass / Steer / Block via organizationally calibrated thresholds. Their central
open problem: **risk calibration** — a policy returning 0.7 must mean a
genuinely 70%-likely violation, which requires labeled traces that don't exist
at scale. Their reference implementation currently treats scores as severity
indicators — presented as a shortcoming.

**The question:** take their AI-Act-inspired example policies (§3.5, Table 1)
and run them through CumAdm + Depends(Action, U) + the P_unknown rule. Where
does a probability threshold come out cleaner or safer as a typed U block?

## Policy-by-policy

**(a) Agent integrity** (hash of running definition vs registered hash; binary)
and **(b) Purpose/documentation** (required metadata present; binary).
Both map to deterministic preconditions in either framework — no uncertainty
involved, no disagreement. These are rails, not probabilities, on both sides.

**(c) PII predecessor** (1 if personal data accessed with no PII_Check step in
path; binary) and **(d) Approval before external actions** (1 if external
action with no Human_Approval in path; binary). Their framework expresses a
missing precondition as *violation probability 1* — "certain violation." The
Lexicon expresses it as **missing warrant**, which is not a probability at all
and has a different remedy: a certain violation says *block*; missing warrant
says *the action was never authorized — seek authorization or refuse*.
Conflating the two hides the operational difference between "this is
forbidden" and "nobody said yes." The Lexicon's authority separation keeps
them distinct: approval is an AuthorityRecord/assent event, not a score.

**(e) Data exfiltration** (σ_max/σ_ceiling — ratio of max sensitivity touched
to a ceiling; graduated). **This is the cleanest comparison case.** The ratio
is presented as a violation probability, but it is a severity indicator
wearing a probability's clothes: nothing grounds the claim that touching
60%-of-ceiling data makes external transmission 60%-likely a violation. Worse,
the sensitivity labels are written into Σ *by the agent's own completed
steps* — self-reported sensitivity laundered into a number. The Lexicon's
treatment: the labels are evidence with provenance terminating in the agent
itself, i.e. **unverifiable provenance → typed U**, not input to arithmetic.
P_unknown applies: never fabricate the number. Either a deterministic rail
covers the case (external send of σ-class data requires verified
classification — binary, no probability) or the uncertainty is typed, the
safety state rises, and the action blocks pending a resolution path. Cleaner
(no false precision) and safer (self-reported labels can't buy down the
score by construction).

**(f) Information barrier** (1 if Σ shows cross-barrier access; binary).
Deterministic state check in both frameworks; no uncertainty to type. Agreed
ground — and their own note that it "cannot be evaluated from A's path
alone" is exactly why Σ (shared state) exists in their framework and why the
history commitment exists in ours.

**(g) Execution bounds** (score rising linearly with |P_i|, reaching 1 at a
configured maximum; graduated). **The second comparison case, and the most
damning for ungrounded probabilities.** A linear map from step count to
violation probability has no grounding whatsoever — it is pure fabrication,
and their own open problem on *behavioral drift* concedes the real
uncertainty: is this long path degrading? The Lexicon splits it honestly: the
bound itself is a deterministic rail (fail-closed at N steps — no probability
needed, no precision pretended), and the drift question is a typed U with a
resolution path (profile the v_T distribution against a baseline; without a
baseline the U stays open and the bound does the work). Their framework must
either invent the number or leave drift unaddressed; ours does neither.

**(h) Time restriction** (1 outside permitted hours; binary). Deterministic
precondition; agreed ground.

## What their open problems map to here

- **Risk calibration** (their central open problem) → answered by P_unknown +
  typed U classes: where calibration data doesn't exist, don't emit the
  number; type the ignorance and attach a resolution path.
- **Delegation provenance** (their open problem: what propagates from a
  sub-agent's path P′; unsettled) → answered by the S1 work: the
  AuthorityRecord with provenance chain, holder binding, and individual
  revocability. Propagate *warrant*, not just state summaries.
- **Policy interaction at scale** (their composition rule inflates v_i as
  policies accumulate) → the composition battery already demonstrates the
  deterministic analogue (individually-admissible actions composing into an
  inadmissible trajectory via the daily rail; split attacks dying at the
  composition boundary). Deterministic rails compose legibly; multiplied
  probabilities compose opaquely.
- **Completeness of enforced compliance** (agents operating outside the
  governed environment) → conceded on both sides; no framework governs what
  it can't see. Their honesty here is noted and shared.

## Verdict

Two of their eight example policies — data exfiltration (e) and execution
bounds (g) — come out cleaner *and* safer as typed U blocks than as
probability thresholds: the thresholds fabricate precision where no grounding
exists, and in (e) the inputs are self-reported by the governed party. Two
more — PII predecessor (c) and approval-required (d) — come out cleaner
reframed as missing warrant rather than certain violation, because the remedy
differs. The remaining four are deterministic preconditions under both
frameworks; no disagreement.

The pattern: **their framework is forced to price what it cannot measure,
because probabilities are its only uncertainty representation.** The
Lexicon's typed non-numeric uncertainty exists precisely for the cases where
pricing is fabrication. That is the comparison case, and it lands on their
own central open problem.
