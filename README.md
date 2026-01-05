# Dijital Türk Lirası (DTL) - Multi-Indexer DB PoC

Bu proje, **Dijital Türk Lirası (DTL)** ekosistemi için geliştirilmiş kapsamlı bir **Proof of Concept (Kavram Kanıtı)** çalışmasıdır. Proje, merkeziyetsiz bir blokzinciri ağı, olay tabanlı (event-driven) bir arka uç, modern bir kullanıcı arayüzü ve akıllı veri doğrulama mekanizmalarını içerir.

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

### 5. SDK (Multi-Indexer Consensus)

- **Güven Mekanizması**: İstemci tarafında "Trust Majority" (Çoğunluğa Güven) mantığıyla çalışan bir TypeScript kütüphanesi. Farklı indexer servislerinden gelen verileri çapraz doğrulayarak güvenliği artırır.

---

## 📂 Detaylı Dosya ve Proje Yapısı

Aşağıda projenin tüm klasörleri ve içerdikleri önemli dosyaların amaçları detaylıca açıklanmıştır.

```
dtl-multiindexer-db-poc/
├── 📁 backend/             # Rust Workspace (Tüm arka uç servisleri)
├── 📁 frontend/            # Vue.js Cüzdan Uygulaması
├── 📁 blockchain/          # Akıllı Kontratlar (Hardhat)
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

### 4. 📦 SDK (Client-Side Verification)

Bu proje "Multi-Indexer" (Çoklu İndeksleyici) mimarisini kullandığı için, verinin doğruluğu kritik önem taşır.

- **`src/index.ts`**: `MultiIndexerClient` sınıfını içerir.
  - **Trust Majority (Çoğunluğa Güven):** İstemci, bir veri (örneğin bakiye) sorgularken tek bir sunucuya güvenmek yerine, konfigüre edilmiş 3 farklı sunucuya (Indexer) aynı soruyu sorar.
  - Eğer en az 2 sunucu aynı cevabı verirse (Çoğunluk/Quorum), veri doğru kabul edilir. Bu, merkezi bir otoriteye olan güveni dağıtarak güvenliği artırır.

---

### 5. 🏗️ Altyapı ve DevOps

- **`docker-compose.yaml`**: Tüm sistemi tek komutla ayağa kaldıran orkestrasyon dosyasıdır.
  - `validator1-4`: 4 adet Hyperledger Besu nodu (Blokzinciri Ağı).
  - `ipfs`: Dosya depolama sunucusu.
  - `postgres` & `redis`: Veritabanı servisleri.
- **`infra/ipfs/swarm.key`**: Özel IPFS ağının güvenliği için kullanılan anahtar dosyasıdır. Sadece bu anahtara sahip node'lar ağa katılabilir.

## 🚀 Kurulum ve Çalıştırma

Tüm sistemi çalıştırmak için aşağıdaki adımları izleyebilirsiniz (Detaylar `WALKTHROUGH.md` dosyasındadır).
