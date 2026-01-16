# DTL Multi-Indexer - Kullanım Kılavuzu

Bu belge projenin adım adım nasıl çalıştırılacağını ve test edileceğini açıklar.

## Hızlı Başlangıç

### Terminal 1: Backend

```bash
cd /Users/admin/Desktop/DTL/dtl-multiindexer-db-poc/backend
python app.py
```

### Terminal 2: Frontend

```bash
cd /Users/admin/Desktop/DTL/dtl-multiindexer-db-poc/frontend
npm install   # Sadece ilk sefer
npm run dev
```

### Erişim Linkleri

| Servis | URL |
|--------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/swagger/ |

---

## 1. Kurulum (Detaylı)

### 1.1 Gereksinimler

```bash
# Python versiyonu kontrol (3.9+ gerekli)
python --version

# Node.js versiyonu kontrol (18+ önerilir)
node --version

# Docker versiyonu kontrol (blockchain için)
docker --version
```

### 1.2 Blockchain Ağını Başlat (Opsiyonel)

Eğer gerçek blockchain bağlantısı istiyorsan:

```bash
cd infra
docker compose up -d

# Durumu kontrol et
docker ps
```

**Not:** Blockchain olmadan da çalışır - transfer'ler mock tx_hash ile yapılır.

### 1.3 Backend Kurulumu

```bash
cd backend

# Virtual environment (önerilir)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Başlat
python app.py
```

**Başarılı çıktı:**
```
╔══════════════════════════════════════════════════════════╗
║        DTL Multi-Indexer - OpenCBDC Mode                 ║
╠══════════════════════════════════════════════════════════╣
║  🔗 Storage: OpenCBDC UTXO Ledger (JSON)                 ║
║  🔐 Auth: Wallet Signature Verification                  ║
║  📊 Swagger: http://localhost:8000/swagger/              ║
║  ❌ PostgreSQL: NOT USED                                 ║
╚══════════════════════════════════════════════════════════╝
 * Running on http://0.0.0.0:8000
```

### 1.4 Frontend Kurulumu

**Yeni terminal aç:**

```bash
cd frontend
npm install
npm run dev
```

**Çıktı:**
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

---

## 2. API ile Test (curl/Swagger)

### 2.1 Swagger UI

Tarayıcıda aç: **http://localhost:8000/swagger/**

Tüm endpoint'leri görsel olarak test edebilirsin.

### 2.2 Demo Hesapları Oluştur

```bash
curl -X POST http://localhost:8000/health/seed
```

**Beklenen çıktı:**
```json
{
  "status": "seeded",
  "created": [
    {"address": "0x1111111111111111111111111111111111111111", "balance": 1000},
    {"address": "0x2222222222222222222222222222222222222222", "balance": 500},
    {"address": "0x3333333333333333333333333333333333333333", "balance": 250},
    {"address": "0x0000000000000000000000000000000000000001", "balance": 10000}
  ]
}
```

### 2.3 Hesapları Listele

```bash
curl http://localhost:8000/accounts
```

### 2.4 Transfer Yap

```bash
curl -X POST http://localhost:8000/transactions/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "from": "0x1111111111111111111111111111111111111111",
    "to": "0x2222222222222222222222222222222222222222",
    "amount": 100,
    "validator": "validator1"
  }'
```

**Beklenen çıktı:**
```json
{
  "status": "success",
  "tx_id": 1,
  "utxo_id": "utxo_abc123...",
  "sender": "0x1111111111111111111111111111111111111111",
  "receiver": "0x2222222222222222222222222222222222222222",
  "amount": "100",
  "sender_new_balance": "900",
  "receiver_new_balance": "600",
  "tx_hash": "0x...",
  "ipfs_cid": "Qm...",
  "block_number": 12345,
  "validator": "validator1",
  "message": "Transfer tamamlandı. Blockchain + IPFS + OpenCBDC kaydedildi."
}
```

### 2.5 Validator Loglarını Kontrol Et

```bash
# Tek validator logu
curl http://localhost:8000/nodes/validator-logs/validator1

# Tüm validator logları özeti
curl http://localhost:8000/nodes/validator-logs
```

### 2.6 Transfer Loglarını Gör

```bash
curl http://localhost:8000/nodes/transfers
```

### 2.7 OpenCBDC Ledger Loglarını Gör

```bash
curl http://localhost:8000/nodes/ledger
```

