"""
api/app.py
──────────
Flask REST API — exposes the blockchain over HTTP.
All responses are JSON.

Endpoints
─────────
GET  /                          — health + node info
GET  /chain                     — full chain
GET  /chain/valid               — is chain valid?
POST /transactions/new          — add transaction to mempool
GET  /transactions/pending      — list mempool
GET  /transactions/<address>    — history for an address
POST /mine                      — mine a block
POST /wallet/new                — create a new wallet
GET  /wallet/<address>/balance  — wallet balance
GET  /wallets                   — all known wallets
GET  /nodes                     — list peer nodes
POST /nodes/register            — register a peer (simulation)
POST /nodes/resolve             — trigger consensus
GET  /stats                     — chain statistics
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sys, os

# Make sure we can import from parent
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.blockchain import Blockchain
from core.wallet     import Wallet
from core.node       import Node

# ── App & node setup ─────────────────────────────────────────
app  = Flask(__name__)
CORS(app)

NODE_ID = "node-1"
node    = Node(NODE_ID, miner_label="Node-1 Miner")

# Pre-fund a genesis wallet so the demo has coins to send
GENESIS_WALLET = Wallet(label="Genesis")
node.chain.register_wallet(GENESIS_WALLET.address)
# Mine an initial block to give the genesis wallet its reward
node.chain.mine_pending_transactions(GENESIS_WALLET.address)

# Keep a registry of created wallets for the demo
wallets: dict[str, Wallet] = {
    GENESIS_WALLET.address: GENESIS_WALLET,
    node.wallet.address:    node.wallet,
}


# ── Helpers ───────────────────────────────────────────────────
def ok(data: dict, status: int = 200):
    return jsonify(data), status

def err(message: str, status: int = 400):
    return jsonify({"error": message}), status


# ── Routes ────────────────────────────────────────────────────
@app.get("/")
def index():
    return ok({
        "message":   "BlockPy Network Node",
        "node_id":   NODE_ID,
        "version":   "1.0.0",
        "endpoints": [
            "GET  /chain",
            "GET  /chain/valid",
            "POST /transactions/new",
            "GET  /transactions/pending",
            "GET  /transactions/<address>",
            "POST /mine",
            "POST /wallet/new",
            "GET  /wallet/<address>/balance",
            "GET  /wallets",
            "GET  /stats",
        ],
    })


# ── Chain ─────────────────────────────────────────────────────
@app.get("/chain")
def get_chain():
    bc = node.chain
    return ok({
        "length":     bc.height,
        "difficulty": bc.DIFFICULTY,
        "chain":      bc.chain_as_list(),
    })


@app.get("/chain/valid")
def chain_valid():
    valid = node.chain.is_valid_chain()
    return ok({"valid": valid, "length": node.chain.height})


# ── Transactions ──────────────────────────────────────────────
@app.post("/transactions/new")
def new_transaction():
    data = request.get_json() or {}
    required = ["sender", "recipient", "amount"]
    missing  = [f for f in required if f not in data]
    if missing:
        return err(f"Missing fields: {', '.join(missing)}")

    try:
        amount = float(data["amount"])
        tx = node.chain.add_transaction(
            sender    = data["sender"],
            recipient = data["recipient"],
            amount    = amount,
            memo      = data.get("memo", ""),
        )
        return ok({"message": "Transaction added to mempool", "transaction": tx}, 201)
    except ValueError as e:
        return err(str(e))


@app.get("/transactions/pending")
def pending_transactions():
    return ok({
        "count":        len(node.chain.pending_transactions),
        "transactions": node.chain.pending_transactions,
    })


@app.get("/transactions/<address>")
def transaction_history(address):
    txns = node.chain.get_transactions(address)
    return ok({"address": address, "count": len(txns), "transactions": txns})


# ── Mining ────────────────────────────────────────────────────
@app.post("/mine")
def mine():
    data          = request.get_json() or {}
    miner_address = data.get("miner_address", node.wallet.address)

    if not node.chain.pending_transactions:
        # Mining with no transactions still earns reward
        pass

    block = node.chain.mine_pending_transactions(miner_address)
    return ok({
        "message":       f"Block #{block.index} mined successfully!",
        "block":         block.to_dict(),
        "reward":        node.chain.MINING_REWARD,
        "miner_address": miner_address,
    }, 201)


# ── Wallets ───────────────────────────────────────────────────
@app.post("/wallet/new")
def new_wallet():
    data   = request.get_json() or {}
    label  = data.get("label", "")
    wallet = Wallet(label=label)
    wallets[wallet.address] = wallet
    node.chain.register_wallet(wallet.address)
    return ok({
        "message": "Wallet created",
        "wallet":  wallet.to_dict(),
    }, 201)


@app.get("/wallet/<address>/balance")
def wallet_balance(address):
    balance = node.chain.get_balance(address)
    return ok({
        "address": address,
        "balance": balance,
        "label":   wallets[address].label if address in wallets else "unknown",
    })


@app.get("/wallets")
def list_wallets():
    result = []
    for addr, w in wallets.items():
        result.append({
            "label":   w.label,
            "address": addr,
            "balance": node.chain.get_balance(addr),
        })
    # Include wallets seen in chain but not in registry
    for addr in node.chain.wallets:
        if addr not in wallets and addr != "NETWORK":
            result.append({
                "label":   "unknown",
                "address": addr,
                "balance": node.chain.get_balance(addr),
            })
    return ok({"wallets": result})


# ── Stats ─────────────────────────────────────────────────────
@app.get("/stats")
def stats():
    bc       = node.chain
    all_txns = sum(len(b.transactions) for b in bc.chain)
    total_supply = sum(
        tx["amount"]
        for block in bc.chain
        for tx in block.transactions
        if tx["type"] == "reward"
    )
    return ok({
        "node_id":          NODE_ID,
        "chain_height":     bc.height,
        "total_blocks":     bc.height,
        "total_transactions": all_txns,
        "pending_transactions": len(bc.pending_transactions),
        "difficulty":       bc.DIFFICULTY,
        "mining_reward":    bc.MINING_REWARD,
        "total_supply":     round(total_supply, 2),
        "is_valid":         bc.is_valid_chain(),
        "known_wallets":    len(wallets),
    })


# ── Nodes / Consensus ─────────────────────────────────────────
@app.get("/nodes")
def list_nodes():
    return ok({"node_id": NODE_ID, "peers": [p.node_id for p in node.peers]})


if __name__ == "__main__":
    print("\n  ⛓  BlockPy Network Node running on http://localhost:5000")
    print("  📖  Interactive docs: open frontend/index.html in your browser\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
