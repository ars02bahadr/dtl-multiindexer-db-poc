# DTL Multi-Indexer - OpenCBDC Mode

Digital Turkish Lira (DTL) merkezi olmayan doğrulama ve multi-indexer PoC projesi.

## Mimari

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DTL Multi-Indexer                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│   │  Validator1  │◄──►│  Validator2  │◄──►│  Validator3  │◄──►...       │
│   │  (Besu:8545) │    │  (Besu:8555) │    │  (Besu:8565) │              │
│   └──────┬───────┘    └──────────────┘    └──────────────┘              │
│          │                                                               │
│          ▼                                                               │
│   ┌──────────────────────────────────────────────────────────┐          │
│   │                    Flask Backend (:8000)                  │          │
│   │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐ │          │
│   │  │ REST API│  │Scheduler│  │ Event   │  │  Validator  │ │          │
│   │  │ Swagger │  │         │  │ Listener│  │   Logger    │ │          │
│   │  └─────────┘  └─────────┘  └─────────┘  └─────────────┘ │          │
│   └──────────────────────────────────────────────────────────┘          │
│          │                                                               │
│          ▼                                                               │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│   │   OpenCBDC   │    │     IPFS     │    │    Redis     │              │
│   │ JSON Ledger  │    │  (Metadata)  │    │   (Cache)    │              │
│   └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                                          │
│   ┌──────────────────────────────────────────────────────────┐          │
│   │                   Vue.js Frontend (:5173)                 │          │
│   │  - Wallet Bakiyeleri    - Transfer Formu                 │          │
│   │  - Validator Durumları  - Validator Logları              │          │
│   └──────────────────────────────────────────────────────────┘          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Teknolojiler

| Katman | Teknoloji | Açıklama |
|--------|-----------|----------|
| Blockchain | Hyperledger Besu (QBFT) | 4 Validator node, Byzantine fault tolerant |
| Backend | Python Flask + Flask-RESTX | REST API, Swagger UI |
| Storage | OpenCBDC JSON Ledger | UTXO-based, PostgreSQL YOK |
| Metadata | IPFS | Decentralized storage |
| Cache | Redis | Opsiyonel, performans için |
| Frontend | Vue 3 + Vite | Reactive UI |

## Gereksinimler

- **Docker & Docker Compose** (Blockchain için)
- **Python 3.9+** (Backend için)
- **Node.js 18+ & npm** (Frontend için)
- **Git**

## Kurulum

### 1. Projeyi Klonla

```bash
git clone <repo-url>
cd dtl-multiindexer-db-poc
```

### 2. Blockchain Ağını Başlat (Docker)

```bash
cd infra
docker compose up -d

# Konteynerların durumunu kontrol et
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Beklenen konteynerler:**
- `dtl-validator1` (port 8545)
- `dtl-validator2` (port 8555)
- `dtl-validator3` (port 8565)
- `dtl-validator4` (port 8575)
- `dtl-ipfs` (port 5001)
- `dtl-redis` (port 6379)

**Blockchain sağlık kontrolü:**
```bash
# Block number kontrol
curl -s -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Peer sayısı kontrol (3 olmalı)
curl -s -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"net_peerCount","params":[],"id":1}'
```

### 3. Backend'i Kur ve Başlat

```bash
cd backend

# Virtual environment oluştur (önerilir)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Backend'i başlat
python app.py
```

**Başarılı başlatma çıktısı:**
```
╔══════════════════════════════════════════════════════════╗
║        DTL Multi-Indexer - OpenCBDC Mode                 ║
╠══════════════════════════════════════════════════════════╣
║  🔗 Storage: OpenCBDC UTXO Ledger (JSON)                 ║
║  🔐 Auth: Wallet Signature Verification                  ║
║  📊 Swagger: http://localhost:8000/swagger/              ║
║  ❌ PostgreSQL: NOT USED                                 ║
╚══════════════════════════════════════════════════════════╝
```

### 4. Frontend'i Kur ve Başlat

**Yeni terminal aç:**
```bash
cd frontend

# Bağımlılıkları yükle
npm install

# Development server başlat
npm run dev
```

**Frontend URL:** http://localhost:5173

## Dosya Yapısı

```
dtl-multiindexer-db-poc/
├── backend/
│   ├── app.py                 # Ana Flask uygulaması
│   ├── swagger.py             # REST API endpoint'leri
│   ├── config.py              # Konfigürasyon
│   ├── extensions.py          # Redis extension
│   ├── requirements.txt       # Python bağımlılıkları
│   ├── data/
│   │   └── opencbdc_ledger.json   # UTXO Ledger (tüm veri)
│   ├── infra/
│   │   ├── opencbdc_storage.py    # UTXO storage engine
│   │   ├── blockchain.py          # Web3 blockchain client
│   │   ├── ipfs_client.py         # IPFS client
│   │   ├── validator_logger.py    # Validator log yazıcı
│   │   ├── scheduler.py           # Background job scheduler
│   │   ├── event_listener.py      # Blockchain event listener
│   │   └── wallet_auth.py         # Wallet signature auth
│   └── logs/
│       ├── transfers.txt          # Transfer log özeti
│       ├── opencbdc_ledger.txt    # UTXO log özeti
│       ├── dtl-validator-1.txt    # Validator 1 detaylı log
│       ├── dtl-validator-2.txt    # Validator 2 detaylı log
│       ├── dtl-validator-3.txt    # Validator 3 detaylı log
│       └── dtl-validator-4.txt    # Validator 4 detaylı log
├── frontend/
│   ├── src/
│   │   └── App.vue            # Ana Vue component
│   ├── package.json
│   └── vite.config.js
└── infra/
    ├── compose.yaml           # Docker Compose config
    └── besu/                   # Besu validator configs
