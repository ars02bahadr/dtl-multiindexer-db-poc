<script setup>
import { ref, onMounted, watch } from 'vue'
import axios from 'axios'

const API_URL = 'http://localhost:8000'

const VALIDATORS = [
  { name: 'Validator 1', url: 'http://localhost:8545', id: 1 },
  { name: 'Validator 2', url: 'http://localhost:8555', id: 2 },
  { name: 'Validator 3', url: 'http://localhost:8565', id: 3 },
  { name: 'Validator 4', url: 'http://localhost:8575', id: 4 },
]

// ==================== STATE ====================

// Auth
const currentUser = ref(null) // { username, name, address, token }
const loginForm = ref({ username: '', password: '' })
const loginError = ref('')

// Data
const users = ref([])
const accounts = ref([])
const transactions = ref([])
const transfers = ref([])
const validatorLogs = ref({})
const status = ref('')
const lastTx = ref(null)

// Transfer
const transferMode = ref('standard')
const selectedTemplateId = ref('')
const transferForm = ref({
  to: '',
  amount: 100,
  validator: 'validator1'
})

// Templates
const templates = ref([])
const sidebarTab = ref('templates') // 'templates' | 'newTemplate' | 'editTemplate'
const templateForm = ref({
  template_name: '',
  payee_name: '',
  payee_account: '',
  default_amount: 0,
  description: ''
})
const editingTemplateId = ref(null)

// ==================== AUTH ====================

function setupInterceptor() {
  axios.interceptors.request.use(config => {
    if (currentUser.value?.token) {
      config.headers.Authorization = `Bearer ${currentUser.value.token}`
    }
    return config
  }, error => Promise.reject(error))
}

async function login() {
  loginError.value = ''
  if (!loginForm.value.username || !loginForm.value.password) {
    loginError.value = 'Kullanıcı adı ve şifre gerekli'
    return
  }

  try {
    const res = await axios.post(`${API_URL}/auth/login`, {
      username: loginForm.value.username,
      password: loginForm.value.password
    })

    currentUser.value = {
      username: res.data.username,
      name: res.data.name,
      address: res.data.address,
      token: res.data.token
    }

    localStorage.setItem('dtl_user', JSON.stringify(currentUser.value))
    setupInterceptor()
    status.value = `${res.data.name} olarak giriş yapıldı`
    await refreshAll()
  } catch (e) {
    loginError.value = e.response?.data?.error || 'Giriş hatası'
  }
}

function logout() {
  currentUser.value = null
  localStorage.removeItem('dtl_user')
  window.location.reload()
}

// ==================== HELPERS ====================

function getUserName(address) {
  if (!address) return '?'
  const acc = accounts.value.find(a => a.address === address)
  return acc ? acc.name : address.slice(0, 10) + '...'
}

// ==================== TEMPLATES ====================

async function loadTemplates() {
  if (!currentUser.value) return
  try {
    const res = await axios.get(`${API_URL}/templates`)
    templates.value = res.data
  } catch (e) {
    console.error('Template error:', e)
  }
}

function startNewTemplate() {
  editingTemplateId.value = null
  templateForm.value = {
    template_name: '',
    payee_name: '',
    payee_account: '',
    default_amount: 0,
    description: ''
  }
  sidebarTab.value = 'newTemplate'
}

function startEditTemplate(tpl) {
  editingTemplateId.value = tpl.template_id
  templateForm.value = {
    template_name: tpl.template_name || '',
    payee_name: tpl.payee_name || '',
    payee_account: tpl.payee_account || '',
    default_amount: tpl.default_amount || 0,
    description: tpl.description || ''
  }
  sidebarTab.value = 'editTemplate'
}

async function saveTemplate() {
  const payload = { ...templateForm.value }

  try {
    if (editingTemplateId.value) {
      await axios.put(`${API_URL}/templates/${editingTemplateId.value}`, payload)
      status.value = 'Template güncellendi!'
    } else {
      await axios.post(`${API_URL}/templates`, payload)
      status.value = 'Template oluşturuldu!'
    }
    sidebarTab.value = 'templates'
    await loadTemplates()
  } catch (e) {
    status.value = 'Template hatası: ' + (e.response?.data?.error || e.message)
  }
}

