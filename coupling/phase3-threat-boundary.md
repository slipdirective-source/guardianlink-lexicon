# Phase 3 Threat-Model Boundary (explicit)

## What the durable store guarantees

- **Crash consistency:** after any crash and recovery, the observable
  capability-store state equals the state after some atomic prefix of the
  operation history (RecoveryOracle). Verified by the crash harness (every
  write/fsync boundary, torn writes, crash-during-recovery, double crashes)
  and by exhaustive TLC model-checking of the commit protocol.
- **Cross-process linearization:** the file lock + append + fsync is a single
  atomic operation. Two processes cannot both commit the same capability;
  the check-and-set is under the lock.
- **Monotonicity:** consumed sets only grow, revocation sets only grow,
  usage counters only increase, fencing epochs only increase. These are
  monotonic counters, never wall-clock-derived.

## What it does NOT guarantee (explicitly out of scope)

### Store rollback (snapshot restore)

**Threat:** an operator (or attacker with filesystem access) restores the
`capability.log` file from an older backup/snapshot. Consumed capabilities
become unconsumed; revoked capabilities become unrevoked; usage counters
roll back. The store cannot distinguish a restored old log from a legitimate
log — both are well-formed.

**Why no local mechanism prevents it:** any purely local check (checksums,
sequence numbers, HMACs) is defeated by restoring the *entire* store
directory to a prior consistent state. The attacker isn't forging a record;
they're rewinding time. Detecting rewind requires a monotonic reference
*outside* the rewound store.

**Disposition:** OUT OF SCOPE in writing for Phase 3. The mitigation is an
external monotonic anchor: periodically anchor the log's tip hash (or the
fencing epoch) to an external system that the rollback attacker cannot
rewind — the existing `ExternalAnchor` (Merkle root anchoring) is the
natural future anchor point. On recovery, the store would compare its log
tip against the anchored tip and refuse to start if the log is behind.
This is defined as future work, not implemented in Phase 3.

### Wall-clock skew and expiry

Usage counters and fencing epochs are monotonic counters, never derived
from wall-clock. **"Cannot roll backward" holds under clock skew** for
these. Expiry (`notAfterMs`) *is* wall-clock-derived by necessity (a TTL
is a wall-clock concept). Under clock skew:
- Clock jumps forward: capabilities expire early (fail-closed, safe).
- Clock jumps backward: an expired capability may appear valid again.
  Mitigation: the store checks expiry under the lock with its own clock
  read (no staleness within the commit), but it cannot defend against the
  clock itself lying. Clock trust is a deployment assumption, documented
  here, not a store guarantee.

### Byzantine storage

The store assumes the filesystem is not actively malicious (it may crash,
lose writes, reorder without fsync — all modeled — but it does not forge
records). A storage layer that returns different data to different readers,
or that acknowledges an fsync without persisting, is out of scope. This is
the standard crash-fault (not Byzantine-fault) storage model.

### Operator with root

An operator with unrestricted filesystem access can delete the log, corrupt
it arbitrarily, or bypass the store entirely. This is the "host disk
adversary" from the residual-attacks doc: out of scope. The store defends
against crashes and concurrent processes, not against the machine's owner.

## Summary table

| Threat | Covered? | Mechanism / Disposition |
|---|---|---|
| Crash at any write/fsync point | Yes | WAL + fsync + idempotent replay; harness + TLC |
| Torn write (partial log line) | Yes | Malformed lines ignored on replay; harness-tested |
| Crash during recovery | Yes | Recovery is idempotent; harness-tested |
| Double crash | Yes | Same; harness-tested |
| Two processes, same capability | Yes | File lock + atomic check-and-set |
| Validate-stall-resume after revoke | Yes | Under-lock recheck + fencing epoch |
| Crashed lock holder | Yes | OS releases file lock; fencing blocks stale resume |
| Usage/counters roll backward | Yes | Monotonic counters, never wall-clock |
| Store file restored from backup | **No** | Out of scope; needs external monotonic anchor (future) |
| Wall-clock skew vs expiry | Partial | Fail-closed on forward jump; clock trust assumed |
| Byzantine storage | No | Crash-fault model only |
| Root operator | No | Host-disk adversary out of scope |
