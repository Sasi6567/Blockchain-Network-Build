"""
core/block.py
─────────────
A single block in the blockchain.
Each block holds transactions, links to the previous block via its hash,
and is secured by a Proof-of-Work nonce.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import List, Dict, Any


class Block:
    """Represents one block in the chain."""

    def __init__(
        self,
        index: int,
        transactions: List[Dict[str, Any]],
        previous_hash: str,
        nonce: int = 0,
        timestamp: float = None,
    ):
        self.index         = index
        self.timestamp     = timestamp or datetime.now(timezone.utc).timestamp()
        self.transactions  = transactions
        self.previous_hash = previous_hash
        self.nonce         = nonce
        self.hash          = self.compute_hash()

    # ── Hashing ───────────────────────────────────────────────
    def compute_hash(self) -> str:
        """SHA-256 hash of the block's canonical JSON representation."""
        block_string = json.dumps(self.to_dict(include_hash=False), sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    # ── Serialisation ─────────────────────────────────────────
    def to_dict(self, include_hash: bool = True) -> Dict[str, Any]:
        data = {
            "index":         self.index,
            "timestamp":     self.timestamp,
            "transactions":  self.transactions,
            "previous_hash": self.previous_hash,
            "nonce":         self.nonce,
        }
        if include_hash:
            data["hash"] = self.hash
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Block":
        block = cls(
            index         = data["index"],
            transactions  = data["transactions"],
            previous_hash = data["previous_hash"],
            nonce         = data["nonce"],
            timestamp     = data["timestamp"],
        )
        block.hash = data["hash"]
        return block

    def __repr__(self) -> str:
        return (
            f"Block(index={self.index}, "
            f"txns={len(self.transactions)}, "
            f"hash={self.hash[:12]}…)"
        )