### 2.8 Sistem Durumu

```bash
curl http://localhost:8000/health
```

---

## 3. Frontend ile Test

### 3.1 Frontend'i Aç

Tarayıcıda: **http://localhost:5173**

### 3.2 Demo Kullanıcıları Oluştur

1. "🌱 Seed Demo Users" butonuna tıkla
2. Alice, Bob, Charlie ve Admin hesapları oluşturulacak

### 3.3 Transfer Yap

1. **Validator seç:** Dropdown'dan validator1-4 arasından seç
2. **Gönderen seç:** Dropdown'dan hesap seç
3. **Alıcı seç:** Dropdown'dan hedef hesap seç
4. **Miktar gir:** Transfer miktarı
5. **"💸 Transfer Gönder" butonuna tıkla**

### 3.4 Sonuçları Gör

Transfer sonrası:

- **Son Transfer paneli:** TX Hash, Block Number, IPFS CID, Validator bilgisi
- **Kullanıcılar tablosu:** Güncellenen bakiyeler
- **Validator Logları:** 4 validator'ın her birinde transfer logu
- **İşlem Geçmişi:** Tüm transfer'lerin listesi

### 3.5 Validator Sekmelerini Kullan

- Üstteki validator tab'larına tıklayarak her validator'ın durumunu gör
- 🟢 Online / 🔴 Offline durumu
- Block number'ları karşılaştır (sync durumu)

---

## 4. Log Dosyaları

### 4.1 Log Dosyaları Nerede?

```
backend/logs/
├── transfers.txt           # Genel transfer özeti
├── opencbdc_ledger.txt     # UTXO kayıtları
├── dtl-validator-1.txt     # Validator 1 detaylı log
├── dtl-validator-2.txt     # Validator 2 detaylı log
├── dtl-validator-3.txt     # Validator 3 detaylı log
└── dtl-validator-4.txt     # Validator 4 detaylı log
```

### 4.2 Log Dosyalarını İzle (Terminal)

```bash
# Validator 1 loglarını canlı izle
tail -f backend/logs/dtl-validator-1.txt

# Transfer loglarını izle
tail -f backend/logs/transfers.txt

# Tüm validator loglarını aynı anda izle
tail -f backend/logs/dtl-validator-*.txt
```

### 4.3 Log Formatları

**transfers.txt:**
```
[2026-01-17 01:14:49] 0x00000000... -> 0x33333333...: 350 DTL (utxo: utxo_75ca29aa8a7)
```

**opencbdc_ledger.txt:**
```
[2026-01-16T22:14:49.290044] UTXO: utxo_75ca29aa8a78cc73 | 0x00000000... -> 0x33333333... | 350 DTL
```

**dtl-validator-X.txt:**
```
[2026-01-17 01:14:49.291] [INFO] >>> OUTGOING TRANSFER (from this node)
[2026-01-17 01:14:49.291] [INFO]   tx_hash: 0x20260116221449...
[2026-01-17 01:14:49.291] [INFO]   from: 0x00000000...
[2026-01-17 01:14:49.291] [INFO]   to: 0x33333333...
[2026-01-17 01:14:49.291] [INFO]   amount: 350 DTL
[2026-01-17 01:14:49.291] [INFO]   ipfs_cid: QmXgkqopQcTEutDgmxNJuPk6q6ubWetXVYH1QXKwRAN4qN
[2026-01-17 01:14:49.291] [INFO]   status: CONFIRMED
```

### 4.4 Log Amaçları

| Log Dosyası | Amaç | Ne Zaman Yazılır |
|-------------|------|------------------|
| `transfers.txt` | Transfer özeti, scheduler tarafından | Her transfer + scheduler başlangıcı |
| `opencbdc_ledger.txt` | UTXO kayıtları | Her yeni UTXO oluşturulduğunda |
| `dtl-validator-X.txt` | Detaylı validator logları | Her transfer'de 4'üne de yazılır |

---

## 5. Örnek Senaryolar

### Senaryo A: Basit Transfer

```bash
# 1. Seed users
curl -X POST http://localhost:8000/health/seed

# 2. Alice'den Bob'a 100 DTL transfer
curl -X POST http://localhost:8000/transactions/transfer \
  -H "Content-Type: application/json" \
  -d '{"from": "0x1111111111111111111111111111111111111111", "to": "0x2222222222222222222222222222222222222222", "amount": 100, "validator": "validator1"}'

# 3. Bakiyeleri kontrol et
curl http://localhost:8000/accounts/0x1111111111111111111111111111111111111111/balance
curl http://localhost:8000/accounts/0x2222222222222222222222222222222222222222/balance
```

