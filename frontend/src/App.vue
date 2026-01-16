<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

const API_URL = 'http://localhost:8000'

// Validator endpoints (direkt blockchain'e bağlan)
const VALIDATORS = [
  { name: 'Validator 1', url: 'http://localhost:8545', id: 1 },
  { name: 'Validator 2', url: 'http://localhost:8555', id: 2 },
  { name: 'Validator 3', url: 'http://localhost:8565', id: 3 },
  { name: 'Validator 4', url: 'http://localhost:8575', id: 4 },
]

const users = ref([])
const nodes = ref({ nodes: [] })
const transfers = ref([])
const ledger = ref([])
const transactions = ref([])
const selectedFrom = ref('')
const selectedTo = ref('')
const amount = ref(100)
const selectedValidator = ref('validator1')  // Transfer için validator seçimi
const status = ref('')
const lastTx = ref(null)
const activeValidator = ref(1)
const validatorData = ref({})
const validatorLogs = ref({})  // Her validator'ın logları

// Her validator için block number ve veri
async function loadValidatorData() {
  for (const v of VALIDATORS) {
    try {
      // Block number al
      const resp = await fetch(v.url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'eth_blockNumber',
          params: [],
          id: 1
        })
      })
      const data = await resp.json()
      const blockNum = data.result ? parseInt(data.result, 16) : null

      validatorData.value[v.id] = {
        name: v.name,
        url: v.url,
        online: true,
        blockNumber: blockNum,
        synced: true
      }
    } catch (e) {
      validatorData.value[v.id] = {
        name: v.name,
        url: v.url,
        online: false,
        blockNumber: null,
        synced: false
      }
    }
  }
}

async function loadUsers() {
  try {
    const res = await axios.get(`${API_URL}/accounts`)
    // OpenCBDC mode: accounts response'u farklı
    users.value = res.data.map((acc, i) => ({
      id: i + 1,
      username: `Account ${i + 1}`,  // Adres bazlı, username yok
      address: acc.address,
      balance: acc.balance
    }))
    if (users.value.length >= 2) {
      selectedFrom.value = users.value[0].address
      selectedTo.value = users.value[1].address
    }
  } catch (e) {
    status.value = 'Error loading accounts: ' + e.message
  }
}

async function loadNodes() {
  try {
    const res = await axios.get(`${API_URL}/nodes`)
    nodes.value = res.data
  } catch (e) {
    console.error('Error loading nodes:', e)
  }
}

async function loadTransactions() {
  try {
    const res = await axios.get(`${API_URL}/transactions`)
    // OpenCBDC mode: transactions içinde transactions array'i var
    transactions.value = res.data.transactions || res.data
  } catch (e) {
    console.error('Error loading transactions:', e)
  }
}

async function loadTransfers() {
  try {
    const res = await axios.get(`${API_URL}/nodes/transfers`)
    transfers.value = res.data.transfers || []
  } catch (e) {
    console.error('Error loading transfers:', e)
  }
}

async function loadLedger() {
  try {
    const res = await axios.get(`${API_URL}/nodes/ledger`)
    ledger.value = res.data.ledger || []
  } catch (e) {
    console.error('Error loading ledger:', e)
  }
}

async function loadValidatorLogs() {
  for (const v of VALIDATORS) {
    try {
      const res = await axios.get(`${API_URL}/nodes/validator-logs/validator${v.id}?limit=20`)
      validatorLogs.value[v.id] = res.data.logs || []
    } catch (e) {
      validatorLogs.value[v.id] = []
    }
  }
}

async function seedUsers() {
  status.value = 'Seeding users...'
  try {
    await axios.post(`${API_URL}/health/seed`)
    await loadUsers()
    status.value = 'Users seeded! Alice, Bob, Charlie and Admin created.'
  } catch (e) {
    status.value = 'Seed error: ' + e.message
  }
}

async function sendTransfer() {
  if (!selectedFrom.value || !selectedTo.value || !amount.value) {
    status.value = 'Please fill all fields'
    return
  }
  status.value = `Sending transfer via ${selectedValidator.value}...`
  try {
    const res = await axios.post(`${API_URL}/transactions/transfer`, {
      from: selectedFrom.value,
      to: selectedTo.value,
      amount: Number(amount.value),
      validator: selectedValidator.value
    })
    lastTx.value = res.data
    status.value = `✅ Transfer completed via ${selectedValidator.value}! Blockchain + IPFS + OpenCBDC kaydedildi.`
    await loadUsers()
    await loadTransactions()
    // 2 saniye sonra logları güncelle
    setTimeout(() => {
      loadTransfers()
      loadLedger()
      loadValidatorData()
      loadValidatorLogs()
    }, 2000)
  } catch (e) {
    status.value = 'Transfer error: ' + (e.response?.data?.error || e.message)
  }
}

