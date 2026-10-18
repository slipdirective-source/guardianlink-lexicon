---- MODULE DurableCommitSmall ----
(*
 * Minimal bounded model of the durable commit protocol.
 * 1 process, 2 capabilities, at most 3 operations, crash at any point.
 * Checks the prefix property exhaustively on this small instance.
 *)

EXTENDS Naturals, Integers, Sequences, FiniteSets, TLC

CONSTANTS Caps, MaxLogLen

VARIABLES
    log,        \* Sequence of COMMIT records (durable)
    mem,        \* Volatile set of consumed caps (lost on crash)
    opsDone     \* Number of operations attempted (bound)

TypeOK ==
    /\ log \in Seq([op: {"commit", "revoke"}, cap: Caps])
    /\ mem \in SUBSET Caps
    /\ opsDone \in 0..10

Init ==
    /\ log = <<>>
    /\ mem = {}
    /\ opsDone = 0

(* Commit a capability: atomic append + memory update. *)
Commit(cap) ==
    /\ opsDone < 3
    /\ cap \notin mem
    /\ log' = Append(log, [op |-> "commit", cap |-> cap])
    /\ mem' = mem \cup {cap}
    /\ opsDone' = opsDone + 1

(* Revoke: bounded, like Commit. *)
Revoke(cap) ==
    /\ opsDone < 3
    /\ log' = Append(log, [op |-> "revoke", cap |-> cap])
    /\ opsDone' = opsDone + 1
    /\ UNCHANGED <<mem>>

(* Crash: volatile memory lost; recovery replays the log. *)
Crash ==
    /\ mem' = {r.cap : r \in {s \in {log[i] : i \in 1..Len(log)} : s.op = "commit"}}
    /\ UNCHANGED <<log, opsDone>>

Next ==
    \/ \E cap \in Caps: Commit(cap)
    \/ \E cap \in Caps: Revoke(cap)
    \/ Crash

Spec == Init /\ [][Next]_<<log, mem, opsDone>>

(* The prefix property: mem always equals the replay of the FULL log
 * (because every commit updates both atomically), and after a crash,
 * mem equals replay(log) which is a prefix of the history.
 * Here: mem == {caps committed in log}. *)
PrefixHolds ==
    mem = {r.cap : r \in {s \in {log[i] : i \in 1..Len(log)} : s.op = "commit"}}

(* No resurrection: once in the log, a commit is never removed. *)
LogAppendOnly ==
    [][Len(log') >= Len(log)]_<<log>>

====