### Senaryo B: Farklı Validator'lardan Transfer

```bash
# Validator 2 üzerinden transfer
curl -X POST http://localhost:8000/transactions/transfer \
  -H "Content-Type: application/json" \
  -d '{"from": "0x2222222222222222222222222222222222222222", "to": "0x3333333333333333333333333333333333333333", "amount": 50, "validator": "validator2"}'

# Validator 3 üzerinden transfer
curl -X POST http://localhost:8000/transactions/transfer \
  -H "Content-Type: application/json" \
  -d '{"from": "0x3333333333333333333333333333333333333333", "to": "0x1111111111111111111111111111111111111111", "amount": 25, "validator": "validator3"}'
```

### Senaryo C: Tüm Logları Karşılaştır

```bash
# Her validator'ın logunu göster (hepsi aynı transfer'i görmeli)
echo "=== Validator 1 ===" && curl -s http://localhost:8000/nodes/validator-logs/validator1 | jq '.logs[-5:]'
echo "=== Validator 2 ===" && curl -s http://localhost:8000/nodes/validator-logs/validator2 | jq '.logs[-5:]'
echo "=== Validator 3 ===" && curl -s http://localhost:8000/nodes/validator-logs/validator3 | jq '.logs[-5:]'
echo "=== Validator 4 ===" && curl -s http://localhost:8000/nodes/validator-logs/validator4 | jq '.logs[-5:]'
```

---

## 6. Troubleshooting

### Backend başlamıyor

```bash
# Port kullanımda mı?
lsof -i :8000

# Önceki process'i öldür
pkill -f "python app.py"
```

### Frontend backend'e bağlanamıyor

1. Backend çalışıyor mu kontrol et: `curl http://localhost:8000/health`
2. CORS hatası varsa backend'i yeniden başlat
3. Tarayıcı konsolunda hata mesajını kontrol et (F12)

### Loglar görünmüyor

1. Önce transfer yap - loglar transfer sonrası oluşur
2. Log dizininin var olduğunu kontrol et: `ls -la backend/logs/`
3. Backend'i yeniden başlat

### Validator'lar offline görünüyor

1. Docker çalışıyor mu: `docker ps`
2. Blockchain ağını başlat: `cd infra && docker compose up -d`
3. Validator port'larını kontrol et: `curl http://localhost:8545`

---

## 7. Faydalı Komutlar

```bash
# Backend'i arka planda başlat
cd backend && python app.py &

# Frontend'i arka planda başlat
cd frontend && npm run dev &

# Tüm logları temizle
rm -f backend/logs/*.txt

# Ledger verisini sıfırla
rm -f backend/data/opencbdc_ledger.json

# Her şeyi yeniden başlat
pkill -f "python app.py"
pkill -f "npm run dev"
cd backend && python app.py &
cd frontend && npm run dev &
```

---

## 8. Mimari Özet

```
┌─────────────────────────────────────────────────────────────┐
│                      TRANSFER AKIŞI                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Frontend (Vue.js)                                          │
│        │                                                     │
│        ▼  POST /transactions/transfer                        │
│   ┌─────────────────────────────────────────────────┐       │
│   │              Flask Backend                       │       │
│   │                                                  │       │
│   │  1. Bakiye kontrolü (OpenCBDC JSON Ledger)      │       │
│   │  2. Blockchain'e yaz (Besu) → tx_hash           │       │
│   │  3. IPFS'e metadata → ipfs_cid                  │       │
│   │  4. UTXO oluştur (OpenCBDC)                     │       │
│   │  5. 4 validator loguna yaz                      │       │
│   │                                                  │       │
│   └─────────────────────────────────────────────────┘       │
│        │                                                     │
│        ▼                                                     │
│   ┌─────────────┬─────────────┬─────────────┬─────────────┐ │
│   │ Validator 1 │ Validator 2 │ Validator 3 │ Validator 4 │ │
│   │    .txt     │    .txt     │    .txt     │    .txt     │ │
│   └─────────────┴─────────────┴─────────────┴─────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Tüm validator'lar aynı transaction'ı görür = Merkezi Olmayan Doğrulama**
