# ⛓ BlockPy — Blockchain Network (Basic Level)

A complete, educational blockchain implementation in pure Python with a
REST API and a full-featured web explorer.

---

## What's Inside

| Component | Description |
|-----------|-------------|
| `core/block.py`      | Block with SHA-256 hashing |
| `core/blockchain.py` | Chain, Proof-of-Work, mining, validation |
| `core/wallet.py`     | Key generation, signing, address derivation |
| `core/node.py`       | P2P node with broadcasting & consensus |
| `api/app.py`         | Flask REST API (16 endpoints) |
| `frontend/index.html`| Block explorer web UI |
| `demo.py`            | CLI demo — no server needed |
| `tests/`             | 25+ unit tests |

---

## Quick Start

### 1. Install
```bash
pip install -r requirements.txt
```

### 2. CLI Demo (no server needed)
```bash
python demo.py
```

### 3. Start the API Server
```bash
python api/app.py
# → http://localhost:5000
```

### 4. Open the Block Explorer
Open `frontend/index.html` in your browser.

### 5. Run Tests
```bash
python -m pytest tests/ -v
# or
python tests/test_blockchain.py
```

---

## Project Structure

```
blockchain/
├── core/
│   ├── block.py         # Block: hash, PoW, serialisation
│   ├── blockchain.py    # Chain: mining, transactions, validation
│   ├── wallet.py        # Wallet: keys, address, signing
│   └── node.py          # Node: P2P, broadcast, consensus
├── api/
│   └── app.py           # Flask REST API
├── frontend/
│   └── index.html       # Block explorer (single HTML file)
├── tests/
│   └── test_blockchain.py
├── demo.py              # CLI demo
└── requirements.txt
```

---

## Core Concepts Implemented

### Proof-of-Work
Every block requires a hash starting with N leading zeros (difficulty=3).
The miner increments a nonce until the condition is satisfied.

```python
bc = Blockchain()
block = bc.mine_pending_transactions(miner_address)
print(block.hash)   # starts with "000..."
```

### Transactions
```python
bc.add_transaction(sender="alice_addr", recipient="bob_addr", amount=5.0)
bc.mine_pending_transactions(miner_address)  # confirms the tx
print(bc.get_balance("alice_addr"))
```

### Wallets
```python
wallet = Wallet(label="Alice")
print(wallet.address)     # 40-char hex address
sig = wallet.sign_transaction(tx)
wallet.verify_signature(tx, sig)   # → True
```

### Multi-Node Consensus
```python
node1 = Node("Node-1")
node2 = Node("Node-2")
node1.connect_peer(node2)
node1.mine_and_broadcast()   # Node-2 automatically gets the longer chain
```

### Chain Validation & Tamper Detection
```python
print(bc.is_valid_chain())          # True
bc.chain[1].transactions[0]["amount"] = 9999
print(bc.is_valid_chain())          # False — tampering detected!
```

---

## REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/` | Node info |
| GET  | `/chain` | Full blockchain |
| GET  | `/chain/valid` | Validate chain |
| POST | `/transactions/new` | Add transaction |
| GET  | `/transactions/pending` | Mempool |
| GET  | `/transactions/<addr>` | Address history |
| POST | `/mine` | Mine a block |
| POST | `/wallet/new` | Create wallet |
| GET  | `/wallet/<addr>/balance` | Get balance |
| GET  | `/wallets` | All wallets |
| GET  | `/stats` | Chain statistics |

---

## Mining a Block via API
```bash
# Create a wallet
curl -X POST http://localhost:5000/wallet/new \
  -H "Content-Type: application/json" \
  -d '{"label":"Alice"}'

# Send a transaction
curl -X POST http://localhost:5000/transactions/new \
  -H "Content-Type: application/json" \
  -d '{"sender":"<from_addr>","recipient":"<to_addr>","amount":3.0}'

# Mine the block
curl -X POST http://localhost:5000/mine \
  -H "Content-Type: application/json" \
  -d '{"miner_address":"<miner_addr>"}'
```
