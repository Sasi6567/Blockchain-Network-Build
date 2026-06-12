"""
core/node.py
────────────
Simulates a network node that:
  • Holds a Blockchain instance
  • Knows about peer nodes
  • Broadcasts new blocks / transactions to peers
  • Runs consensus (longest-chain) across peers
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from core.blockchain import Blockchain
from core.wallet     import Wallet


class Node:
    """A single node in the blockchain network."""

    def __init__(self, node_id: str, miner_label: str = ""):
        self.node_id:   str         = node_id
        self.chain:     Blockchain  = Blockchain()
        self.peers:     List[Node]  = []
        self.wallet:    Wallet      = Wallet(label=miner_label or node_id)

    # ── Peer management ───────────────────────────────────────
    def connect_peer(self, other: "Node") -> None:
        """Connect two nodes bidirectionally."""
        if other not in self.peers:
            self.peers.append(other)
        if self not in other.peers:
            other.peers.append(self)

    # ── Broadcasting ──────────────────────────────────────────
    def broadcast_transaction(self, sender: str, recipient: str,
                               amount: float, memo: str = "") -> Dict[str, Any]:
        """Add a transaction locally and broadcast to all peers."""
        tx = self.chain.add_transaction(sender, recipient, amount, memo)
        for peer in self.peers:
            try:
                peer.chain.pending_transactions.append(dict(tx))
            except Exception:
                pass
        return tx

    def mine_and_broadcast(self) -> Dict[str, Any]:
        """
        Mine the next block on this node, then broadcast the
        updated chain to all peers (they adopt if it's longer).
        """
        block = self.chain.mine_pending_transactions(self.wallet.address)
        self._broadcast_chain()
        return block.to_dict()

    def _broadcast_chain(self) -> None:
        """Push our chain to peers; peers run consensus."""
        our_chain = self.chain.chain_as_list()
        for peer in self.peers:
            peer.chain.replace_chain(our_chain)

    # ── Consensus ─────────────────────────────────────────────
    def sync(self) -> bool:
        """Pull the longest valid chain from any peer."""
        replaced = False
        for peer in self.peers:
            candidate = peer.chain.chain_as_list()
            if self.chain.replace_chain(candidate):
                replaced = True
        return replaced

    # ── Status ────────────────────────────────────────────────
    def status(self) -> Dict[str, Any]:
        return {
            "node_id":       self.node_id,
            "miner_address": self.wallet.address,
            "chain_height":  self.chain.height,
            "chain_valid":   self.chain.is_valid_chain(),
            "pending_txns":  len(self.chain.pending_transactions),
            "peers":         [p.node_id for p in self.peers],
        }

    def __repr__(self) -> str:
        return f"Node({self.node_id}, height={self.chain.height})"
