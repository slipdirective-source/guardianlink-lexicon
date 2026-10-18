# Safety states → engine behavior

Binding, not advisory (§19 invariant 13). The Lexicon's safety state machine (§13) drives GuardianLink's execution mode.

| Lexicon state | Engine mode | Concrete behavior |
|---|---|---|
| GREEN | Normal | Operate and monitor. Gates evaluate per action; audit log appends. |
| YELLOW | Heightened | Slow: increase discrimination. Engine raises the evidence bar — wider candidate enumeration, ResidualRefine invoked on U_ident instead of deferring. |
| ORANGE | Constrained | Constrain and sandbox. High-consequence actions require demonstrated recovery paths; redundancy engaged; novel action classes held for review. New capability grants suspended. |
| RED | Halted | Suspend and contain. Warrant no longer licenses continuation: the engine stops issuing new assent and halts in-flight non-critical executions. Resume requires reassessment and a fresh admissibility pass. No execution except under an explicit externally authorized override record with responsibility transfer (§17.1). |
| BLACK | Preservation | Preserve, contain, restore. Active failure threatening essential function, agents, information, or reconstruction capacity. Engine preserves the audit log and correction capacity first, contains the failure, and permits only preservation/containment/restoration or separately authorized emergency action. |

## Trigger wiring

Each Lexicon trigger (§13) maps to an engine sensor:

- **T_irr / T_cat / T_lock** — pre-execution envelope check; a credible catastrophic branch or irreversibility beyond the authorized threshold forces ORANGE minimum before execution.
- **T_unk** — unresolved exposure becoming decision-dominant forces YELLOW; the engine may not promote past it.
- **T_dep / T_corr** — dependency concentration or correlated failure paths engage redundancy requirements (ORANGE).
- **T_agent** — another agent's meaningful agency materially changing re-opens the authorization evaluation; assent scopes are re-derived.
- **T_model** — observed yield exiting the trajectory envelope marks the trajectory Deviated; the map is revised, not the observation discarded.
- **T_capture** — capability/authority asymmetry trips the capture review; if a hard sovereignty boundary fails, BLACK.
- **T_drift** — objective change without authorization halts dependent execution (RED) until re-authorized.
- **T_resp** — new knowledge updating foreseeability re-opens the responsibility vector; the audit log records the update.
- **T_regime** — post-hoc regime change to protect a model is rejected at the gate; only a RegimeDelta with independent reason is admissible.
- **T_integrity** — evidence/audit provenance losing trust fails closed on all dependent claims and actions.
- **T_recovery** — recovery path becoming non-executable escalates the safety state immediately; high-consequence actions suspend until a qualified path exists.
