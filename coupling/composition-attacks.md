# Composition attacks: the horizontal frontier

**Status:** ATTACK SCOPE 2026-10-18. No implementation. This document
scopes the next red-team target: cases where individually legitimate
governed operations compose into a consequence that no single
operation's authority admitted.

## 1. The attack class

Everything attacked so far has been vertical: bypass a boundary,
replay authority, survive a crash, exceed a counter, evade
serialization. In each case one operation violated its own
authorization.

Composition attacks horizontally: every operation satisfies its own
authorization, and the *sequence* is the violation. The property under
test:

*No sequence of governed effects may produce a consequence that the
composition of their authorities did not admit.*

The sole-authority-path as currently stated does not cover this: each
effect crosses the path legitimately. The unauthorized thing exists
only at the level of sequences, interactions, or emergent combined
effects.

## 2. Instances

### C-1: Quantitative composition (engine gap, mechanical)

N actions, each under its per-action limit, composing past a
cumulative bound. Concrete: 10 writes of $40 (each < $50/txn) =
$400, against a $200/day principal intent.

Current state: the **prototype** has CumAdm (cumulative admission) and
daily limits. The **engine** has no cumulative tracking whatsoever —
verified in `NineGates.kt`: no cumulative counters, no daily limits,
no cross-action accounting. The only cross-action state is
`sealedActionIds` (replay) and the ledger (observation, not judgment).

Discriminator: 10 individually-admitted writes, total exceeding the
cumulative bound. Engine today: all seal. Prototype: halts at the
bound.

Diagnostic: move the boundary. The cumulative invariant exists (in
the prototype); it hasn't reached the engine's commit path. The
machinery is the same as H1's usage accounting, extended across a
time window. Mechanical, not new.

### C-2: Semantic composition / exfiltration (hard; possibly new)

`Read(secret)` — authorized (file under the allowed prefix).
`Write("net/out", <bytes of secret>)` — authorized (predicate
satisfied, bytes are just bytes). The composition is exfiltration;
neither authority admitted it.

Current state: the engine has no data-provenance tracking. A Write's
payload is opaque bytes; the gates cannot distinguish "public data"
from "just-read secret." Known residual from S-1:
"concealed-aggregate-effect is semantic, owned by Lexicon layer" —
but the enforcement path from Lexicon judgment to commit boundary is
unspecified.

Discriminator: read-then-write-exfiltrate with both actions
individually admitted. Engine today: both seal; exfiltration
unobserved.

Diagnostic: this may be where reality refuses. Full
information-flow control (taint tracking through the substrate and
all actions) is a new instrument, not a moved boundary. The
mechanical approximation is coarse taint: provenance marks on
substrate records read from sensitive sources; tainted payload to
egress scopes requires composition-level assent (or refuses). That
approximation is buildable; complete IFC is not, with current
instruments. Expect an explicit residual with a precise shape, not
a silent gap.

### C-3: State-dependent meaning drift

Assent binds the action's rendering (bytes). Execution happens
against the *current* substrate — which a prior governed action may
have changed, altering what those bytes *mean*. `Write("config",
{mode:"open"})` assented under S0 (isolated) executes under S1
(networked): same bytes, different consequence.

Current state: NineGates evaluates against the current substrate
(GateContext carries it) and computes impact at execution time —
but nothing compares "meaning at assent" against "meaning at
execution." The rendering is a pure function of action bytes, not of
action-in-state.

Discriminator: assent under S0, intervening state change to S1 via a
governed action, execution under S1 where the consequence class
changed. Does any gate notice? Today: no.

Diagnostic: partially a moved boundary (the capability spec's
stateDeps address this *within* a capability — enrollment change
kills the epoch). Across separate mutation capabilities, the
comparison doesn't exist. Mechanical form: bind the relevant state
assumptions into the assent (extend stateDeps to mutation
capabilities), or re-derive impact-at-execution against
impact-at-assent and halt on class change. Buildable, but not yet
specified.

### C-4: Cross-epoch accumulation (spec gap)

Per-epoch `maxBytes` bounds each epoch. Nothing accumulates across
renewals. Epoch 1: 90MB (under bound). Renew (legitimate).
Epoch 2: 90MB (under bound). Cumulative 180MB — split precisely to
stay under per-epoch accounting.

Current state: the frozen spec (v2.1) has no cross-epoch cumulative
state. Reservations are per-capability-id; renewal starts fresh.
This is a gap the implementation search found — a candidate spec
amendment (v2.2), not an interpretation.

Discriminator: two epochs, each compliant, cumulative exceeding the
principal's intent. Spec today: no mechanism observes it.

Diagnostic: mechanical — cumulative counters keyed by
(principal, scope) carried across renewals, with the renewal
carrying forward the cumulative total. Same accounting machinery as
H1, extended across the renewal boundary. But it changes the spec,
so it needs an explicit decision.

### C-5: Assent composition (ceremony scope)

The human assents to A and to B separately, each with a faithful
rendering. The agent composes A+B into a consequence neither
rendering showed. The assents were informed; the composition was
not.

Current state: the ceremony renders one action. The composition is
invisible to the principal.

Discriminator: resists mechanical testing — it's about what the
principal was shown, not what the engine computed. The mitigation is
ceremony design: when the Lexicon (or a sequence judge) detects an
aggregate effect, the *composition* becomes the unit of assent, not
the members.

Diagnostic: new, and partly human-factors. The mechanical hook: a
sequence-level judgment that can escalate the unit of admission from
action to sequence.

## 3. The split

The frontier divides:

- **Mechanical** (move the boundary): C-1 (cumulative counters at
  the engine commit path — prototype invariant, engine gap), C-4
  (cross-epoch accumulation — extends H1; needs a spec amendment).
- **Semantic** (possibly new invariants): C-2 (information flow —
  coarse taint is buildable, full IFC is a residual), C-3
  (meaning-drift — stateDeps extended to mutation capabilities),
  C-5 (assent scope — ceremony design + sequence-level escalation).

## 4. Next falsification experiments (in order)

1. **C-1**: demonstrate 10×$40 sealing in the engine (documents the
   gap); then implement cumulative counters at `execute()` and show
   the 6th halting. Mechanical.
2. **C-4**: specify cross-epoch accumulation as a v2.2 amendment
   proposal; implement only on decision.
3. **C-3**: construct the S0→S1 meaning-drift case as a failing test;
   extend stateDeps or impact-comparison to close it.
4. **C-2**: build the read-then-exfiltrate demonstration; implement
   coarse taint as the mechanical approximation; write the full-IFC
   residual explicitly.
5. **C-5**: design the sequence-escalation ceremony (with the
   principal, not unilaterally — it's his assent being scoped).

Order matters: take the mechanical ones first (they're boundary
moves), then let the semantic ones show exactly where new invariants
— or honest residuals — live.