async function deleteTemplate(tplId) {
  if (!confirm('Bu template silinecek, emin misiniz?')) return
  try {
    await axios.delete(`${API_URL}/templates/${tplId}`)
    status.value = 'Template silindi'
    await loadTemplates()
  } catch (e) {
    status.value = 'Silme hatası: ' + e.message
  }
}

// ==================== DATA LOADING ====================

async function loadAccounts() {
  try {
    const res = await axios.get(`${API_URL}/accounts`)
    accounts.value = res.data
    // Users for dropdown (exclude current user for "to" field)
    users.value = res.data.map(acc => ({
      address: acc.address,
      name: acc.name || acc.address.slice(0, 10),
      balance: acc.balance
    }))
  } catch (e) {
    status.value = 'Hesap yükleme hatası: ' + e.message
  }
}

async function loadTransactions() {
  try {
    const res = await axios.get(`${API_URL}/transactions`)
    transactions.value = res.data.transactions || res.data
  } catch (e) {}
}

async function loadTransfers() {
  try {
    const res = await axios.get(`${API_URL}/nodes/transfers`)
    transfers.value = res.data.transfers || []
  } catch (e) {}
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
  status.value = 'Kullanıcılar oluşturuluyor...'
  try {
    await axios.post(`${API_URL}/health/seed`)
    await loadAccounts()
    status.value = '7 kullanıcı 1200 DTL ile oluşturuldu!'
  } catch (e) {
    status.value = 'Seed hatası: ' + e.message
  }
}

async function sendTransfer() {
  if (!transferForm.value.to || !transferForm.value.amount) {
    status.value = 'Alıcı ve tutar gerekli'
    return
  }

  status.value = `Transfer gönderiliyor (${transferForm.value.validator})...`
  try {
    const payload = {
      from: currentUser.value.address,
      to: transferForm.value.to,
      amount: Number(transferForm.value.amount),
      validator: transferForm.value.validator
    }

    if (transferMode.value === 'template' && selectedTemplateId.value) {
      payload.template_id = selectedTemplateId.value
    }

    const res = await axios.post(`${API_URL}/transactions/transfer`, payload)

    lastTx.value = res.data
    status.value = `Transfer tamamlandı! TX ID: ${res.data.tx_id}`
    await refreshAll()
  } catch (e) {
    status.value = 'Transfer hatası: ' + (e.response?.data?.error || e.message)
  }
}

async function refreshAll() {
  await Promise.all([
    loadAccounts(), loadTransactions(), loadTransfers(),
    loadValidatorLogs(), loadTemplates()
  ])
}

// Watchers
watch(selectedTemplateId, (newId) => {
  if (transferMode.value === 'template' && newId) {
    const tpl = templates.value.find(t => t.template_id === newId)
    if (tpl) {
      transferForm.value.to = tpl.payee_account
      if (tpl.default_amount) transferForm.value.amount = tpl.default_amount
    }
  }
})

// Lifecycle
onMounted(() => {
  const saved = localStorage.getItem('dtl_user')
  if (saved) {
    try {
      currentUser.value = JSON.parse(saved)
    } catch (e) {
      localStorage.removeItem('dtl_user')
    }
  }

  setupInterceptor()
  refreshAll()

  setInterval(loadValidatorLogs, 5000)
  setInterval(loadAccounts, 10000)
})
</script>

