"""
tests/test_blockchain.py
────────────────────────
Unit tests covering:
  • Block creation & hashing
  • Blockchain genesis
  • Proof-of-Work
  • Transaction validation
  • Mining & rewards
  • Chain validation & tamper detection
  • Wallet creation & signing
  • Multi-node consensus
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import unittest
from core.block      import Block
from core.blockchain import Blockchain
from core.wallet     import Wallet
from core.node       import Node


class TestBlock(unittest.TestCase):

    def setUp(self):
        self.block = Block(index=1, transactions=[{"test": True}],
                           previous_hash="abc123")

    def test_hash_is_string(self):
        self.assertIsInstance(self.block.hash, str)
        self.assertEqual(len(self.block.hash), 64)

    def test_hash_changes_with_nonce(self):
        h1 = self.block.compute_hash()
        self.block.nonce += 1
        h2 = self.block.compute_hash()
        self.assertNotEqual(h1, h2)

    def test_to_dict_has_required_keys(self):
        d = self.block.to_dict()
        for key in ("index", "timestamp", "transactions",
                    "previous_hash", "nonce", "hash"):
            self.assertIn(key, d)

    def test_from_dict_round_trip(self):
        d  = self.block.to_dict()
        b2 = Block.from_dict(d)
        self.assertEqual(self.block.hash,  b2.hash)
        self.assertEqual(self.block.index, b2.index)


class TestBlockchain(unittest.TestCase):

    def setUp(self):
        self.bc = Blockchain()

    def test_genesis_block_exists(self):
        self.assertEqual(len(self.bc.chain), 1)
        self.assertEqual(self.bc.chain[0].index, 0)

    def test_genesis_block_previous_hash(self):
        self.assertEqual(self.bc.chain[0].previous_hash, "0" * 64)

    def test_chain_is_valid_at_start(self):
        self.assertTrue(self.bc.is_valid_chain())

    def test_mine_creates_block(self):
        self.bc.mine_pending_transactions("miner-addr")
        self.assertEqual(len(self.bc.chain), 2)

    def test_mined_block_satisfies_difficulty(self):
        block = self.bc.mine_pending_transactions("miner-addr")
        self.assertTrue(block.hash.startswith("0" * self.bc.DIFFICULTY))

    def test_mining_reward_credited(self):
        self.bc.mine_pending_transactions("miner-addr")
        balance = self.bc.get_balance("miner-addr")
        self.assertEqual(balance, self.bc.MINING_REWARD)

    def test_add_transaction_to_mempool(self):
        # Fund first
        self.bc.mine_pending_transactions("alice")
        self.bc.add_transaction("alice", "bob", 3.0)
        self.assertEqual(len(self.bc.pending_transactions), 1)

    def test_transaction_updates_balances(self):
        self.bc.mine_pending_transactions("alice")
        self.bc.add_transaction("alice", "bob", 4.0)
        self.bc.mine_pending_transactions("miner")
        self.assertAlmostEqual(self.bc.get_balance("alice"),
                               self.bc.MINING_REWARD - 4.0)
        self.assertAlmostEqual(self.bc.get_balance("bob"), 4.0)

    def test_insufficient_funds_raises(self):
        with self.assertRaises(ValueError):
            self.bc.add_transaction("broke-addr", "bob", 999.0)

    def test_zero_amount_raises(self):
        with self.assertRaises(ValueError):
            self.bc.add_transaction("alice", "bob", 0)

    def test_tampered_hash_invalidates_chain(self):
        self.bc.mine_pending_transactions("miner")
        self.bc.chain[1].transactions[0]["amount"] = 999999
        self.assertFalse(self.bc.is_valid_chain())

    def test_tampered_previous_hash_invalidates(self):
        self.bc.mine_pending_transactions("miner")
        self.bc.chain[1].previous_hash = "0" * 64
        self.assertFalse(self.bc.is_valid_chain())

    def test_get_transactions_history(self):
        self.bc.mine_pending_transactions("alice")
        self.bc.add_transaction("alice", "bob", 2.0)
        self.bc.mine_pending_transactions("miner")
        history = self.bc.get_transactions("alice")
        self.assertTrue(len(history) > 0)

    def test_replace_chain_with_longer(self):
        longer_bc = Blockchain()
        longer_bc.mine_pending_transactions("x")
        longer_bc.mine_pending_transactions("x")
        replaced = self.bc.replace_chain(longer_bc.chain_as_list())
        self.assertTrue(replaced)
        self.assertEqual(self.bc.height, longer_bc.height)

    def test_replace_chain_shorter_rejected(self):
        self.bc.mine_pending_transactions("x")
        shorter_bc = Blockchain()
        replaced = self.bc.replace_chain(shorter_bc.chain_as_list())
        self.assertFalse(replaced)


class TestWallet(unittest.TestCase):

    def setUp(self):
        self.wallet = Wallet(label="Test")

    def test_address_is_40_chars(self):
        self.assertEqual(len(self.wallet.address), 40)

    def test_two_wallets_have_different_addresses(self):
        w2 = Wallet()
        self.assertNotEqual(self.wallet.address, w2.address)

    def test_same_private_key_same_address(self):
        w2 = Wallet(private_key=self.wallet.private_key)
        self.assertEqual(self.wallet.address, w2.address)

    def test_sign_and_verify(self):
        tx  = {"sender": self.wallet.address, "recipient": "bob", "amount": 5}
        sig = self.wallet.sign_transaction(tx)
        self.assertTrue(self.wallet.verify_signature(tx, sig))

    def test_bad_signature_fails(self):
        tx  = {"sender": self.wallet.address, "recipient": "bob", "amount": 5}
        self.assertFalse(self.wallet.verify_signature(tx, "badsig"))

    def test_to_dict_has_keys(self):
        d = self.wallet.to_dict()
        for key in ("address", "public_key", "private_key", "label"):
            self.assertIn(key, d)


class TestNode(unittest.TestCase):

    def setUp(self):
        self.node_a = Node("A")
        self.node_b = Node("B")

    def test_node_has_chain(self):
        self.assertIsNotNone(self.node_a.chain)

    def test_connect_peers(self):
        self.node_a.connect_peer(self.node_b)
        self.assertIn(self.node_b, self.node_a.peers)
        self.assertIn(self.node_a, self.node_b.peers)

    def test_mine_and_broadcast(self):
        self.node_a.connect_peer(self.node_b)
        self.node_a.mine_and_broadcast()
        # After broadcast node_b should have same chain height
        self.assertEqual(self.node_a.chain.height, self.node_b.chain.height)

    def test_consensus_adopts_longer_chain(self):
        self.node_a.connect_peer(self.node_b)
        # Node A mines 3 blocks
        for _ in range(3):
            self.node_a.mine_and_broadcast()
        # Node B should have synced
        self.assertEqual(self.node_b.chain.height, self.node_a.chain.height)

    def test_status_dict(self):
        status = self.node_a.status()
        for key in ("node_id", "chain_height", "chain_valid", "pending_txns"):
            self.assertIn(key, status)


if __name__ == "__main__":
    unittest.main(verbosity=2)
