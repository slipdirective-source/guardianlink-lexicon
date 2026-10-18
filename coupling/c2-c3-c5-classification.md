# C-2 / C-3 / C-5 Classification (Inversion Point Methodology, 2026-10-18)

Per the inversion point methodology: remaining uncertainty is CLASSIFIED,
not reflexively eliminated. The core's claim is fully specified (C-1 fixed,
C-4 decided). What follows is the classification of the remaining composition
scope against that claim.

## C-2: Semantic composition / exfiltration — RESIDUAL

**What it is:** `Read(secret)` authorized; `Write("net/out", <bytes>)`
authorized; the composition is exfiltration neither authority admitted.
The engine has no data-provenance tracking. A Write's payload is opaque
bytes; the gates cannot distinguish "public data" from "just-read secret."

**Classification:** Explicit residual. The core does not track provenance
and does not enforce information flow control. This cannot be closed by
testing — it requires new machinery (provenance tracking, IFC) that does
not exist in the current core.

**Boundary:** The core's claim does NOT include semantic exfiltration
prevention. Any application requiring exfiltration resistance is a
candidate construction that must supply its own provenance/IFC layer
above the core.

## C-3: State-dependent meaning drift — SEMANTIC BOUNDARY

**What it is:** Assent binds the action's rendering (bytes). Execution
happens against the current substrate, which a prior governed action may
have changed, altering what those bytes mean. Same bytes, different
consequence.

**Classification:** Semantic boundary, not a mechanical defect. The issue
is the relationship between the action's semantics and the world state,
not the authority mechanism. NineGates evaluates against the current
substrate, but nothing compares "meaning at assent" vs. "meaning at
execution."

**Boundary:** The core guarantees the authorized bytes execute; it does
not guarantee the bytes mean the same thing at execution as at assent.
Applications requiring meaning-stability must construct it above the core
(e.g., by binding substrate state hashes into the authorization).

## C-5: Assent composition — DEFERRED TO PRINCIPAL

**What it is:** The human assents to A and B separately, each with a
faithful rendering. The agent composes A+B into a consequence neither
rendering showed. The assents were informed; the composition was not.

**Classification:** Requires principal participation. The mitigation is
about what the principal was shown (ceremony design), not what the engine
computed. Cannot be resolved unilaterally by implementation.

**Boundary:** The core renders and binds individual actions. Composition
visibility is a ceremony/interface design question for the principal.

## Summary

| ID | Class | Core claim includes? | Requires |
|----|-------|---------------------|----------|
| C-2 | Residual | No (no provenance/IFC) | New machinery (future) |
| C-3 | Semantic boundary | No (bytes, not meanings) | Application-layer construction |
| C-5 | Deferred | No (single-action rendering) | Principal design input |

None of the three is a demonstrated defect in the core's mechanical
properties. All three are classified boundaries against which candidate
constructions must be evaluated.