<template>
  <!-- LOGIN SCREEN -->
  <div v-if="!currentUser" class="login-screen">
    <div class="login-box">
      <h1>Digital Turkish Lira</h1>
      <p class="login-subtitle">Multi-Indexer PoC - OpenCBDC</p>

      <div class="login-form">
        <div class="field">
          <label>Kullanıcı Adı</label>
          <input v-model="loginForm.username" placeholder="ör: uluer.01" @keyup.enter="login" />
        </div>
        <div class="field">
          <label>Şifre</label>
          <input v-model="loginForm.password" type="password" placeholder="admin.1234" @keyup.enter="login" />
        </div>
        <div v-if="loginError" class="login-error">{{ loginError }}</div>
        <button @click="login" class="login-btn">Giriş Yap</button>
      </div>

      <div class="login-hint">
        <p>Demo Hesaplar:</p>
        <small>bahadir.01 / uluer.01 / cagatay.01 / ebru.01 / burcu.01 / gizem.01 / burak.01</small>
        <small>Şifre: <strong>admin.1234</strong></small>
      </div>
    </div>
  </div>

  <!-- MAIN APP -->
  <div v-else class="app-layout">

    <!-- SIDEBAR -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="user-info">
          <div class="user-name">{{ currentUser.name }}</div>
          <div class="user-username">@{{ currentUser.username }}</div>
          <div class="user-balance" v-if="accounts.length">
            {{ parseFloat(accounts.find(a => a.address === currentUser.address)?.balance || 0).toFixed(2) }} DTL
          </div>
        </div>
        <button @click="logout" class="logout-btn">Çıkış</button>
      </div>

      <div class="sidebar-nav">
        <button :class="{active: sidebarTab === 'templates'}" @click="sidebarTab = 'templates'">Template'lerim</button>
      </div>

      <!-- Template List -->
      <div v-if="sidebarTab === 'templates'" class="sidebar-content">
        <button @click="startNewTemplate" class="new-tpl-btn">+ Yeni Template</button>

        <div v-if="templates.length === 0" class="empty-msg">Henüz template yok</div>

        <div v-for="t in templates" :key="t.template_id" class="tpl-card">
          <div class="tpl-card-header">
            <strong>{{ t.template_name }}</strong>
            <span class="tpl-amount">{{ t.default_amount }} DTL</span>
          </div>
          <div class="tpl-card-detail">
            <span>Alıcı: {{ t.payee_name || getUserName(t.payee_account) }}</span>
          </div>
          <div class="tpl-card-cid" v-if="t.cid">
            IPFS: {{ t.cid.slice(0, 16) }}...
          </div>
          <div class="tpl-card-actions">
            <button @click="startEditTemplate(t)" class="btn-sm">Düzenle</button>
            <button @click="deleteTemplate(t.template_id)" class="btn-sm btn-danger">Sil</button>
          </div>
        </div>
      </div>

      <!-- New / Edit Template Form -->
      <div v-if="sidebarTab === 'newTemplate' || sidebarTab === 'editTemplate'" class="sidebar-content">
        <h4>{{ sidebarTab === 'editTemplate' ? 'Template Düzenle' : 'Yeni Template' }}</h4>

        <div class="field">
          <label>Template Adı</label>
          <input v-model="templateForm.template_name" placeholder="ör: Kira Ödemesi" />
        </div>
        <div class="field">
          <label>Alıcı Adı</label>
          <input v-model="templateForm.payee_name" placeholder="ör: Ev sahibi" />
        </div>
        <div class="field">
          <label>Alıcı</label>
          <select v-model="templateForm.payee_account">
            <option value="">Seçiniz...</option>
            <option v-for="u in users" :key="u.address" :value="u.address">
              {{ u.name }} ({{ u.address.slice(0, 10) }}...)
            </option>
          </select>
        </div>
        <div class="field">
          <label>Tutar (DTL)</label>
          <input v-model="templateForm.default_amount" type="number" />
        </div>
        <div class="field">
          <label>Açıklama</label>
          <input v-model="templateForm.description" placeholder="Opsiyonel not" />
        </div>

        <div class="form-actions">
          <button @click="saveTemplate" class="btn-primary">Kaydet</button>
          <button @click="sidebarTab = 'templates'" class="btn-cancel">İptal</button>
        </div>
      </div>
    </aside>

    <!-- MAIN CONTENT -->
    <main class="main-content">
      <header class="top-bar">
        <h2>DTL Multi-Indexer Dashboard</h2>
        <div class="top-actions">
          <button @click="seedUsers" class="btn-seed">Seed Users</button>
          <button @click="refreshAll" class="btn-refresh">Yenile</button>
        </div>
      </header>

      <!-- Status Bar -->
      <div v-if="status" class="status-bar">{{ status }}</div>

      <div class="content-grid">

        <!-- LEFT: Transfer + Accounts -->
        <div class="content-col">

          <!-- Transfer Box -->
          <div class="card">
            <h3>Transfer Yap</h3>
            <div class="from-info">
              Gönderen: <strong>{{ currentUser.name }}</strong> ({{ currentUser.address.slice(0, 10) }}...)
            </div>

            <div class="toggle-row">
              <button :class="{active: transferMode === 'standard'}" @click="transferMode='standard'">Standart</button>
              <button :class="{active: transferMode === 'template'}" @click="transferMode='template'">Template ile</button>
            </div>

            <div class="field">
              <label>Validator</label>
              <select v-model="transferForm.validator">
                <option value="validator1">Validator 1</option>
                <option value="validator2">Validator 2</option>
                <option value="validator3">Validator 3</option>
                <option value="validator4">Validator 4</option>
              </select>
            </div>

            <!-- Template seçimi -->
            <div v-if="transferMode === 'template'" class="field">
              <label>Template</label>
              <select v-model="selectedTemplateId">
                <option value="">Template seçin...</option>
                <option v-for="t in templates" :key="t.template_id" :value="t.template_id">
                  {{ t.template_name }} ({{ t.payee_name || 'Adsız' }} - {{ t.default_amount }} DTL)
                </option>
              </select>
            </div>

            <div class="field">
              <label>Alıcı</label>
              <select v-model="transferForm.to" :disabled="transferMode === 'template' && selectedTemplateId">
                <option value="">Alıcı seçin...</option>
                <option v-for="u in users.filter(u => u.address !== currentUser.address)" :key="u.address" :value="u.address">
                  {{ u.name }} ({{ parseFloat(u.balance).toFixed(0) }} DTL)
                </option>
              </select>
            </div>

            <div class="field">
              <label>Tutar (DTL)</label>
              <input v-model="transferForm.amount" type="number" />
            </div>

            <button @click="sendTransfer" class="btn-send">
              {{ transferMode === 'template' ? 'Template ile Gönder' : 'Transfer Gönder' }}
            </button>
          </div>

          <!-- Last TX -->
          <div v-if="lastTx" class="card card-success">
            <h3>Son Transfer</h3>
            <div class="tx-summary">
              <span>TX #{{ lastTx.tx_id }} | {{ lastTx.amount }} DTL</span>
              <span v-if="lastTx.ipfs_cid" class="ipfs-badge">IPFS: {{ lastTx.ipfs_cid.slice(0, 12) }}...</span>
              <span v-if="lastTx.template_used" class="tpl-badge">Template Kullanıldı</span>
            </div>
            <div class="flow-text">Blockchain -> IPFS -> OpenCBDC -> MultiIndexer</div>
          </div>

          <!-- Accounts -->
          <div class="card">
            <h3>Hesaplar</h3>
            <table>
              <thead><tr><th>Ad</th><th>Adres</th><th>Bakiye</th></tr></thead>
              <tbody>
                <tr v-for="acc in accounts" :key="acc.address"
                    :class="{highlight: acc.address === currentUser.address}">
                  <td><strong>{{ acc.name }}</strong></td>
                  <td class="mono">{{ acc.address.slice(0, 12) }}...</td>
                  <td class="balance">{{ parseFloat(acc.balance).toFixed(2) }} DTL</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- RIGHT: Logs -->
        <div class="content-col">

          <!-- Validator Logs -->
          <div class="card">
            <h3>Validator Logları (4 Node)</h3>
            <div v-for="v in VALIDATORS" :key="v.id" class="log-group">
              <div class="log-label">Validator {{ v.id }}</div>
              <div class="log-content">
                <div v-for="(l, idx) in (validatorLogs[v.id] || []).slice(-12)" :key="idx">{{ l }}</div>
                <div v-if="!(validatorLogs[v.id] || []).length" class="empty-log">Henüz log yok</div>
              </div>
            </div>
          </div>

          <!-- Recent Transactions -->
          <div class="card">
            <h3>Son İşlemler</h3>
            <div v-if="transactions.length === 0" class="empty-msg">Henüz işlem yok</div>
            <div class="tx-list">
              <div v-for="tx in transactions.slice(0, 10)" :key="tx.tx_id" class="tx-row">
                <span class="tx-id">#{{ tx.tx_id }}</span>
                <span class="tx-detail">{{ getUserName(tx.sender) }} -> {{ getUserName(tx.receiver) }}</span>
                <span class="tx-amount">{{ tx.amount }} DTL</span>
                <span v-if="tx.template_id" class="tpl-tag">TPL</span>
                <span v-if="tx.ipfs_cid" class="ipfs-tag">IPFS</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }

