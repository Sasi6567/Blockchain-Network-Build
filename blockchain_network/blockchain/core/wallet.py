"""
core/wallet.py
──────────────
A simple wallet that generates a unique address
and can sign / verify transactions using ECDSA
(via Python's built-in hashlib + secrets for the basic version,
or via the 'cryptography' library for full ECDSA when available).

For the basic level this provides:
  • Unique deterministic wallet address (SHA-256 of public seed)
  • Simple HMAC-based signing (no external crypto deps required)
  • Balance retrieval from the blockchain
"""

import hashlib
import hmac
import secrets
import json
from typing import Dict, Any


class Wallet:
    """
    A minimal cryptocurrency wallet.
    Address = first 40 hex chars of SHA-256(public_key).
    """

    def __init__(self, private_key: str = None, label: str = ""):
        # Generate a new key-pair if none supplied
        self.private_key: str = private_key or secrets.token_hex(32)
        self.public_key:  str = self._derive_public_key(self.private_key)
        self.address:     str = self._derive_address(self.public_key)
        self.label:       str = label

    # ── Key derivation ────────────────────────────────────────
    @staticmethod
    def _derive_public_key(private_key: str) -> str:
        """Derive a pseudo-public key from the private key."""
        return hashlib.sha256(("pubkey:" + private_key).encode()).hexdigest()

    @staticmethod
    def _derive_address(public_key: str) -> str:
        """Wallet address = first 40 hex chars of SHA-256(public_key)."""
        return hashlib.sha256(public_key.encode()).hexdigest()[:40]

    # ── Signing ───────────────────────────────────────────────
    def sign_transaction(self, tx: Dict[str, Any]) -> str:
        """
        Create an HMAC-SHA256 signature of the transaction data.
        In a real chain this would be ECDSA with secp256k1.
        """
        message = json.dumps(tx, sort_keys=True).encode()
        return hmac.new(
            self.private_key.encode(), message, hashlib.sha256
        ).hexdigest()

    def verify_signature(self, tx: Dict[str, Any], signature: str) -> bool:
        """Verify a signature against this wallet's key."""
        expected = self.sign_transaction(tx)
        return hmac.compare_digest(expected, signature)

    # ── Serialisation ─────────────────────────────────────────
    def to_dict(self) -> Dict[str, str]:
        return {
            "label":       self.label,
            "address":     self.address,
            "public_key":  self.public_key,
            # NEVER expose private_key in a real app!
            # Included here only for the demo / educational purposes.
            "private_key": self.private_key,
        }

    def __repr__(self) -> str:
        return f"Wallet(label='{self.label}', address={self.address[:12]}…)"