```

## Log Dosyaları

| Dosya | İçerik | Kullanım |
|-------|--------|----------|
| `transfers.txt` | Transfer özeti (from → to: amount) | Scheduler tarafından yazılır |
| `opencbdc_ledger.txt` | UTXO kayıtları | Her UTXO oluşturulduğunda |
| `dtl-validator-X.txt` | Detaylı transfer logları | Her transfer'de 4 validator'a da yazılır |

**Log örneği (dtl-validator-1.txt):**
```
[2026-01-17 01:14:49.291] [INFO] >>> OUTGOING TRANSFER (from this node)
[2026-01-17 01:14:49.291] [INFO]   tx_hash: 0x20260116221449...
[2026-01-17 01:14:49.291] [INFO]   from: 0x00000000...
[2026-01-17 01:14:49.291] [INFO]   to: 0x33333333...
[2026-01-17 01:14:49.291] [INFO]   amount: 350 DTL
[2026-01-17 01:14:49.291] [INFO]   ipfs_cid: QmXgkqopQcTEutDgmxNJuPk6q6ubWetXVYH1QXKwRAN4qN
[2026-01-17 01:14:49.291] [INFO]   status: CONFIRMED
```

## API Endpoints

### Hesaplar
| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/accounts` | Tüm hesapları listele |
| GET | `/accounts/{address}` | Hesap detayı |
| GET | `/accounts/{address}/balance` | Bakiye sorgula |
| GET | `/accounts/{address}/transactions` | Hesap işlemleri |
| POST | `/accounts` | Yeni hesap oluştur |

### Transfer
| Method | Endpoint | Açıklama |
|--------|----------|----------|
| POST | `/transactions/transfer` | Transfer yap |
| GET | `/transactions` | Tüm işlemleri listele |

### Validator & Loglar
| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/nodes` | Validator durumları |
| GET | `/nodes/validator-logs` | Tüm validator log özeti |
| GET | `/nodes/validator-logs/{name}` | Belirli validator logu |
| GET | `/nodes/transfers` | transfers.txt içeriği |
| GET | `/nodes/ledger` | opencbdc_ledger.txt içeriği |

### Sistem
| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/health` | Sistem durumu |
| POST | `/health/seed` | Demo hesaplar oluştur |
| GET | `/ledger/stats` | Ledger istatistikleri |
| POST | `/ledger/mint` | Para bas (admin) |

## Transfer Akışı

```
1. Client → POST /transactions/transfer
   ↓
2. Bakiye kontrolü (OpenCBDC Ledger)
   ↓
3. Blockchain'e transaction yaz (Besu)
   ↓
4. IPFS'e metadata yükle
   ↓
5. OpenCBDC UTXO oluştur
   ↓
6. Tüm validator loglarına yaz
   ↓
7. Response → Client
```

## Environment Variables

```bash
# Backend (.env dosyası opsiyonel)
FLASK_ENV=development
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# Blockchain
BLOCKCHAIN_RPC_URL=http://localhost:8545
VALIDATOR1_URL=http://localhost:8545
VALIDATOR2_URL=http://localhost:8555
VALIDATOR3_URL=http://localhost:8565
VALIDATOR4_URL=http://localhost:8575

# IPFS
IPFS_API_URL=http://localhost:5001/api/v0

# Redis (opsiyonel)
REDIS_URL=redis://localhost:6379/0
```

## Troubleshooting

### Backend başlamıyor
```bash
# Port kullanımda mı kontrol et
lsof -i :8000

# Log dosyalarının yazılabilir olduğunu kontrol et
ls -la backend/logs/
```

### Validator'lara bağlanamıyor
```bash
# Docker konteynerları çalışıyor mu?
docker ps

# Validator1 log kontrol
docker logs dtl-validator1 --tail 50
```

### Frontend API'ye bağlanamıyor
- CORS hatası: Backend'in `CORS(app, resources={r"/*": {"origins": "*"}})` ayarını kontrol et
- Backend çalışıyor mu: http://localhost:8000/health

### Log dosyaları boş görünüyor
- Transfer yapıldıktan sonra loglar oluşur
- Swagger UI'dan `/health/seed` çağırıp demo hesap oluştur
- Sonra transfer yap

## Production Deployment

```bash
# Gunicorn ile çalıştır
cd backend
gunicorn wsgi:app -b 0.0.0.0:8000 -w 4

# veya Docker ile
docker build -t dtl-backend .
docker run -p 8000:8000 dtl-backend
```

## Lisans

MIT License
