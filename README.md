# Dijital Türk Lirası (DTL) - Multi-Indexer DB PoC

Bu proje, **Dijital Türk Lirası (DTL)** ekosistemi için geliştirilmiş kapsamlı bir **Proof of Concept (Kavram Kanıtı)** çalışmasıdır. Proje, merkeziyetsiz bir blokzinciri ağı, olay tabanlı (event-driven) bir arka uç, modern bir kullanıcı arayüzü, akıllı veri doğrulama mekanizmalarını ve **OpenCBDC entegrasyonunu** içerir.

## ✨ Son Güncellemeler

- ✅ **OpenCBDC Entegrasyonu:** Scheduler artık ERC20 transferlerini otomatik olarak CBDC sistemine aktarıyor
- ✅ **Kod Yeniden Yapılandırma:** Scheduler modüler hale getirildi (main.go, model.go, payment.go)
- ✅ **Akıllı Loglama:** Sadece gerçek transfer olduğunda log dosyasına yazılıyor
- ✅ **Docker Desteği:** Tüm sistem container'larda çalışabiliyor
- ✅ **Gelişmiş Monitoring:** Son 30 blok kontrolü, detaylı CBDC raporları

## 🏗 Proje Mimarisi

Sistem aşağıdaki temel bileşenlerden oluşur:

### 1. Blokzinciri Ağı (Hyperledger Besu)

Özel bir konsorsiyum blokzinciri olarak kurgulanmıştır.

- **Node Yapısı:** 4 Validator Node (Doğrulayıcı Düğüm)
- **Konsensüs:** QBFT (Quorum Byzantine Fault Tolerance) - Kurumsal ve hızlı mutabakat sağlar.
- **Smart Contracts:** `MoneyToken` gibi temel varlık sözleşmelerini çalıştırır.

### 2. Arka Uç (Backend - Rust)

Yüksek performanslı ve güvenli bir yapı için **Rust** dili kullanılmıştır. Workspace yapısında organize edilmiştir:

- **`api`**: Dış dünya ile iletişim kuran Actix-web tabanlı REST API sunucusu.
- **`event-listener`**: Blokzincirindeki olayları (transferler, onaylar vb.) dinleyen ve veritabanına işleyen servis.
- **`domain`**: Projenin kalbini oluşturan veri modelleri ve iş kuralları.
- **`infra`**: Veritabanı ve blokzinciri bağlantılarını yöneten altyapı katmanı.

### 3. Ön Yüz (Frontend - Vue.js)

Kullanıcıların cüzdanlarını bağlayıp işlem yapabildikleri arayüz.

- **Teknoloji:** Vue 3 + Vite.
- **Web3 Entegrasyonu:** `ethers.js` ile cüzdan (MetaMask vb.) bağlantısı ve işlem imzalama.

### 4. Veri ve Depolama

- **PostgreSQL**: İşlenen blokzinciri verilerinin (kullanıcı bakiyeleri, işlem geçmişi) tutulduğu ana veritabanı.
- **Redis**: Hızlı veri erişimi ve önbellekleme için kullanılır.
- **IPFS**: Merkeziyetsiz dosya depolama sistemi (örn. dokümanlar veya metadata için).

### 5. Scheduler (Go - Hangfire Benzeri) + OpenCBDC Entegrasyonu

Blockchain ağını periyodik olarak izleyen ve raporlayan servis. Şimdi **OpenCBDC** entegrasyonu ile gerçek CBDC transferlerini de destekler.

- **Teknoloji:** Go 1.21, Alpine Linux tabanlı minimal Docker image.
- **Özellikler:**
  - Her 30 saniyede bir Besu blockchain'i sorgular
  - Blok numarası, validator bilgisi, peer sayısı takibi
  - ERC20 token transferlerini tespit eder ve decode eder
  - **OpenCBDC entegrasyonu:** Token transferlerini CBDC sistemine aktarır
  - Detaylı raporları TXT dosyasına yazar
  - "A kişisi B kişisine X DTL gönderdi" formatında okunabilir çıktı
  - **Akıllı loglama:** Sadece gerçek transfer olduğunda dosyaya yazar

#### Dosya Yapısı:
```
scheduler/
├── main.go          # Ana scheduler döngüsü ve blockchain RPC çağrıları
├── model.go         # Tüm struct tanımları (JSONRPC, Transaction, UTXO vb.)
├── payment.go       # OpenCBDC client'ları ve CBDC transfer işlemleri
├── Dockerfile       # Multi-stage build
└── logs/
    ├── blockchain_report.txt  # Blockchain transfer logları
    └── opencbdc_report.txt    # CBDC işlem detayları
```

