# Development governance protocol

This project is developed under the principles it specifies. The Trajectory Lexicon's self-application test (§22) does not stop at the document boundary: **the development process is one of the earliest serious test cases of the machinery.** These artifacts are no longer conversational output — a formal working specification and an implemented fail-closed execution governor — and potentially high impact warrants developing them the way they'd require anyone else to work.

## 1. Change classes and provenance

Every change to a governed artifact carries, in its commit message or changelog entry:

| Class | Meaning | Example |
|---|---|---|
| Editorial | Language-only; no semantic change. | Typo fix, table reformatting. |
| Tightening | Formalizer's precision work; doctrine unchanged. | Disambiguating a definition, fixing a garbled table. |
| Doctrine | Changes what the framework claims. | Four-valued Δ, authorship clause, new invariant. |
| Tested | A change plus the test that earned it. | A5c passing against a new U-handling rule. |

Plus: **who proposed it** (Caleb / Copilot / Muse / other), **when**, and **status**: Proposed or Validated.

**Status is orthogonal to class.** A Doctrine-class change can be Proposed; an Editorial change is Validated by review. The change class says what kind of change it is; the status says what epistemic standing it has earned. "Merged into Git" is neither — a merge records that the change exists, not that it is validated. (The class formerly named "Validated" is now "Tested" precisely to prevent this type collapse.) A Proposed change is a candidate (Cand/Hyp in Lexicon terms); it becomes Validated only through the evidence its class requires. Failure to validate is not falsification — the proposal stays on record.

## 2. Proposed vs validated

No proposal is merged as validated without its evidence:

- Editorial: review by the author.
- Tightening: review plus a statement of the doctrine it preserves (the doctrine-vs-language line).
- Doctrine: Caleb's explicit word. Silence is not approval.
- Tested: the operational test, named and linked. A green test suite validates the *implementation against the spec*; it does not validate the *spec*.

## 3. Evidence discipline

Three rules, stated absolutely:

1. **An AI's confidence is not evidence.** A fluent, confident proposal from any model — including the ones building this — is a candidate until tested. Confidence scales with fluency, not with truth.
2. **A successful implementation is not proof the reasoning was correct** (§16, applied to development). Tests passing means the engine matches the spec. Spec correctness needs the adversarial battery and independent review.
3. **A prediction is not a fact.** "Potentially high impact" warrants seriousness of process; it does not warrant promoting impact claims into established facts. Hyp stays Hyp until Gamma says otherwise.

## 4. Disagreements stay visible

Reviewer disagreements (human or AI) are recorded in the open-decisions register with positions attributed, never silently resolved by whoever edits last. A disagreement that can't be resolved by evidence becomes a typed unresolved item (§5), not a footnote.

## 5. Unresolved problems stay typed

Open issues use the Lexicon's own U-classes (U_obs … U_fund). Each carries its required response and, where applicable, its resolution path. "Later" is not a type.

## 6. Disputed operationalizability

When reviewers disagree on whether a claim *can* be operationalized into a test, the claim is typed as U_model/U_ident with a resolution path — not shelved, not forced into a premature test. The type records the disagreement; the path records how it could be settled.

## 7. Proportionality (the Lexicon applied to itself)

Governance burden scales with consequence — the same principle the Lexicon applies to actions:

- Editorial changes: light review.
- Tightening: review + doctrine-preservation statement.
- Doctrine and engine-behavior changes: full protocol (proposal, evidence, attribution, tests).
- Emergency changes: permitted with a written record made at the time, reviewed after. The record is mandatory; the review follows as soon as the emergency passes.

Process weight that strangles development under deadlines is itself a governance failure — it routes work around the process (the bypass sensor applies here too).

## 8. Self-amendment

This protocol revises under its own rules: amendments are Doctrine-class changes, attributed, and subject to the same evidence discipline. The protocol cannot exempt itself from itself.

## 9. Registers

| Register | Location | Purpose |
|---|---|---|
| Provenance ledger | Head of each spec document | What changed, whose doctrine, what effect |
| Changelog | `CHANGELOG.md` per repo | Version history |
| Open decisions | This file's §10 (below) / GitHub issues | Attributed disagreements awaiting resolution |
| Test battery | `coupling/threshold-battery.md` | Operational tests; regression gates for U-handling changes |
| Attic | `attic/` | As-received sources; provenance anchor |

## 10. Open decisions

| # | Decision | Positions | Status |
|---|---|---|---|
| 1 | Four-valued Δ vs three-valued D as canonical | Caleb's A1–A9 (four-valued, adopted 2026-10-17) vs Lexicon v1.1/v1.2 text (three-valued) | Proposed (v1.3 implements four-valued per his adoption; awaiting his confirmation) |
| 2 | T_unk operative criterion to spec level (v1.4) | Cut 2026-10-18 with Caleb's explicit word. Counterfactual-sensitivity criterion in spec; Depends demoted to information. | Closed |
| 3 | Lexicon vs CDC relationship | Operationalization layer vs supersession | Open — Caleb's call |
| 4 | Manuscript authority over formalizations | Struck from v0.3 normative text; §22 "neither overrules the other without Caleb's word" | Open — Caleb's call |
| 5 | Objective statement (§0.1, v1.5) | Cut 2026-10-18 on Caleb's explicit word ("Yes. Cut v1.5.": maximize-subject-to structure; constraints as hard bounds; "legitimate" = provenance-terminating delegation). | Closed |

## 11. The objective razor

Every proposal for the stack must answer: **which term of the objective does this serve?** A mechanism must either increase a maximand (useful competence, legitimate delegated agency, consequential leverage) or protect a hard constraint (human sovereignty, revocability, bounded authority, corrigibility, auditability, recoverability). If it does neither, it is challenged — the burden is on the proposer to show why it's there.

The razor applies retroactively: `coupling/objective-coverage.md` maps every existing mechanism to its objective term. Anything unaccounted for is flagged, not grandfathered. "Maximum leverage, minimal surrender of control" is the one-line compression; the full statement is Lexicon §0.1.
