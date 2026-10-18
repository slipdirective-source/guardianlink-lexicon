"""lexicon_governor: executable coupling contract between the Trajectory Lexicon
(specification) and GuardianLink (enforcement engine).

Prototype status: the governance path is real (records, ratchet, binding,
CumAdm, decision-dominance, hash-chained history); action *effects* are
simulated. It demonstrates the contract, not the engine internals.
"""
from .records import HistoryLog, AuthorityRecord, GovernanceConstraintRecord, ConsequenceRecord
from .governor import Governor, LexiconLayer, Clock, FailClosed
from .actions import (Action, SendEmail, ModifyFile, SpendMoney, ExternalApiCall,
                      ALL_RAILS)

__all__ = ["HistoryLog", "AuthorityRecord", "GovernanceConstraintRecord",
           "ConsequenceRecord", "Governor", "LexiconLayer", "Clock", "FailClosed",
           "Action", "SendEmail", "ModifyFile", "SpendMoney", "ExternalApiCall",
           "ALL_RAILS"]
