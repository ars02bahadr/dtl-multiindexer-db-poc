# Digital Turkish Lira (DTL) - Project Verification Walkthrough

This document provides the step-by-step commands to run the DTL ecosystem.

## 1. Prerequisites

Ensure you have the following installed:

- Docker & Docker Compose
- Rust (stable)
- Node.js (LTS) & pnpm/npm
- simple-http-server (optional, for viewing logs if needed)

## 2. Start Infrastructure (Besu & IPFS)

Start the blockchain network and databases.

```bash
# From root directory
docker compose -f infra/compose.yaml up -d

# Verify containers are running
docker ps
# Expected: dtl-validator1, dtl-validator2..., dtl-ipfs, dtl-postgres, dtl-redis
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

## 6. End-to-End Test Scenarios

### Scenario A: Wallet Connection

1. Open Frontend.
2. Click "Connect Wallet".
3. Approve MetaMask connection (ensure MetaMask is connected to Localhost 8545 with Chain ID 1337).
4. **Verify**: Address and Balance (initially high if using genesis account) are displayed.

### Scenario B: Transfer

1. Enter recipient address (e.g., `0x627306090abab3a6e1400e9345bc60c78a8bef57`).
2. Enter amount.
3. Click Send.
4. **Verify**:
   - Backend logs show "submitted".
   - Toast/Status in UI says "Tx Hash: ...".
   - Besu logs (docker logs dtl-validator1) show transaction processing.

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

## 7. Troubleshooting

- **Besu Peering**: check `docker logs dtl-validator1` to see if peers are connected.
- **CORS**: If Frontend can't talk to Besu, check `rpc-http-cors-origins=["*"]` in `config.toml`.
- **Reset**: `docker compose -f infra/compose.yaml down -v` to wipe chain data.
