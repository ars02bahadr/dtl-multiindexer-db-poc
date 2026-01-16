
## 1. API ile Test (curl/Swagger)

### 1.1 Swagger UI

Tarayicida ac: http://localhost:8000/swagger/

### 1.2 Demo Hesaplari Olustur
```bash
curl -X POST http://localhost:8000/health/seed
```

Beklenen cikti (ornek):
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

### 1.3 Hesaplari Listele

```bash
curl http://localhost:8000/accounts
```

### 1.4 Transfer Yap

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

Beklenen cikti (ornek):
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
  "message": "Transfer tamamlandi. Blockchain + IPFS + OpenCBDC kaydedildi."
}
```

### 1.5 Validator Loglarini Kontrol Et

```bash
# Tek validator logu
curl http://localhost:8000/nodes/validator-logs/validator1

# Tum validator loglarinin ozeti
curl http://localhost:8000/nodes/validator-logs
```

### 1.6 Transfer Loglarini Gor

```bash
curl http://localhost:8000/nodes/transfers
```

### 1.7 OpenCBDC Ledger Loglarini Gor

```bash
curl http://localhost:8000/nodes/ledger
```

### 1.8 Sistem Durumu

```bash
curl http://localhost:8000/health
```

---

## 2. Frontend ile Test

### 2.1 Frontend'i Ac

Tarayicida: http://localhost:5173

### 2.2 Demo Kullanicilari Olustur  
1. "Seed Demo Users" butonuna tikla
2. Alice, Bob, Charlie ve Admin hesaplari olusturulur

### 2.3 Transfer Yap
1. Validator sec: dropdown'dan validator1-4
2. Gonderen sec
3. Alici sec
4. Miktar gir
5. "Transfer Gonder" butonuna tikla

### 2.4 Sonuclari Gor

- Son Transfer paneli: TX Hash, Block Number, IPFS CID, Validator bilgisi
- Kullanicilar tablosu: guncellenen bakiyeler
- Validator Loglari: 4 validator'da transfer logu
- Islem Gecmisi: tum transfer'lerin listesi

---

## 3. Log Dosyalari

### 3.1 Log Dosyalari Nerede?

```
backend/logs/
  transfers.txt           # Genel transfer ozeti
  opencbdc_ledger.txt      # UTXO kayitlari
  dtl-validator-1.txt      # Validator 1 detayli log
  dtl-validator-2.txt      # Validator 2 detayli log
  dtl-validator-3.txt      # Validator 3 detayli log
  dtl-validator-4.txt      # Validator 4 detayli log
```

### 3.2 Log Dosyalarini Izle (Terminal)

```bash
# Validator 1 loglarini canli izle
tail -f backend/logs/dtl-validator-1.txt

# Transfer loglarini izle
tail -f backend/logs/transfers.txt

# Tum validator loglarini ayni anda izle
tail -f backend/logs/dtl-validator-*.txt
```

### 3.3 Log Formatlari

transfers.txt:
```
[2026-01-17 01:14:49] 0x00000000... -> 0x33333333...: 350 DTL (utxo: utxo_75ca29aa8a7)
```

opencbdc_ledger.txt:
```
[2026-01-16T22:14:49.290044] UTXO: utxo_75ca29aa8a78cc73 | 0x00000000... -> 0x33333333... | 350 DTL
```

dtl-validator-X.txt:
```
[2026-01-17 01:14:49.291] [INFO] >>> OUTGOING TRANSFER (from this node)
[2026-01-17 01:14:49.291] [INFO]   tx_hash: 0x20260116221449...
[2026-01-17 01:14:49.291] [INFO]   from: 0x00000000...
[2026-01-17 01:14:49.291] [INFO]   to: 0x33333333...
[2026-01-17 01:14:49.291] [INFO]   amount: 350 DTL
[2026-01-17 01:14:49.291] [INFO]   ipfs_cid: QmXgkqopQcTEutDgmxNJuPk6q6ubWetXVYH1QXKwRAN4qN
[2026-01-17 01:14:49.291] [INFO]   status: CONFIRMED
```

---

## 4. Ornek Senaryolar

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

### Senaryo B: Farkli Validator'lardan Transfer

```bash
# Validator 2 uzerinden transfer
curl -X POST http://localhost:8000/transactions/transfer \
  -H "Content-Type: application/json" \
  -d '{"from": "0x2222222222222222222222222222222222222222", "to": "0x3333333333333333333333333333333333333333", "amount": 50, "validator": "validator2"}'

# Validator 3 uzerinden transfer
curl -X POST http://localhost:8000/transactions/transfer \
  -H "Content-Type: application/json" \
  -d '{"from": "0x3333333333333333333333333333333333333333", "to": "0x1111111111111111111111111111111111111111", "amount": 25, "validator": "validator3"}'
```

### Senaryo C: Tum Loglari Karsilastir

```bash
# Her validator'un logunu goster (hepsi ayni transfer'i gormeli)
echo "=== Validator 1 ===" && curl -s http://localhost:8000/nodes/validator-logs/validator1 | jq '.logs[-5:]'
echo "=== Validator 2 ===" && curl -s http://localhost:8000/nodes/validator-logs/validator2 | jq '.logs[-5:]'
echo "=== Validator 3 ===" && curl -s http://localhost:8000/nodes/validator-logs/validator3 | jq '.logs[-5:]'
echo "=== Validator 4 ===" && curl -s http://localhost:8000/nodes/validator-logs/validator4 | jq '.logs[-5:]'
```

---

## 5. Troubleshooting

### Backend baslamiyor

```bash
# Port kullanimda mi?
# macOS/Linux:
#   lsof -i :8000
# Windows PowerShell:
#   netstat -ano | findstr :8000

# Onceki process'i oldur
# macOS/Linux:
#   pkill -f "python app.py"
# Windows PowerShell:
#   Get-Process python | Stop-Process
```

### Frontend backend'e baglanamiyor

1. Backend calisiyor mu: `curl http://localhost:8000/health`
2. CORS hatasi varsa backend'i yeniden baslat
3. Tarayici konsolundaki hata mesajlarini kontrol et (F12)

### Loglar gorunmuyor

1. Once transfer yap - loglar transfer sonrasi olusur
2. Log dizini var mi: `ls -la backend/logs/`
3. Backend'i yeniden baslat

### Validator'lar offline gorunuyor

1. Docker calisiyor mu: `docker ps`
2. Blockchain agini baslat: `cd infra && docker compose up -d`
3. Validator portlarini kontrol et: `curl http://localhost:8545`

---

## 6. Faydalı Komutlar

```bash
# Backend'i arka planda baslat
cd backend && python app.py &

# Frontend'i arka planda baslat
cd frontend && npm run dev &

# Tum loglari temizle
rm -f backend/logs/*.txt

# Ledger verisini sifirla
rm -f backend/data/opencbdc_ledger.json
```

---

## 7. Mimari Ozet

```
Frontend (Vue.js)
  -> POST /transactions/transfer

Backend (Flask)
  1) Bakiye kontrolu (OpenCBDC JSON Ledger)
  2) Blockchain'e yaz (Besu) -> tx_hash
  3) IPFS'e metadata -> ipfs_cid
  4) UTXO olustur (OpenCBDC)
  5) 4 validator loguna yaz

Validator Loglari
  - dtl-validator-1.txt
  - dtl-validator-2.txt
  - dtl-validator-3.txt
  - dtl-validator-4.txt
```

Tum validator'lar ayni transaction'i gorur = Merkezi olmayan dogrulama