#### OpenCBDC Entegrasyonu:
- **HTTP Client:** Gerçek OpenCBDC API'sine bağlanır
- **Mock Client:** Geliştirme için dahili simülasyon
- **UTXO Modeli:** Bitcoin benzeri transaction yapısı
- **Coin Selection:** Transfer için uygun UTXO'ları seçer
- **Transaction Broadcasting:** CBDC ağında transfer yayınlar

### 6. OpenCBDC Entegrasyonu

**Central Bank Digital Currency (CBDC)** sistemi entegrasyonu.

- **UTXO Modeli:** Bitcoin benzeri transaction yapısı
- **HTTP API:** Gerçek OpenCBDC node'una bağlanır
- **Mock Client:** Geliştirme ortamı için simülasyon
- **Coin Selection:** Transfer için optimal UTXO seçimi
- **Transaction Broadcasting:** CBDC ağında transfer yayınlama

### 7. SDK (Multi-Indexer Consensus)

- **Güven Mekanizması**: İstemci tarafında "Trust Majority" (Çoğunluğa Güven) mantığıyla çalışan bir TypeScript kütüphanesi. Farklı indexer servislerinden gelen verileri çapraz doğrulayarak güvenliği artırır.

---

## 📂 Detaylı Dosya ve Proje Yapısı

Aşağıda projenin tüm klasörleri ve içerdikleri önemli dosyaların amaçları detaylıca açıklanmıştır.

```
dtl-multiindexer-db-poc/
├── 📁 backend/             # Rust Workspace (Tüm arka uç servisleri)
├── 📁 frontend/            # Vue.js Cüzdan Uygulaması
├── 📁 blockchain/          # Akıllı Kontratlar (Hardhat)
├── 📁 scheduler/           # Go Blockchain İzleme + OpenCBDC Servisi
├── 📁 sdk/                 # Client-side Doğrulama Kütüphanesi
├── 📁 infra/               # DevOps ve Sistem Kurulum Dosyaları
└── 📄 docker-compose.yaml  # Orkestrasyon dosyası
```

### 1. 🦀 Backend (Rust)

Güvenlik ve perfromans için Rust dili kullanılmıştır. `Cargo workspace` özelliği ile birden fazla paket (crate) modüler olarak yönetilir.

#### `backend/api` (REST API Sunucusu)

Bu modül dış dünyadan gelen HTTP isteklerini karşılar.

- **`src/main.rs`**: Uygulamanın giriş noktasıdır. `actix-web` sunucusunu başlatır, veritabanı havuzunu (`infra` katmanından alarak) `App` state'ine ekler ve rotaları tanımlar.
- **`src/auth.rs`**: JWT (JSON Web Token) tabanlı kimlik doğrulama işlemlerini yapar. Token oluşturma (`create_token`) ve doğrulama (`validate_token`) fonksiyonlarını barındırır.
- **`src/handlers.rs`**: API uç noktalarının (endpoints) iş mantığını içerir. Örneğin `transfer` fonksiyonu, gelen para transferi isteğini karşılar ve bir sonraki adıma (örn. kuyruğa yazma veya blokzincirine iletme) yönlendirir.

#### `backend/event-listener` (Olay Dinleyici)

Blokzincirinde gerçekleşen işlemleri takip eder ve veritabanıyla senkronize eder.

- **`src/main.rs`**: Besu node'una WebSocket (`ws://`) üzerinden bağlanır. `MoneyToken` kontratındaki olayları (event) filtreler ve yakaladığı her log kaydını işleyerek PostgreSQL veritabanına yazar. Bu, kullanıcının bakiyesini sorgularken blokzincirini değil, hızlı veritabanını kullanabilmemizi sağlar (Indexing).

#### `backend/infra` (Altyapı Katmanı)

Diğer servislerin dış sistemlere (Veritabanı, Blockchain) erişmesini sağlayan köprü katmanıdır.

