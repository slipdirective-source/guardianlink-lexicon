# guardianlink-lexicon

The integration layer between two halves of one system:

- **`lexicon/`** — the [Trajectory Lexicon](https://github.com/slipdirective-source/trajectory-lexicon): the specification. A fail-closed language for consequential discrimination, trajectory mapping, bounded intervention, agency, safety, responsibility, and governed execution. It says what "governed" means.
- **`guardianlink/`** — [GuardianLink](https://github.com/slipdirective-source/Guardianlink): the enforcement engine. Voice-biometric assent, deterministic policy gates, Merkle-anchored audit log, fail-closed clocks. It is the machine that refuses to act outside the Lexicon's bounds.

## Why two layers

The spec and the engine make each other recursively stronger. The engine produces consequences; the Lexicon types them; the typed record exposes where the spec is loose; the spec revision tightens the engine; the tighter engine produces cleaner consequences. Each pass leaves both more precise than the last. Deployment feeds the loop too: every real-world run lands in the audit log as evidence the framework can audit itself against.

The load-bearing condition: revisions must be allowed to *break* the engine, never just describe it. A spec change that only blesses what the engine already does is immunization, and the Lexicon's own RegimeDelta rules forbid it.

## Coupling

`coupling/` holds the interface elements that join the layers:

| File | Purpose |
|---|---|
| `lexicon-output.schema.json` | Machine-readable schema for `LexiconOutput` (§16): the typed record every governed decision emits. |
| `LEXICON_TO_GUARDIANLINK.md` | Field-by-field mapping: each LexiconOutput element to the GuardianLink component that produces or consumes it. |
| `safety-state-mapping.md` | GREEN/YELLOW/ORANGE/RED/BLACK bound to concrete engine behavior. |

## Working the layers together

1. GuardianLink's Gate 7 (execution gate) consumes `LexiconOutput.admissibility` and `authorizationRequirement` before any consequential execution.
2. Every executed action emits a `decisionRecord` into the Merkle-anchored audit log, satisfying the Lexicon's provenance (Prov) and consequence-record proof obligations (§17.1).
3. Safety-state transitions drive engine mode: see `safety-state-mapping.md`.
4. Framework revisions that change engine behavior arrive as RegimeDeltas with independent justification — never silent.

## Layout

```
guardianlink-lexicon/
├── lexicon/          # submodule: slipdirective-source/trajectory-lexicon
├── guardianlink/     # submodule: slipdirective-source/Guardianlink
└── coupling/         # interface specs joining the two layers
```