/* ==================== LOGIN ==================== */
.login-screen {
  min-height: 100vh; display: flex; justify-content: center; align-items: center;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  font-family: 'Inter', 'Segoe UI', sans-serif;
}
.login-box {
  background: #1e293b; padding: 40px; border-radius: 12px; width: 400px;
  border: 1px solid #334155; text-align: center;
}
.login-box h1 { color: #38bdf8; margin: 0 0 5px; font-size: 24px; }
.login-subtitle { color: #64748b; margin: 0 0 30px; font-size: 13px; }

.login-form { text-align: left; }
.login-form .field { margin-bottom: 16px; }
.login-form label { display: block; color: #94a3b8; font-size: 12px; margin-bottom: 4px; }
.login-form input {
  width: 100%; padding: 10px 12px; background: #0f172a; border: 1px solid #334155;
  color: white; border-radius: 6px; font-size: 14px;
}
.login-error { color: #ef4444; font-size: 12px; margin-bottom: 10px; }
.login-btn {
  width: 100%; padding: 12px; background: #38bdf8; color: #0f172a;
  border: none; border-radius: 6px; font-weight: 700; font-size: 15px; cursor: pointer;
}
.login-hint { margin-top: 24px; color: #64748b; font-size: 11px; }
.login-hint p { margin: 0 0 4px; color: #94a3b8; }
.login-hint small { display: block; margin-top: 2px; }

/* ==================== APP LAYOUT ==================== */
.app-layout {
  display: flex; min-height: 100vh; background: #0f172a;
  font-family: 'Inter', 'Segoe UI', sans-serif; color: #e2e8f0;
}

/* SIDEBAR */
.sidebar {
  width: 280px; background: #1e293b; border-right: 1px solid #334155;
  display: flex; flex-direction: column; flex-shrink: 0;
}
.sidebar-header {
  padding: 16px; border-bottom: 1px solid #334155;
  display: flex; justify-content: space-between; align-items: flex-start;
}
.user-info { }
.user-name { font-weight: 700; font-size: 16px; color: #f1f5f9; }
.user-username { font-size: 12px; color: #64748b; }
.user-balance { font-size: 14px; color: #4ade80; font-weight: 600; margin-top: 4px; }
.logout-btn {
  background: #ef4444; color: white; border: none; border-radius: 4px;
  padding: 4px 10px; font-size: 11px; cursor: pointer; font-weight: 600;
}

.sidebar-nav {
  display: flex; border-bottom: 1px solid #334155;
}
.sidebar-nav button {
  flex: 1; padding: 10px; background: transparent; color: #94a3b8;
  border: none; font-size: 12px; cursor: pointer; font-weight: 600;
}
.sidebar-nav button.active { color: #38bdf8; border-bottom: 2px solid #38bdf8; }

.sidebar-content { flex: 1; overflow-y: auto; padding: 12px; }

.new-tpl-btn {
  width: 100%; padding: 10px; background: #16a34a; color: white;
  border: none; border-radius: 6px; font-weight: 600; cursor: pointer; margin-bottom: 12px;
}

.tpl-card {
  background: #0f172a; border-radius: 8px; padding: 12px; margin-bottom: 10px;
  border: 1px solid #334155;
}
.tpl-card-header { display: flex; justify-content: space-between; align-items: center; }
.tpl-card-header strong { color: #f1f5f9; font-size: 13px; }
.tpl-amount { color: #4ade80; font-weight: 600; font-size: 12px; }
.tpl-card-detail { font-size: 11px; color: #94a3b8; margin-top: 4px; }
.tpl-card-cid { font-size: 9px; color: #a855f7; margin-top: 4px; font-family: monospace; }
.tpl-card-actions { display: flex; gap: 6px; margin-top: 8px; }

.btn-sm {
  padding: 4px 10px; font-size: 10px; border: none; border-radius: 4px;
  cursor: pointer; font-weight: 600; background: #334155; color: #e2e8f0;
}
.btn-danger { background: #ef4444; color: white; }

/* Sidebar Form */
.sidebar-content h4 { color: #38bdf8; margin: 0 0 12px; font-size: 14px; }
.sidebar-content .field { margin-bottom: 12px; }
.sidebar-content .field label { display: block; color: #94a3b8; font-size: 11px; margin-bottom: 3px; }
.sidebar-content .field input,
.sidebar-content .field select {
  width: 100%; padding: 8px; background: #0f172a; border: 1px solid #334155;
  color: white; border-radius: 4px; font-size: 12px;
}
.form-actions { display: flex; gap: 8px; margin-top: 16px; }
.btn-primary {
  flex: 1; padding: 8px; background: #38bdf8; color: #0f172a;
  border: none; border-radius: 6px; font-weight: 600; cursor: pointer;
}
.btn-cancel {
  flex: 1; padding: 8px; background: #334155; color: #e2e8f0;
  border: none; border-radius: 6px; font-weight: 600; cursor: pointer;
}

/* MAIN CONTENT */
.main-content { flex: 1; overflow-y: auto; }

.top-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 24px; border-bottom: 1px solid #334155;
}
.top-bar h2 { margin: 0; color: #38bdf8; font-size: 18px; }
.top-actions { display: flex; gap: 8px; }
.btn-seed {
  padding: 6px 14px; background: #16a34a; color: white;
  border: none; border-radius: 4px; font-weight: 600; cursor: pointer; font-size: 12px;
}
.btn-refresh {
  padding: 6px 14px; background: #2563eb; color: white;
  border: none; border-radius: 4px; font-weight: 600; cursor: pointer; font-size: 12px;
}

.status-bar {
  padding: 8px 24px; background: #1e293b; color: #fbbf24;
  font-size: 12px; border-bottom: 1px solid #334155;
}

.content-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding: 20px 24px;
}
.content-col { display: flex; flex-direction: column; gap: 16px; }

/* CARDS */
.card {
  background: #1e293b; border-radius: 8px; padding: 16px;
  border: 1px solid #334155;
}
.card h3 { color: #38bdf8; font-size: 14px; margin: 0 0 12px; padding-bottom: 8px; border-bottom: 1px solid #334155; }
.card-success { border-left: 4px solid #4ade80; }

/* Transfer */
.from-info {
  background: #0f172a; padding: 8px 12px; border-radius: 6px;
  font-size: 12px; color: #94a3b8; margin-bottom: 12px;
}
.toggle-row { display: flex; gap: 4px; margin-bottom: 12px; }
.toggle-row button {
  flex: 1; padding: 8px; background: #334155; color: #94a3b8;
  border: none; border-radius: 4px; font-weight: 600; cursor: pointer; font-size: 12px;
}
.toggle-row button.active { background: #38bdf8; color: #0f172a; }

.card .field { margin-bottom: 12px; }
.card .field label { display: block; color: #94a3b8; font-size: 11px; margin-bottom: 3px; }
.card .field input,
.card .field select {
  width: 100%; padding: 8px; background: #0f172a; border: 1px solid #334155;
  color: white; border-radius: 4px; font-size: 12px;
}

.btn-send {
  width: 100%; padding: 12px; background: linear-gradient(135deg, #f59e0b, #ea580c);
  color: white; border: none; border-radius: 6px; font-weight: 700; font-size: 14px; cursor: pointer;
}

/* TX Summary */
.tx-summary { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; font-size: 12px; }
.ipfs-badge { color: #a855f7; font-family: monospace; font-size: 10px; }
.tpl-badge { background: #a855f7; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; }
.flow-text { color: #64748b; font-size: 10px; margin-top: 8px; }

/* Table */
table { width: 100%; border-collapse: collapse; }
th, td { padding: 6px 8px; text-align: left; border-bottom: 1px solid #334155; font-size: 12px; }
th { color: #64748b; font-size: 11px; }
.mono { font-family: monospace; color: #94a3b8; font-size: 11px; }
.balance { color: #4ade80; font-weight: 600; }
tr.highlight { background: rgba(56, 189, 248, 0.1); }

/* Logs */
.log-group { margin-bottom: 8px; }
.log-label { color: #38bdf8; font-size: 11px; font-weight: 600; margin-bottom: 3px; }
.log-content {
  background: #0f172a; padding: 8px; border-radius: 4px;
  font-family: monospace; font-size: 9px; color: #bef264;
  max-height: 200px; overflow-y: auto;
}
.empty-log { color: #475569; }

/* TX List */
.tx-list { display: flex; flex-direction: column; gap: 4px; }
.tx-row {
  display: flex; align-items: center; gap: 6px; padding: 6px 8px;
  background: #0f172a; border-radius: 4px; font-size: 11px;
}
.tx-id { color: #64748b; font-family: monospace; min-width: 30px; }
.tx-detail { flex: 1; color: #cbd5e1; }
.tx-amount { color: #4ade80; font-weight: 600; }
.tpl-tag { font-size: 9px; background: #a855f7; color: white; padding: 1px 4px; border-radius: 3px; }
.ipfs-tag { font-size: 9px; background: #0ea5e9; color: white; padding: 1px 4px; border-radius: 3px; }

.empty-msg { color: #475569; font-size: 12px; text-align: center; padding: 16px; }
</style>
