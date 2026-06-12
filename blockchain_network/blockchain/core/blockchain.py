"""
core/blockchain.py
──────────────────
The main Blockchain class:
  • Genesis block creation
  • Proof-of-Work mining
  • Transaction management (mempool)
  • Chain validation
  • Wallet balance calculation
  • Chain replacement (consensus)
"""

import json
from typing import List, Dict, Any, Optional

from core.block import Block


class Blockchain:
    # Mining difficulty: how many leading zeros required in hash
    DIFFICULTY        = 3
    MINING_REWARD     = 10.0   # coins awarded to miner per block
    REWARD_ADDRESS    = "NETWORK"

    def __init__(self):
        self.chain:               List[Block]          = []
        self.pending_transactions: List[Dict[str, Any]] = []
        self.wallets:             Dict[str, float]      = {}   # address → balance cache

        # Create the first block (genesis)
        self._create_genesis_block()

    # ── Genesis ───────────────────────────────────────────────
    def _create_genesis_block(self) -> None:
        genesis = Block(
            index         = 0,
            transactions  = [],
            previous_hash = "0" * 64,
            nonce         = 0,
        )
        genesis.hash = genesis.compute_hash()
        self.chain.append(genesis)

    # ── Properties ────────────────────────────────────────────
    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    @property
    def height(self) -> int:
        return len(self.chain)

    # ── Proof-of-Work ─────────────────────────────────────────
    def proof_of_work(self, block: Block) -> str:
        """
        Increment the nonce until block.hash starts with
        DIFFICULTY leading zeros.  Returns the winning hash.
        """
        target = "0" * self.DIFFICULTY
        block.nonce = 0
        computed = block.compute_hash()
        while not computed.startswith(target):
            block.nonce += 1
            computed = block.compute_hash()
        return computed

    # ── Mining ────────────────────────────────────────────────
    def mine_pending_transactions(self, miner_address: str) -> Block:
        """
        Bundle all pending transactions (plus the mining reward)
        into a new block and add it to the chain.
        """
        # Add coinbase reward transaction
        reward_tx = {
            "sender":    self.REWARD_ADDRESS,
            "recipient": miner_address,
            "amount":    self.MINING_REWARD,
            "type":      "reward",
        }
        transactions = list(self.pending_transactions) + [reward_tx]

        new_block = Block(
            index         = len(self.chain),
            transactions  = transactions,
            previous_hash = self.last_block.hash,
        )

        # Mine it
        new_block.hash = self.proof_of_work(new_block)
        self.chain.append(new_block)

        # Clear mempool
        self.pending_transactions = []

        # Refresh wallet balances
        self._rebuild_balances()

        return new_block

    # ── Transactions ──────────────────────────────────────────
    def add_transaction(
        self,
        sender:    str,
        recipient: str,
        amount:    float,
        memo:      str = "",
    ) -> Dict[str, Any]:
        """
        Validate and add a transaction to the mempool.
        Returns the transaction dict.
        Raises ValueError on insufficient funds or bad input.
        """
        if not sender or not recipient:
            raise ValueError("Sender and recipient addresses are required.")
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        if sender != self.REWARD_ADDRESS:
            balance = self.get_balance(sender)
            if balance < amount:
                raise ValueError(
                    f"Insufficient funds: {sender[:8]}… has {balance:.2f}, "
                    f"tried to send {amount:.2f}."
                )

        tx = {
            "sender":    sender,
            "recipient": recipient,
            "amount":    amount,
            "memo":      memo,
            "type":      "transfer",
        }
        self.pending_transactions.append(tx)
        return tx

    # ── Wallet / Balances ─────────────────────────────────────
    def get_balance(self, address: str) -> float:
        """Calculate the confirmed balance of an address from the chain."""
        balance = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx["recipient"] == address:
                    balance += tx["amount"]
                if tx["sender"] == address:
                    balance -= tx["amount"]
        return round(balance, 8)

    def _rebuild_balances(self) -> None:
        """Rebuild the wallet cache (called after each mined block)."""
        addresses = set()
        for block in self.chain:
            for tx in block.transactions:
                addresses.add(tx["sender"])
                addresses.add(tx["recipient"])
        for addr in addresses:
            self.wallets[addr] = self.get_balance(addr)

    def register_wallet(self, address: str) -> None:
        """Register a new wallet with zero balance if not seen before."""
        if address not in self.wallets:
            self.wallets[address] = 0.0

    # ── Chain Validation ──────────────────────────────────────
    def is_valid_chain(self, chain: List[Block] = None) -> bool:
        """
        Validate every block in the chain:
          1. Hashes are correct
          2. Proof-of-Work is satisfied
          3. previous_hash links are intact
        """
        chain = chain or self.chain
        for i in range(1, len(chain)):
            current  = chain[i]
            previous = chain[i - 1]

            # Recompute and compare hash
            if current.hash != current.compute_hash():
                return False
            # Check difficulty
            if not current.hash.startswith("0" * self.DIFFICULTY):
                return False
            # Check linkage
            if current.previous_hash != previous.hash:
                return False
        return True

    def is_valid_block(self, block: Block) -> bool:
        """Validate a single incoming block."""
        if block.previous_hash != self.last_block.hash:
            return False
        if block.hash != block.compute_hash():
            return False
        if not block.hash.startswith("0" * self.DIFFICULTY):
            return False
        return True

    # ── Consensus (longest valid chain wins) ──────────────────
    def replace_chain(self, new_chain: List[Dict]) -> bool:
        """
        Replace our chain with a longer valid one.
        Used in a multi-node network.  Returns True if replaced.
        """
        candidate = [Block.from_dict(b) for b in new_chain]
        if len(candidate) <= len(self.chain):
            return False
        if not self.is_valid_chain(candidate):
            return False
        self.chain = candidate
        self._rebuild_balances()
        return True

    # ── Serialisation ─────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        return {
            "length":   self.height,
            "chain":    [b.to_dict() for b in self.chain],
            "pending":  self.pending_transactions,
            "wallets":  self.wallets,
        }

    def chain_as_list(self) -> List[Dict]:
        return [b.to_dict() for b in self.chain]

    # ── Transaction history for an address ────────────────────
    def get_transactions(self, address: str) -> List[Dict[str, Any]]:
        history = []
        for block in self.chain:
            for tx in block.transactions:
                if tx["sender"] == address or tx["recipient"] == address:
                    entry = dict(tx)
                    entry["block_index"] = block.index
                    entry["block_hash"]  = block.hash[:16] + "…"
                    history.append(entry)
        return history
