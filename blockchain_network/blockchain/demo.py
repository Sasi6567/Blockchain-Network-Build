"""
demo.py
───────
Interactive CLI demo of BlockPy — runs entirely in the terminal,
no web server needed.

Shows:
  1. Wallet creation
  2. Mining (Proof-of-Work)
  3. Sending transactions
  4. Chain validation & tamper detection
  5. Multi-node consensus
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from core.blockchain import Blockchain
from core.wallet     import Wallet
from core.node       import Node

CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def header(title: str):
    print(f"\n{BOLD}{CYAN}{'─'*55}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*55}{RESET}")


def ok(msg: str):   print(f"  {GREEN}✓{RESET}  {msg}")
def info(msg: str): print(f"  {YELLOW}ℹ{RESET}  {msg}")
def bad(msg: str):  print(f"  {RED}✗{RESET}  {msg}")


def print_block(b):
    print(f"    Block #{b.index}")
    print(f"      Hash:      {b.hash[:20]}…")
    print(f"      Prev Hash: {b.previous_hash[:20]}…")
    print(f"      Nonce:     {b.nonce}")
    print(f"      Txns:      {len(b.transactions)}")


def main():
    print(f"\n{BOLD}{'='*55}")
    print("   ⛓  BlockPy — Blockchain Demo")
    print(f"{'='*55}{RESET}")

    # ── 1. Create Wallets ─────────────────────────────────────
    header("1. Creating Wallets")
    alice  = Wallet(label="Alice")
    bob    = Wallet(label="Bob")
    carol  = Wallet(label="Carol")
    miner  = Wallet(label="Miner")

    for w in (alice, bob, carol, miner):
        ok(f"{w.label:<8}  {w.address}")

    # ── 2. Start Blockchain ───────────────────────────────────
    header("2. Initialising Blockchain")
    bc = Blockchain()
    info(f"Genesis block created.  Hash: {bc.chain[0].hash[:20]}…")
    info(f"Difficulty: {bc.DIFFICULTY} leading zeros  |  Reward: {bc.MINING_REWARD} coins/block")

    # ── 3. Mine First Block (funds Alice) ─────────────────────
    header("3. Mining Block #1  →  Alice earns reward")
    t0    = time.time()
    block = bc.mine_pending_transactions(alice.address)
    elapsed = time.time() - t0
    print_block(block)
    ok(f"Mined in {elapsed:.3f}s  (nonce={block.nonce})")
    ok(f"Alice balance: {bc.get_balance(alice.address):.2f} coins")

    # ── 4. Transactions ───────────────────────────────────────
    header("4. Adding Transactions to Mempool")
    bc.add_transaction(alice.address,  bob.address,   3.0, memo="Lunch money")
    bc.add_transaction(alice.address,  carol.address, 2.0, memo="Books")
    info(f"Pending transactions: {len(bc.pending_transactions)}")
    for tx in bc.pending_transactions:
        info(f"  {tx['sender'][:8]}… → {tx['recipient'][:8]}…  "
             f"{tx['amount']:.2f} coins  [{tx.get('memo','')}]")

    # ── 5. Mine Block #2 ──────────────────────────────────────
    header("5. Mining Block #2  →  Miner earns reward")
    t0    = time.time()
    block = bc.mine_pending_transactions(miner.address)
    elapsed = time.time() - t0
    print_block(block)
    ok(f"Mined in {elapsed:.3f}s  (nonce={block.nonce})")

    # ── 6. Balances ───────────────────────────────────────────
    header("6. Wallet Balances")
    for w in (alice, bob, carol, miner):
        bal = bc.get_balance(w.address)
        bar = "█" * int(bal)
        ok(f"{w.label:<8}  {bal:6.2f} coins  {bar}")

    # ── 7. Chain Validation ───────────────────────────────────
    header("7. Chain Validation")
    valid = bc.is_valid_chain()
    ok(f"Chain is valid: {valid}  (height={bc.height})")

    # ── 8. Tamper Detection ───────────────────────────────────
    header("8. Tamper Detection — modifying a transaction")
    original = bc.chain[2].transactions[0]["amount"]
    bc.chain[2].transactions[0]["amount"] = 9999.99
    valid_after = bc.is_valid_chain()
    bad(f"After tampering:  chain valid = {valid_after}  ← correctly INVALID")
    # Restore
    bc.chain[2].transactions[0]["amount"] = original
    ok(f"After restoring:  chain valid = {bc.is_valid_chain()}")

    # ── 9. Transaction History ────────────────────────────────
    header("9. Alice's Transaction History")
    history = bc.get_transactions(alice.address)
    for h in history:
        direction = "received" if h["recipient"] == alice.address else "sent"
        ok(f"Block #{h['block_index']}  {direction:<8}  {h['amount']:.2f} coins"
           + (f"  [{h['memo']}]" if h.get("memo") else ""))

    # ── 10. Wallet Signing ────────────────────────────────────
    header("10. Wallet Signing & Verification")
    tx  = {"sender": alice.address, "recipient": bob.address, "amount": 1.0}
    sig = alice.sign_transaction(tx)
    ok(f"Signature: {sig[:32]}…")
    ok(f"Verification (Alice's key): {alice.verify_signature(tx, sig)}")
    bad(f"Verification (Bob's key):   {bob.verify_signature(tx, sig)}  ← correctly INVALID")

    # ── 11. Multi-Node Network ────────────────────────────────
    header("11. Multi-Node Network & Consensus")
    node1 = Node("Node-1")
    node2 = Node("Node-2")
    node3 = Node("Node-3")

    node1.connect_peer(node2)
    node2.connect_peer(node3)

    info("Topology: Node-1 ── Node-2 ── Node-3")
    info(f"Initial heights: {node1.chain.height}, {node2.chain.height}, {node3.chain.height}")

    # Node-1 mines 3 blocks and broadcasts
    for i in range(3):
        node1.mine_and_broadcast()

    info(f"After Node-1 mines 3 blocks:")
    info(f"  Node-1 height: {node1.chain.height}")
    info(f"  Node-2 height: {node2.chain.height}")
    info(f"  Node-3 height: {node3.chain.height}")

    # Node-3 syncs manually (not directly connected to Node-1)
    node3.sync()
    info(f"  Node-3 after sync: {node3.chain.height}")

    all_same = (node1.chain.height == node2.chain.height == node3.chain.height)
    if all_same:
        ok("All nodes are in consensus ✓")
    else:
        bad("Nodes out of sync!")

    # ── Summary ───────────────────────────────────────────────
    header("Summary")
    total_supply = sum(
        tx["amount"]
        for block in bc.chain
        for tx in block.transactions
        if tx["type"] == "reward"
    )
    info(f"Chain height:        {bc.height}")
    info(f"Total transactions:  {sum(len(b.transactions) for b in bc.chain)}")
    info(f"Total coin supply:   {total_supply:.2f} coins")
    info(f"Chain valid:         {bc.is_valid_chain()}")
    info(f"Difficulty:          {bc.DIFFICULTY}")

    print(f"\n{BOLD}{GREEN}  ✅  Demo complete!{RESET}\n")
    print("  To start the API server:  python api/app.py")
    print("  To run tests:             python -m pytest tests/ -v\n")


if __name__ == "__main__":
    main()