- **`src/lib.rs`**: Bu paketin dışa açılan kapısıdır. `db` ve `blockchain` modüllerini `pub` (public) yaparak diğer servislerin kullanımına sunar.
- **`src/db.rs`**: PostgreSQL bağlantı havuzunu (`sqlx::PgPool`) yönetir. Bağlantı hatalarını ve konfigürasyonları burada ele alır.
- **`src/blockchain.rs`**: `ethers-rs` kütüphanesini kullanarak blokzinciri RPC (Remote Procedure Call) bağlantısını `Provider` nesnesi olarak hazırlar. İşlem imzalamak için gerekli `Signer` yapılandırması da burada olabilir.

#### `backend/domain` (Ortak Veri Tipleri)

- **`src/lib.rs`**: Proje genelinde kullanılan veri modellerini (`struct`) ve hata tiplerini (`enum`) içerir. Örneğin `Transaction` struct'ı hem API hem de Event Listener tarafından kullanılır. Bu sayede kod tekrarı önlenir ve tip güvenliği sağlanır.

---

### 2. ⛓️ Blockchain (Hardhat & Solidity)

Akıllı kontratların geliştirildiği ve ağa yüklendiği bölümdür.

- **`contracts/MoneyToken.sol`**: DTL (Dijital Türk Lirası) token'ını temsil eden akıllı kontrat.
  - `ERC20` standardını kullanır.
  - `mint` (para basma), `burn` (yakma) ve `updateMetadata` (işlemlere IPFS hash ekleme) gibi fonksiyonlara sahiptir.
- **`scripts/deploy.ts`**: Kontratı Besu ağına yükleyen (deployment) TypeScript betiğidir. Kontrat yüklendikten sonra oluşturulan adresi konsola basar. Bu adres backend ve frontend konfigürasyonlarında kullanılır.

---

### 3. 🖥️ Frontend (Vue.js)

Son kullanıcının etkileşime girdiği cüzdan arayüzü.

- **`src/App.vue`**: Ana uygulama dosyasıdır.
  - **Cüzdan Bağlantısı**: `ethers.js` kütüphanesini kullanarak tarayıcıdaki cüzdan (MetaMask) ile bağlantı kurar.
  - **Bakiye Gösterimi**: Kullanıcının DTL bakiyesini gösterir.
  - **Transfer Formu**: Başka bir adrese DTL göndermek için basit bir form sunar ve bu isteği backend API'sine iletir.
- **`src/main.js`**: Vue uygulamasını başlatan giriş dosyasıdır.

---

### 4. ⏱️ Scheduler (Go)

Blockchain ağını periyodik olarak izleyen, Hangfire benzeri bir job scheduler servisi.

- **`main.go`**: Ana uygulama dosyasıdır.
  - **JSON-RPC İstemcisi**: Besu node'una HTTP üzerinden bağlanır.
  - **Blok Takibi**: Güncel blok numarası, hash, timestamp ve validator bilgilerini alır.
  - **Transfer Tespiti**: Son 10 bloktaki ERC20 token transferlerini tespit eder ve decode eder.
  - **Rapor Oluşturma**: Detaylı blockchain raporlarını TXT dosyasına yazar.
- **`Dockerfile`**: Multi-stage build ile minimal Alpine image oluşturur.
- **`logs/blockchain_report.txt`**: Oluşturulan raporların tutulduğu dosya.

Scheduler çıktı örneği:
```
2026/01/06 20:50:25 ========== Running scheduled job ==========
2026/01/06 20:50:25 📦 Current block number: 5930
2026/01/06 20:50:25 💸 Found 1 transactions in last 30 blocks
2026/01/06 20:50:25 📡 [Mock] Transaction Broadcasted internally:
2026/01/06 20:50:25    Inputs: 1, Outputs: 2
2026/01/06 20:50:25    Memo/Data: IPFS:TODO_EXTRACT_FROM_LOGS
2026/01/06 20:50:25    💸 OpenCBDC Payment Logged | 0xa197...5585 -> 0x6273...ef57 : 200 DTL (30ms)
2026/01/06 20:50:25    📝 Logged: 0xa197...5585 -> 0x6273...ef57 : 200 DTL
2026/01/06 20:50:25 ✅ Job completed in 31.038375ms
```