async function refreshAll() {
  await Promise.all([
    loadUsers(),
    loadNodes(),
    loadTransfers(),
    loadLedger(),
    loadTransactions(),
    loadValidatorData(),
    loadValidatorLogs()
  ])
  status.value = 'All data refreshed!'
}

// Seçili validator'ın durumu
const currentValidator = computed(() => validatorData.value[activeValidator.value] || {})

// Tüm validator'lar sync mi?
const allSynced = computed(() => {
  const blocks = Object.values(validatorData.value)
    .filter(v => v.online)
    .map(v => v.blockNumber)
  return blocks.length > 0 && new Set(blocks).size === 1
})

onMounted(() => {
  loadUsers()
  loadNodes()
  loadTransfers()
  loadLedger()
  loadTransactions()
  loadValidatorData()
  loadValidatorLogs()
  // Her 5 saniyede validator verilerini güncelle
  setInterval(loadValidatorData, 5000)
  setInterval(loadValidatorLogs, 5000)
  setInterval(loadNodes, 10000)
})
</script>

<template>
  <main>
    <div class="container">
      <h1>🇹🇷 Digital Turkish Lira (DTL)</h1>
      <p class="subtitle">Multi-Indexer & Decentralized Validation Demo</p>

      <div class="actions">
        <button @click="seedUsers" class="seed-btn">🌱 Seed Demo Users</button>
        <button @click="refreshAll" class="refresh-btn">🔄 Refresh All</button>
      </div>

      <!-- Validator Tab'ları -->
      <div class="validator-tabs">
        <button v-for="v in VALIDATORS" :key="v.id" @click="activeValidator = v.id"
          :class="{ active: activeValidator === v.id, online: validatorData[v.id]?.online, offline: !validatorData[v.id]?.online }"
          class="validator-tab">
          <span class="status-dot">{{ validatorData[v.id]?.online ? '🟢' : '🔴' }}</span>
          {{ v.name }}
          <span class="block-num" v-if="validatorData[v.id]?.blockNumber">
            #{{ validatorData[v.id].blockNumber }}
          </span>
        </button>
      </div>

      <!-- Sync Status -->
      <div class="sync-banner" :class="{ synced: allSynced, 'not-synced': !allSynced }">
        <span v-if="allSynced">✅ Tüm Validator'lar Senkronize - Merkezi Olmayan Veri Tutarlılığı Sağlandı (QBFT)</span>
        <span v-else>⏳ Validator'lar senkronize ediliyor...</span>
      </div>

      <!-- Aktif Validator Bilgisi -->
      <div class="active-validator-info">
        <h2>📊 {{ currentValidator.name || 'Validator' }} - Veri Görünümü</h2>
        <p class="validator-url">{{ currentValidator.url }}</p>
      </div>

      <!-- Kullanıcılar (Tüm validator'larda aynı) -->
      <div v-if="users.length" class="users-table">
        <h3>👥 Kullanıcılar & Bakiyeler</h3>
        <p class="note">Bu veri tüm {{Object.values(validatorData).filter(v => v.online).length}} validator'da
          aynıdır.</p>
        <table>
          <thead>
            <tr>
              <th>Hesap</th>
              <th>Adres</th>
              <th>Bakiye</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>{{ user.username }}</td>
              <td class="address">{{ user.address.slice(0, 10) }}...{{ user.address.slice(-6) }}</td>
              <td class="balance">{{ parseFloat(user.balance).toFixed(2) }} DTL</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Transfer Formu -->
      <div class="transfer-box">
        <h3>💸 Transfer Yap</h3>
        <p class="note">Transfer: Blockchain → IPFS → OpenCBDC → Tüm Validator'lara Broadcast</p>
        <div class="form-row">
          <label>Validator:</label>
          <select v-model="selectedValidator" class="validator-select">
            <option value="validator1">🟢 Validator 1 (8545)</option>
            <option value="validator2">🟢 Validator 2 (8555)</option>
            <option value="validator3">🟢 Validator 3 (8565)</option>
            <option value="validator4">🟢 Validator 4 (8575)</option>
          </select>
        </div>
        <div class="form-row">
          <label>Gönderen:</label>
          <select v-model="selectedFrom">
            <option v-for="user in users" :key="user.id" :value="user.address">
              {{ user.username }} ({{ parseFloat(user.balance).toFixed(2) }} DTL)
            </option>
          </select>
        </div>
        <div class="form-row">
          <label>Alıcı:</label>
          <select v-model="selectedTo">
            <option v-for="user in users" :key="user.id" :value="user.address">
              {{ user.username }}
            </option>
          </select>
        </div>
        <div class="form-row">
          <label>Miktar:</label>
          <input v-model="amount" type="number" placeholder="Miktar (DTL)" />
        </div>
        <button @click="sendTransfer" class="send-btn">💸 Transfer Gönder ({{ selectedValidator }})</button>
      </div>

      <!-- Son İşlem -->
      <div v-if="lastTx" class="last-tx">
        <h3>✅ Son Transfer</h3>
        <div class="tx-details">
          <p><strong>TX ID:</strong> {{ lastTx.tx_id }}</p>
          <p><strong>Miktar:</strong> {{ lastTx.amount }} DTL</p>
          <p v-if="lastTx.tx_hash"><strong>TX Hash:</strong> <span class="hash">{{ lastTx.tx_hash }}</span></p>
          <p v-if="lastTx.block_number"><strong>Block:</strong> #{{ lastTx.block_number }}</p>
          <p v-if="lastTx.ipfs_cid"><strong>IPFS CID:</strong> <span class="cid">{{ lastTx.ipfs_cid }}</span></p>
          <p v-if="lastTx.validator"><strong>Validator:</strong> {{ lastTx.validator }}</p>
        </div>
        <div class="broadcast-info">
          🔗 Blockchain ✓ → 📦 IPFS ✓ → 💰 OpenCBDC ✓ → 📡 All Validators ✓
        </div>
      </div>

      <!-- İşlem Geçmişi -->
      <div class="transactions-panel">
        <h3>📜 İşlem Geçmişi (Tüm Validator'larda Mevcut)</h3>
        <div class="transactions-list" v-if="transactions.length">
          <div v-for="tx in transactions.slice(0, 10)" :key="tx.id" class="tx-item">
            <span class="tx-id">#{{ tx.id }}</span>
            <span class="tx-amount">{{ parseFloat(tx.amount).toFixed(2) }} DTL</span>
            <span class="tx-status">{{ tx.status }}</span>
            <span class="tx-ipfs" v-if="tx.ipfs_cid">IPFS ✓</span>
          </div>
        </div>
        <p v-else class="no-data">Henüz işlem yok. Bir transfer yapın!</p>
      </div>

      <!-- Validator Logları -->
      <div class="validator-logs-section">
        <h3>📋 Validator Logları (dtl-validator-X.txt)</h3>
        <div class="validator-logs-grid">
          <div v-for="v in VALIDATORS" :key="v.id" class="validator-log-panel">
            <h4>
              <span :class="validatorData[v.id]?.online ? 'online-dot' : 'offline-dot'">●</span>
              {{ v.name }}
            </h4>
            <div class="log-content">
              <div v-for="(line, i) in (validatorLogs[v.id] || []).slice(-8)" :key="i" class="log-line">{{ line }}</div>
              <p v-if="!(validatorLogs[v.id] || []).length" class="no-data">Henüz log yok</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Transfers & OpenCBDC Logları -->
      <div class="logs-section">
        <div class="log-panel">
          <h4>📝 Transfer Logları</h4>
          <div class="log-content">
            <div v-for="(line, i) in transfers.slice(-10)" :key="i" class="log-line">{{ line }}</div>
            <p v-if="!transfers.length" class="no-data">Henüz log yok</p>
          </div>
        </div>
        <div class="log-panel">
          <h4>💰 OpenCBDC Ledger</h4>
          <div class="log-content">
            <div v-for="(line, i) in ledger.slice(-10)" :key="i" class="log-line">{{ line }}</div>
            <p v-if="!ledger.length" class="no-data">Henüz UTXO yok</p>
          </div>
        </div>
      </div>

      <p class="status">{{ status }}</p>
    </div>
  </main>
</template>

<style scoped>
.container {
  max-width: 1000px;
  margin: 20px auto;
  padding: 25px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  color: #e8e8e8;
}

h1 {
  text-align: center;
  margin-bottom: 5px;
  color: #00d9ff;
}

.subtitle {
  text-align: center;
  color: #888;
  margin-bottom: 20px;
  font-size: 14px;
}

h2,
h3 {
  color: #00d9ff;
  margin-top: 20px;
}

.actions {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

button {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.2s;
}

.seed-btn {
  background: #4caf50;
  color: white;
}

.refresh-btn {
  background: #2196f3;
  color: white;
}

.send-btn {
  background: linear-gradient(135deg, #ff9800, #ff5722);
  color: white;
  width: 100%;
  margin-top: 10px;
  font-size: 16px;
}

button:hover {
  transform: translateY(-2px);
  opacity: 0.9;
}

/* Validator Tabs */
.validator-tabs {
  display: flex;
  gap: 5px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.validator-tab {
  flex: 1;
  min-width: 120px;
  padding: 12px 10px;
  background: #1a1a2e;
  color: #888;
  border: 2px solid #333;
  border-radius: 8px 8px 0 0;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}

.validator-tab.active {
  background: #0d1b2a;
  color: #00d9ff;
  border-color: #00d9ff;
  border-bottom: none;
}

.validator-tab.online {
  border-top-color: #4caf50;
}

.validator-tab.offline {
  border-top-color: #f44336;
}

.status-dot {
  font-size: 10px;
}

.block-num {
  font-size: 10px;
  color: #666;
}

/* Sync Banner */
.sync-banner {
  padding: 10px;
  border-radius: 0 0 8px 8px;
  text-align: center;
  font-weight: bold;
  margin-bottom: 15px;
}

.sync-banner.synced {
  background: #1b4332;
  color: #4caf50;
}

.sync-banner.not-synced {
  background: #4a1a1a;
  color: #ff9800;
}

/* Active Validator Info */
.active-validator-info {
  background: #0d1b2a;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 15px;
}

.active-validator-info h2 {
  margin: 0 0 5px 0;
  font-size: 16px;
}

.validator-url {
  font-family: monospace;
  font-size: 11px;
  color: #666;
  margin: 0;
}

/* Users Table */
.users-table {
  margin-bottom: 20px;
}

.users-table table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}

.users-table th,
.users-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #333;
}

.users-table th {
  color: #00d9ff;
  font-size: 12px;
}

.address {
  font-family: monospace;
  font-size: 11px;
  color: #888;
}

.balance {
  color: #4caf50;
  font-weight: bold;
}

.note {
  font-size: 11px;
  color: #666;
  margin: 5px 0;
}

/* Transfer Box */
.transfer-box {
  padding: 20px;
  background: #0d1b2a;
  border-radius: 12px;
  margin-bottom: 20px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.form-row label {
  width: 80px;
  font-size: 13px;
}

.form-row select,
.form-row input {
  flex: 1;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #333;
  background: #1a1a2e;
  color: white;
}

/* Last TX */
.last-tx {
  padding: 15px;
  background: linear-gradient(135deg, #0f3460, #1a1a2e);
  border-radius: 8px;
  border-left: 4px solid #4caf50;
  margin-bottom: 20px;
}

.last-tx h3 {
  color: #4caf50;
  margin: 0 0 10px 0;
  font-size: 14px;
}

.tx-details {
  margin-bottom: 10px;
}

.tx-details p {
  margin: 3px 0;
  font-size: 12px;
}

.cid {
  font-family: monospace;
  font-size: 10px;
  color: #00d9ff;
}

.broadcast-info {
  font-size: 11px;
  color: #4caf50;
  background: #1b4332;
  padding: 8px;
  border-radius: 4px;
}

/* Transactions Panel */
.transactions-panel {
  background: #0d1b2a;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 15px;
}

.transactions-panel h3 {
  margin: 0 0 10px 0;
  font-size: 14px;
}

.transactions-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.tx-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 8px;
  background: #1a1a2e;
  border-radius: 4px;
  font-size: 12px;
}

.tx-id {
  color: #888;
}

.tx-amount {
  color: #4caf50;
  font-weight: bold;
}

.tx-status {
  color: #00d9ff;
}

.tx-ipfs {
  font-size: 10px;
  color: #9c27b0;
}

/* Logs Section */
.logs-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
  margin-bottom: 15px;
}

.log-panel {
  background: #0d1b2a;
  padding: 12px;
  border-radius: 8px;
}

.log-panel h4 {
  color: #00d9ff;
  margin: 0 0 10px 0;
  font-size: 12px;
}

.log-content {
  background: #000;
  padding: 8px;
  border-radius: 4px;
  max-height: 120px;
  overflow-y: auto;
  font-family: monospace;
  font-size: 10px;
}

.log-line {
  padding: 2px 0;
  color: #0f0;
  border-bottom: 1px solid #111;
}

.no-data {
  color: #666;
  font-style: italic;
  font-size: 11px;
}

.status {
  margin-top: 15px;
  padding: 10px;
  background: #333;
  border-radius: 6px;
  text-align: center;
  font-size: 13px;
}

/* Validator Select */
.validator-select {
  background: #0f3460 !important;
  border-color: #00d9ff !important;
}

/* TX Hash */
.hash {
  font-family: monospace;
  font-size: 10px;
  color: #ff9800;
  word-break: break-all;
}

/* Validator Logs Section */
.validator-logs-section {
  margin-bottom: 20px;
}

.validator-logs-section h3 {
  font-size: 14px;
  margin-bottom: 10px;
}

.validator-logs-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.validator-log-panel {
  background: #0d1b2a;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid #333;
}

.validator-log-panel h4 {
  color: #00d9ff;
  margin: 0 0 8px 0;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.online-dot {
  color: #4caf50;
}

.offline-dot {
  color: #f44336;
}

.validator-log-panel .log-content {
  max-height: 100px;
  font-size: 9px;
}

@media (max-width: 768px) {
  .validator-logs-grid {
    grid-template-columns: 1fr;
  }
}
</style>
