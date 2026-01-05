# Digital Turkish Lira (DTL) - Project Verification Walkthrough

This document provides the step-by-step commands to run the DTL ecosystem.

## 1. Prerequisites

Ensure you have the following installed:

- Docker & Docker Compose
- Rust (stable)
- Node.js (LTS) & pnpm/npm
- Go 1.21+ (optional, for local scheduler development)

## 2. Start Infrastructure (Besu, IPFS, Databases, Scheduler)

Start the blockchain network, databases, and monitoring services.

```bash
# From infra directory
cd infra
docker compose up -d

# Verify all containers are running
docker ps --format "table {{.Names}}\t{{.Status}}"
```

**Expected containers:**
- `dtl-validator1` through `dtl-validator4` - Besu QBFT validators
- `dtl-ipfs` - IPFS node for decentralized storage
- `dtl-db` - PostgreSQL database
- `dtl-redis` - Redis cache
- `dtl-scheduler` - Go-based blockchain monitor

### Verify Blockchain Health

```bash
# Check validator1 is producing blocks
curl -s -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Check peer connections (should be 3)
curl -s -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"net_peerCount","params":[],"id":1}'
```

## 3. Deploy Smart Contracts

Deploy the `MoneyToken` to the local Besu network.

```bash
cd blockchain
npm install
# Deploy to local Besu network (ensure localhost:8545 is reachable)
npx hardhat run scripts/deploy.ts --network besu
```

_Note the deployed contract address from the output._

## 4. Run Backend Services

Start the Actix-web API and Event Listener.

### API (Terminal 1)

```bash
cd backend
# Set env vars if needed, defaults are set in code for localhost
cargo run -p dtl-api
```

_Server runs at http://localhost:8080_

### Event Listener (Terminal 2)

```bash
cd backend
cargo run -p dtl-event-listener
```

## 5. Run Frontend

Start the Vue.js Wallet application.

```bash
cd frontend
npm install
npm run dev
```

_Access at http://localhost:5173_ (or port shown).

## 6. Monitor Blockchain with Scheduler

The Go scheduler automatically monitors the blockchain every 2 minutes and logs reports.

### View Scheduler Logs

```bash
# Real-time Docker logs
docker logs -f dtl-scheduler

# Or view the report file
tail -f scheduler/logs/blockchain_report.txt
```

### Scheduler Output Example

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  📅 BESU BLOCKCHAIN RAPORU - 2026-01-05 17:35:33                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  📦 GÜNCEL BLOK NUMARASI: 3230                                               ║
║  👥 BAĞLI PEER SAYISI: 3                                                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  💸 SON TRANSFER İŞLEMLERİ (Son 10 blok):                                    ║
║  🪙 TOKEN TRANSFER #1                                                        ║
║     Gönderen: 0xa197...5585                                                  ║
║     Alan    : 0x6273...ef57                                                  ║
║     Miktar  : 500 DTL                                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### Configure Scheduler Interval

Edit `infra/compose.yaml` to change the interval:

```yaml
scheduler:
  environment:
    - SCHEDULER_INTERVAL=10s  # Options: 10s, 1m, 2m, 5m, etc.
```

Then restart: `docker compose up -d scheduler`

## 7. End-to-End Test Scenarios

### Scenario A: Wallet Connection

1. Open Frontend.
2. Click "Connect Wallet".
3. Approve MetaMask connection (ensure MetaMask is connected to Localhost 8545 with Chain ID 1337).
4. **Verify**: Address and Balance (initially high if using genesis account) are displayed.

### Scenario B: Transfer with Scheduler Monitoring

1. Enter recipient address (e.g., `0x627306090abab3a6e1400e9345bc60c78a8bef57`).
2. Enter amount (e.g., 500).
3. Click Send.
4. **Verify**:
   - Backend logs show "submitted".
   - Toast/Status in UI says "Tx Hash: ...".
   - Besu logs (`docker logs dtl-validator1`) show transaction processing.
   - **Scheduler report** shows the transfer within 2 minutes:
     ```
     ║  🪙 TOKEN TRANSFER #1                                                        ║
     ║     Gönderen: 0xa197...5585                                                  ║
     ║     Alan    : 0x6273...ef57                                                  ║
     ║     Miktar  : 500 DTL                                                        ║
     ```

### Scenario C: SDK Consensus (Code Check)

The SDK located in `sdk/src/index.ts` implements the "Trust Majority" logic.

```typescript
// Pseudocode usage
const client = new MultiIndexerClient([
  "http://indexer1/api",
  "http://indexer2/api",
  "http://indexer3/api",
]);
const balance = await client.query("/balance/0x123...");
```

## 8. Troubleshooting

### Besu Issues

- **Validators not starting**: Check genesis.json extraData is properly RLP-encoded with 4 validator addresses.
- **No peers**: Verify static-nodes.json has correct enode URLs with public keys.
- **RPC 403 Forbidden**: Ensure `--host-allowlist=*` is set in validator1 command.

### Scheduler Issues

- **"Error getting block number"**: Validator might not be ready. Wait a few seconds and restart scheduler.
- **Transfers not showing**: Scheduler only checks last 10 blocks. If transfer was earlier, it won't appear.

### General

- **Besu Peering**: `docker logs dtl-validator1` to see if peers are connected.
- **CORS**: If Frontend can't talk to Besu, check `rpc-http-cors-origins=["*"]` in config.toml.
- **Reset Everything**:
  ```bash
  cd infra
  docker compose down -v
  docker compose up -d
  ```

## 9. Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DTL Ecosystem                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │  Validator1  │◄──►│  Validator2  │◄──►│  Validator3  │◄──►│ Validator4 │ │
│  │   (Besu)     │    │   (Besu)     │    │   (Besu)     │    │  (Besu)    │ │
│  └──────┬───────┘    └──────────────┘    └──────────────┘    └────────────┘ │
│         │ RPC:8545                                                           │
│         ▼                                                                    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │  Scheduler   │    │ Event        │    │   Frontend   │                   │
│  │   (Go)       │    │ Listener     │    │   (Vue.js)   │                   │
│  │ ⏱️ 2min      │    │ (Rust)       │    │              │                   │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘                   │
│         │                   │                                                │
│         ▼                   ▼                                                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │ Report TXT   │    │  PostgreSQL  │    │    Redis     │                   │
│  │ 📄           │    │  💾          │    │    ⚡        │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│                                                                              │
│  ┌──────────────┐                                                           │
│  │    IPFS      │  Decentralized Storage                                    │
│  │    📦        │                                                           │
│  └──────────────┘                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```