**Log Dosyaları:**
- `blockchain_report.txt`: Sadece transfer satırları (başlangıç/kapanış mesajları yok)
- `opencbdc_report.txt`: Detaylı CBDC işlem raporları (UTXO'lar, coin selection vb.)

---

### 5. 📦 SDK (Client-Side Verification)

Bu proje "Multi-Indexer" (Çoklu İndeksleyici) mimarisini kullandığı için, verinin doğruluğu kritik önem taşır.

- **`src/index.ts`**: `MultiIndexerClient` sınıfını içerir.
  - **Trust Majority (Çoğunluğa Güven):** İstemci, bir veri (örneğin bakiye) sorgularken tek bir sunucuya güvenmek yerine, konfigüre edilmiş 3 farklı sunucuya (Indexer) aynı soruyu sorar.
  - Eğer en az 2 sunucu aynı cevabı verirse (Çoğunluk/Quorum), veri doğru kabul edilir. Bu, merkezi bir otoriteye olan güveni dağıtarak güvenliği artırır.

---

### 6. 🏗️ Altyapı ve DevOps

- **`infra/compose.yaml`**: Tüm sistemi tek komutla ayağa kaldıran orkestrasyon dosyasıdır.
  - `validator1-4`: 4 adet Hyperledger Besu nodu (QBFT konsensüs ile).
  - `ipfs0`: Özel IPFS ağı (swarm.key ile güvenli).
  - `postgres` & `redis`: Veritabanı servisleri.
  - `scheduler`: Go tabanlı blockchain izleme servisi.
- **`infra/besu/genesis.json`**: QBFT konsensüs için genesis bloğu. 4 validator adresi extraData'da RLP-encoded olarak tanımlanmıştır.
- **`infra/besu/config.toml`**: Besu node konfigürasyonu (RPC, P2P, mining ayarları).
- **`infra/besu/static-nodes.json`**: Validator'ların birbirini bulması için enode adresleri.
- **`infra/besu/keys/`**: Her validator için özel anahtar dosyaları.
- **`infra/ipfs/swarm.key`**: Özel IPFS ağının güvenliği için kullanılan anahtar dosyasıdır.

---

## 🔧 Validator Adresleri

Proje, test amaçlı bilinen private key'ler kullanır (Ganache/Hardhat standart hesapları):

| Validator | Private Key | Address |
|-----------|-------------|---------|
| validator1 | `0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63` | `0xfe3b557e8fb62b89f4916b721be55ceb828dbd73` |
| validator2 | `0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3` | `0x627306090abab3a6e1400e9345bc60c78a8bef57` |
| validator3 | `0xae6ae8e5ccbfb04590405997ee2d52d2b330726137b875053c36d94e974d162f` | `0xf17f52151ebef6c7334fad080c5704d77216b732` |
| validator4 | `0x0dbbe8e4ae425a6d2687f1a7e3ba17bc98c673636790f1b8ad91193c05875ef1` | `0xc5fdf4076b8f3a5357c5e395ab970b5b54098fef` |

> ⚠️ **Uyarı**: Bu key'ler sadece geliştirme/test amaçlıdır. Production ortamında kesinlikle kullanmayın!

## 🚀 Kurulum ve Çalıştırma

Tüm sistemi çalıştırmak için aşağıdaki adımları izleyebilirsiniz (Detaylar `WALKTHROUGH.md` dosyasındadır).

### Docker ile Çalıştırma (Önerilen)

```bash
# Tüm sistemi başlat
cd infra
docker compose up -d

# Logları takip et
docker logs -f dtl-scheduler
```

### Manuel Çalıştırma

```bash
# 1. Blockchain ağı
cd infra
docker compose up -d validator1 validator2 validator3 validator4

# 2. Backend servisleri
cd ../backend
cargo build --release
cargo run --bin dtl-api &
cargo run --bin dtl-event-listener &

# 3. Frontend
cd ../frontend
npm install
npm run dev

# 4. Scheduler (Go)
cd ../scheduler
go run main.go model.go payment.go
```

### Environment Variables

| Variable | Default | Açıklama |
|----------|---------|----------|
| `BESU_RPC_URL` | `http://localhost:8545` | Besu RPC endpoint |
| `SCHEDULER_INTERVAL` | `30s` | Kontrol aralığı |
| `OPENCBDC_URL` | `mock` | OpenCBDC API URL (mock için boş bırakın) |
| `LOG_FILE` | `./logs/blockchain_report.txt` | Log dosyası yolu |

### Test Transfer Gönderme

```bash
# Hardhat console'dan
cd blockchain
npx hardhat console --network localhost

# Token transfer
const token = await ethers.getContractAt("MoneyToken", "DEPLOYED_CONTRACT_ADDRESS")
await token.transfer("0x627306090abab3a6e1400e9345bc60c78a8bef57", ethers.parseEther("100"))
```
