# Verification Coverage Matrix

**Question:** not "how many angles?" but "which failure classes does each angle actually cover?"

A row covered only by angles sharing a dependency is a gap that *looks* covered.
A row with nothing is an obvious gap. Build the matrix; the next angle follows
from the thinnest row rather than from adding another of the same kind.

## Failure classes (rows)

1. **Spec wrong** — the frozen spec itself errs (predicate language insufficient, commit rule wrong).
2. **Implementation wrong** — code doesn't implement the spec (TOCTOU race, missed check).
3. **Test wrong** — the test doesn't discriminate what it claims (measures the wrong thing, encodes a false assumption).
4. **Shared model blind spot** — an attack class or failure mode none of the reviewers conceived.
5. **Environment/CI divergence** — passes in CI, fails in deployment (JVM vs Android, FakeClock vs real clock, Gradle sandbox vs device).
6. **Doctrine inconsistent with itself** — the spec contradicts the lexicon or itself.

## Angles (columns)

- **M (me):** Muse writing and reviewing code/tests.
- **C (Copilot):** external model, different training, reviews on relay.
- **T (CI):** automated test execution (Gradle: engine `:test`, sidecar).
- **R (runtime facts):** CI logs, actual behavior, observed failures.
- **U (user):** Caleb — doctrine owner, adversarial thinker, final word.
- **CR (cold read):** someone unfamiliar with the work reading it fresh. (Aspirational; not currently staffed.)

## The matrix (Phase 1 + Phase 2, 2026-10-18)

| Failure class | M | C | T | R | U | CR |
|---|---|---|---|---|---|---|
| Spec wrong | partial (may misread) | partial | — | — | **strong** (froze it) | — |
| Implementation wrong | partial (TOCTOU blind spot proved it) | — | **strong** (24 falsification + 220+) | **strong** (logs caught 3 bugs) | — | — |
| Test wrong | **weak** (wrote wrong tests twice) | partial (may share my assumption) | — (CI executes tests; cannot judge their correctness) | partial (failures reveal, but only when they fire) | — | — |
| Shared blind spot | — (I *am* the shared model) | partial | — | — | partial | — |
| Env/CI divergence | weak (no local Gradle; blind to device) | — | partial (JVM ≠ Android; sidecar e2e is closest) | partial (logs only) | — | — |
| Doctrine inconsistent | partial | — | — | — | **strong** | — |

**Legend:** **strong** = discriminates reliably; partial = covers some instances; weak = present but unreliable; — = no coverage; (parenthetical) = the dependency or limit.

## Reading the matrix

**Thinnest row: "Test wrong."** Every angle covering it depends on *someone's idea of what the test should say*:
- I write the test from my model (wrong twice: CIDR/string, clock sync, voice-challenge entanglement).
- Copilot reviews from a similar model (may share the assumption).
- CI runs it faithfully (a wrong test passing is the worst outcome — silent).
- Runtime facts only help when the wrongness causes a visible failure.

A test that passes but doesn't discriminate is invisible to every current angle. That is the gap that looks covered.

**Second thinnest: "Shared blind spot."** All model-based angles share training-distribution assumptions. Partially covered by U (adversarial thinking) and C (different model), but neither is systematic.

## The orthogonal angle

For "test wrong": a check that **does not depend on anyone's idea of what the test should say**.

- **Property-based:** properties stated directly from the spec ("a consumed capability never commits, for all capabilities/times/renderings"), inputs generated randomly. The property is the spec's claim; the cases are not hand-picked. A wrong mental model of an *example* doesn't matter because there are no examples — only the invariant.
- **Mutation-style:** inject faults into the implementation (flip a comparison, drop a check) and verify the suite kills every mutant. A surviving mutant is a test gap made visible. This measures the *tests*, not the code.

Both are orthogonal to "M writes a test, C reviews it, T runs it" because neither depends on a human's conception of the correct example.

## Status

- [x] Matrix built (this doc).
- [ ] Property-based proof-of-concept for capability invariants (in progress).
- [ ] Mutation-style check (future; likely PIT on the capability package via CI).
- [ ] Cold read (unstaffed; the hire outreach is the long-term answer).
